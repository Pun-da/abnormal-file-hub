"""
Views for monitoring stats endpoints.
"""
from datetime import timedelta

from django.db.models import Sum, Count, Avg, Max
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework.decorators import action

from contracts.models import File, FileContent
from ..models import QueryLog
from .serializers import StorageStatsSerializer, QueryLogSerializer, QuerySummarySerializer


class StorageStatsView(APIView):
    """
    GET /api/stats/storage/
    
    Returns storage statistics showing deduplication effectiveness.
    """
    
    def get(self, request):
        """Get storage statistics."""
        try:
            stats = self._calculate_storage_stats()
            serializer = StorageStatsSerializer(stats)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': f'Failed to calculate storage stats: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _calculate_storage_stats(self):
        """Calculate storage statistics from database."""
        # Count total files and unique contents
        total_files = File.objects.count()
        unique_contents = FileContent.objects.count()
        duplicate_count = max(0, total_files - unique_contents)
        
        # Calculate logical size (total size if no deduplication)
        logical_size_result = File.objects.aggregate(
            total=Sum('content__size')
        )
        logical_size_bytes = logical_size_result['total'] or 0
        
        # Calculate physical size (actual storage used)
        physical_size_result = FileContent.objects.aggregate(
            total=Sum('size')
        )
        physical_size_bytes = physical_size_result['total'] or 0
        
        # Calculate savings
        bytes_saved = max(0, logical_size_bytes - physical_size_bytes)
        
        # Calculate savings percentage (avoid division by zero)
        if logical_size_bytes > 0:
            savings_percent = round((bytes_saved / logical_size_bytes) * 100, 2)
        else:
            savings_percent = 0.0
        
        # Calculate deduplication ratio (avoid division by zero)
        if total_files > 0:
            deduplication_ratio = round(unique_contents / total_files, 4)
        else:
            deduplication_ratio = 0.0
        
        return {
            'total_files': total_files,
            'unique_contents': unique_contents,
            'duplicate_count': duplicate_count,
            'logical_size_bytes': logical_size_bytes,
            'physical_size_bytes': physical_size_bytes,
            'bytes_saved': bytes_saved,
            'savings_percent': savings_percent,
            'deduplication_ratio': deduplication_ratio,
            'timestamp': timezone.now(),
        }


