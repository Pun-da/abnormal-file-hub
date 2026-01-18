# Models have been moved to contracts app (shared data contract)
# Import from contracts.models instead:
#   from contracts.models import File, FileContent

from django.db import models
from contracts.models import File, FileContent
import uuid

__all__ = ['File', 'FileContent', 'QueryLog']


class QueryLog(models.Model):
    """
    Model to track API query performance and failures.
    Used for monitoring search/filter performance.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    endpoint = models.CharField(
        max_length=255,
        help_text="API path called"
    )
    method = models.CharField(
        max_length=10,
        help_text="HTTP method (GET, POST, etc.)"
    )
    query_params = models.JSONField(
        default=dict,
        help_text="Filter/search parameters"
    )
    duration_ms = models.PositiveIntegerField(
        help_text="Response time in milliseconds"
    )
    status_code = models.PositiveSmallIntegerField(
        help_text="HTTP response status"
    )
    result_count = models.IntegerField(
        default=-1,
        help_text="Number of results returned (-1 if N/A)"
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text="Error details if failed"
    )
    user_agent = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Client user agent"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="Client IP address"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="When request occurred"
    )

    class Meta:
        verbose_name = "Query Log"
        verbose_name_plural = "Query Logs"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp'], name='querylog_timestamp_idx'),
            models.Index(fields=['status_code'], name='querylog_status_idx'),
            models.Index(fields=['duration_ms'], name='querylog_duration_idx'),
            models.Index(fields=['endpoint'], name='querylog_endpoint_idx'),
        ]

    def __str__(self):
        return f"{self.method} {self.endpoint} - {self.status_code} ({self.duration_ms}ms)"
