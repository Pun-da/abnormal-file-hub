from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from django.conf import settings
from contracts.models import File, FileContent
from .serializers import FileSerializer
from .services import DeduplicationService
from .filters import FileFilter


def get_max_upload_size():
    """Get max upload size from settings, default 10MB."""
    return getattr(settings, 'FILE_UPLOAD_MAX_SIZE', 10 * 1024 * 1024)


def format_file_size(size_bytes):
    """Format bytes as human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


class FilePagination(LimitOffsetPagination):
    """
    Custom pagination for file listings.
    
    Per search_core_algorithm.md:
    - Default limit: 20
    - Maximum limit: 100
    """
    default_limit = 20
    max_limit = 100


class FileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for file operations with deduplication support.
    
    Provides:
    - List files with pagination and filtering
    - Upload files with automatic deduplication
    - Delete files with reference counting
    - Storage metrics endpoint
    
    Filtering (all use AND logic):
    - search: Case-insensitive filename search
    - file_type: Exact MIME type match
    - type_category: MIME prefix (e.g., 'image')
    - size_min/size_max: File size range in bytes
    - date_from/date_to: Upload date range (ISO 8601)
    
    Sorting:
    - Default: -uploaded_at (newest first)
    - Allowed: uploaded_at, original_filename, content__size, file_type
    - Prefix with '-' for descending
    """
    queryset = File.objects.select_related('content').all()
    serializer_class = FileSerializer
    filterset_class = FileFilter
    pagination_class = FilePagination
    ordering_fields = ['uploaded_at', 'original_filename', 'content__size', 'file_type']
    ordering = ['-uploaded_at']  # Default ordering
    
    def get_queryset(self):
        """Optimize queries with select_related to avoid N+1."""
        return File.objects.select_related('content').all()

    def create(self, request, *args, **kwargs):
        """
        Upload a file with deduplication.
        
        If the file content already exists, no duplicate storage occurs.
        The response includes `is_duplicate` flag to indicate if this was a duplicate.
        """
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response(
                {'error': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file size
        max_size = get_max_upload_size()
        if file_obj.size > max_size:
            return Response(
                {
                    'error': 'File size exceeds maximum allowed',
                    'details': {
                        'file_size': file_obj.size,
                        'file_size_formatted': format_file_size(file_obj.size),
                        'max_size': max_size,
                        'max_size_formatted': format_file_size(max_size),
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        original_filename = file_obj.name
        file_type = file_obj.content_type or 'application/octet-stream'
        
        try:
            file_record, is_duplicate = DeduplicationService.upload_file(
                file_obj=file_obj,
                original_filename=original_filename,
                file_type=file_type
            )
        except Exception as e:
            return Response(
                {'error': f'Upload failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        serializer = self.get_serializer(file_record)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete a file with proper reference counting.
        
        Physical file is only deleted when no other references exist.
        """
        try:
            file_record = self.get_object()
        except File.DoesNotExist:
            return Response(
                {'error': 'File not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            result = DeduplicationService.delete_file(file_record)
        except Exception as e:
            return Response(
                {'error': f'Delete failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['get'], url_path='storage-metrics')
    def storage_metrics(self, request):
        """
        Get storage metrics showing deduplication effectiveness.
        
        Returns:
            - total_files: Count of all file records
            - unique_contents: Count of unique content hashes
            - logical_size: Total size if all files stored separately
            - physical_size: Actual storage used
            - storage_saved: Bytes saved through deduplication
            - deduplication_ratio: unique_contents / total_files
        """
        metrics = DeduplicationService.get_storage_metrics()
        return Response(metrics)
    
    @action(detail=False, methods=['get'], url_path='upload-limits')
    def upload_limits(self, request):
        """
        Get upload limits for client-side validation.
        
        Returns:
            - max_file_size: Maximum allowed file size in bytes
            - max_file_size_formatted: Human-readable max size
        """
        max_size = get_max_upload_size()
        return Response({
            'max_file_size': max_size,
            'max_file_size_formatted': format_file_size(max_size),
        })