class QueryLogViewSet(ViewSet):
    """
    ViewSet for query log monitoring endpoints.
    
    Endpoints:
    - GET /api/stats/queries/ - List query logs
    - GET /api/stats/queries/slow/ - Get slow queries
    - GET /api/stats/queries/failed/ - Get failed queries
    - GET /api/stats/queries/summary/ - Get query statistics summary
    - DELETE /api/stats/queries/cleanup/ - Cleanup old logs
    """
    
    def list(self, request):
        """
        GET /api/stats/queries/
        
        List query logs with pagination and filtering.
        
        Query Parameters:
        - limit: Results per page (default: 50, max: 200)
        - offset: Pagination offset
        - endpoint: Filter by endpoint
        - status_code: Filter by status code
        - date_from: Filter from date (ISO format)
        - date_to: Filter to date (ISO format)
        """
        queryset = QueryLog.objects.all()
        
        # Apply filters
        queryset = self._apply_filters(queryset, request.query_params)
        
        # Pagination
        limit = min(int(request.query_params.get('limit', 50)), 200)
        offset = int(request.query_params.get('offset', 0))
        
        total_count = queryset.count()
        queryset = queryset[offset:offset + limit]
        
        serializer = QueryLogSerializer(queryset, many=True)
        
        # Build pagination response
        return Response({
            'count': total_count,
            'limit': limit,
            'offset': offset,
            'results': serializer.data,
        })
    
    @action(detail=False, methods=['get'], url_path='slow')
    def slow_queries(self, request):
        """
        GET /api/stats/queries/slow/
        
        Returns queries exceeding duration threshold.
        
        Query Parameters:
        - threshold_ms: Minimum duration to include (default: 500)
        - limit: Results to return (default: 50)
        """
        threshold_ms = int(request.query_params.get('threshold_ms', 500))
        limit = min(int(request.query_params.get('limit', 50)), 200)
        
        queryset = QueryLog.objects.filter(
            duration_ms__gte=threshold_ms
        ).order_by('-duration_ms')[:limit]
        
        serializer = QueryLogSerializer(queryset, many=True)
        
        return Response({
            'threshold_ms': threshold_ms,
            'count': len(serializer.data),
            'results': serializer.data,
        })
    
    @action(detail=False, methods=['get'], url_path='failed')
    def failed_queries(self, request):
        """
        GET /api/stats/queries/failed/
        
        Returns queries with status_code >= 400.
        
        Query Parameters:
        - limit: Results to return (default: 50)
        - status_code: Filter by specific error code
        """
        limit = min(int(request.query_params.get('limit', 50)), 200)
        
        queryset = QueryLog.objects.filter(status_code__gte=400)
        
        # Optional filter by specific status code
        status_code = request.query_params.get('status_code')
        if status_code:
            queryset = queryset.filter(status_code=int(status_code))
        
        queryset = queryset.order_by('-timestamp')[:limit]
        
        serializer = QueryLogSerializer(queryset, many=True)
        
        return Response({
            'count': len(serializer.data),
            'results': serializer.data,
        })
    
    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        """
        GET /api/stats/queries/summary/
        
        Returns aggregated query statistics.
        
        Query Parameters:
        - hours: Time window in hours (default: all time, e.g., hours=24 for last 24 hours)
        """
        queryset = QueryLog.objects.all()
        
        # Optional time window filter
        hours = request.query_params.get('hours')
        period = 'all_time'
        
        if hours:
            try:
                hours = int(hours)
                now = timezone.now()
                start_time = now - timedelta(hours=hours)
                queryset = queryset.filter(timestamp__gte=start_time)
                period = f'last_{hours}_hours'
            except (ValueError, TypeError):
                pass  # Use all time if hours is invalid
        
        # Basic counts
        total_queries = queryset.count()
        successful_queries = queryset.filter(status_code__lt=400).count()
        failed_queries = queryset.filter(status_code__gte=400).count()
        
        # Success rate
        success_rate_percent = round(
            (successful_queries / total_queries * 100) if total_queries > 0 else 0,
            2
        )
        
        # Duration statistics
        duration_stats = queryset.aggregate(
            avg_duration=Avg('duration_ms'),
            max_duration=Max('duration_ms'),
        )
        
        avg_duration_ms = round(duration_stats['avg_duration'] or 0, 1)
        slowest_query_ms = duration_stats['max_duration'] or 0
        
        # Percentiles (manual calculation for SQLite compatibility)
        p50, p95, p99 = self._calculate_percentiles(queryset)
        
        # Most common endpoint
        most_common_endpoint = None
        endpoint_counts = queryset.values('endpoint').annotate(
            count=Count('endpoint')
        ).order_by('-count').first()
        if endpoint_counts:
            most_common_endpoint = endpoint_counts['endpoint']
        
        # Most common error
        most_common_error = None
        error_counts = queryset.filter(
            status_code__gte=400
        ).values('status_code', 'error_message').annotate(
            count=Count('status_code')
        ).order_by('-count').first()
        if error_counts:
            most_common_error = f"{error_counts['status_code']}"
            if error_counts.get('error_message'):
                most_common_error += f" - {error_counts['error_message'][:50]}"
        
        summary_data = {
            'period': period,
            'total_queries': total_queries,
            'successful_queries': successful_queries,
            'failed_queries': failed_queries,
            'success_rate_percent': success_rate_percent,
            'avg_duration_ms': avg_duration_ms,
            'p50_duration_ms': p50,
            'p95_duration_ms': p95,
            'p99_duration_ms': p99,
            'slowest_query_ms': slowest_query_ms,
            'most_common_endpoint': most_common_endpoint,
            'most_common_error': most_common_error,
        }
        
        serializer = QuerySummarySerializer(summary_data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['delete'], url_path='cleanup')
    def cleanup(self, request):
        """
        DELETE /api/stats/queries/cleanup/
        
        Delete old query logs.
        
        Query Parameters:
        - older_than_days: Delete logs older than N days (default: 30)
        - dry_run: If 'true', preview count without deleting
        """
        older_than_days = int(request.query_params.get('older_than_days', 30))
        dry_run = request.query_params.get('dry_run', 'false').lower() == 'true'
        
        # Validate parameters
        if older_than_days < 1:
            return Response(
                {'error': 'older_than_days must be at least 1'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Calculate cutoff date
        cutoff_date = timezone.now() - timedelta(days=older_than_days)
        
        # Count logs to be deleted
        queryset = QueryLog.objects.filter(timestamp__lt=cutoff_date)
        count = queryset.count()
        
        if dry_run:
            return Response({
                'dry_run': True,
                'older_than_days': older_than_days,
                'cutoff_date': cutoff_date.isoformat(),
                'logs_to_delete': count,
            })
        
        # Actually delete
        deleted_count, _ = queryset.delete()
        
        return Response({
            'dry_run': False,
            'older_than_days': older_than_days,
            'cutoff_date': cutoff_date.isoformat(),
            'deleted_count': deleted_count,
        })
    
    def _apply_filters(self, queryset, params):
        """Apply query filters to queryset."""
        # Filter by endpoint
        endpoint = params.get('endpoint')
        if endpoint:
            queryset = queryset.filter(endpoint__icontains=endpoint)
        
        # Filter by status code
        status_code = params.get('status_code')
        if status_code:
            queryset = queryset.filter(status_code=int(status_code))
        
        # Filter by date range
        date_from = params.get('date_from')
        if date_from:
            queryset = queryset.filter(timestamp__gte=date_from)
        
        date_to = params.get('date_to')
        if date_to:
            queryset = queryset.filter(timestamp__lte=date_to)
        
        return queryset
    
    def _calculate_percentiles(self, queryset):
        """
        Calculate percentiles for duration.
        
        SQLite doesn't support native percentile functions,
        so we calculate manually.
        
        Returns:
            tuple: (p50, p95, p99) duration values
        """
        durations = list(queryset.values_list('duration_ms', flat=True).order_by('duration_ms'))
        
        if not durations:
            return (0, 0, 0)
        
        def percentile(data, p):
            """Calculate the pth percentile of data."""
            n = len(data)
            if n == 0:
                return 0
            k = (n - 1) * p / 100
            f = int(k)
            c = f + 1 if f + 1 < n else f
            if f == c:
                return data[f]
            return int(data[f] * (c - k) + data[c] * (k - f))
        
        p50 = percentile(durations, 50)
        p95 = percentile(durations, 95)
        p99 = percentile(durations, 99)
        
        return (p50, p95, p99)
