"""
URL configuration for stats endpoints.
"""
from django.urls import path
from .views import StorageStatsView, QueryLogViewSet

# Create instances for ViewSet actions
query_log_list = QueryLogViewSet.as_view({'get': 'list'})
query_log_slow = QueryLogViewSet.as_view({'get': 'slow_queries'})
query_log_failed = QueryLogViewSet.as_view({'get': 'failed_queries'})
query_log_summary = QueryLogViewSet.as_view({'get': 'summary'})
query_log_cleanup = QueryLogViewSet.as_view({'delete': 'cleanup'})

urlpatterns = [
    # Storage statistics
    path('storage/', StorageStatsView.as_view(), name='storage-stats'),
    
    # Query logs
    path('queries/', query_log_list, name='query-log-list'),
    path('queries/slow/', query_log_slow, name='query-log-slow'),
    path('queries/failed/', query_log_failed, name='query-log-failed'),
    path('queries/summary/', query_log_summary, name='query-log-summary'),
    path('queries/cleanup/', query_log_cleanup, name='query-log-cleanup'),
]
