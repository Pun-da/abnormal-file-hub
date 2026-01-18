"""
Serializers for monitoring stats endpoints.
"""
from rest_framework import serializers
from ..models import QueryLog


class StorageStatsSerializer(serializers.Serializer):
    """Serializer for storage statistics response."""
    total_files = serializers.IntegerField()
    unique_contents = serializers.IntegerField()
    duplicate_count = serializers.IntegerField()
    logical_size_bytes = serializers.IntegerField()
    physical_size_bytes = serializers.IntegerField()
    bytes_saved = serializers.IntegerField()
    savings_percent = serializers.FloatField()
    deduplication_ratio = serializers.FloatField()
    timestamp = serializers.DateTimeField()


class QueryLogSerializer(serializers.ModelSerializer):
    """Serializer for QueryLog model."""
    
    class Meta:
        model = QueryLog
        fields = [
            'id',
            'endpoint',
            'method',
            'query_params',
            'duration_ms',
            'status_code',
            'result_count',
            'error_message',
            'user_agent',
            'ip_address',
            'timestamp',
        ]
        read_only_fields = fields


class QuerySummarySerializer(serializers.Serializer):
    """Serializer for query statistics summary."""
    period = serializers.CharField()
    total_queries = serializers.IntegerField()
    successful_queries = serializers.IntegerField()
    failed_queries = serializers.IntegerField()
    success_rate_percent = serializers.FloatField()
    avg_duration_ms = serializers.FloatField()
    p50_duration_ms = serializers.IntegerField()
    p95_duration_ms = serializers.IntegerField()
    p99_duration_ms = serializers.IntegerField()
    slowest_query_ms = serializers.IntegerField()
    most_common_endpoint = serializers.CharField(allow_null=True)
    most_common_error = serializers.CharField(allow_null=True)
