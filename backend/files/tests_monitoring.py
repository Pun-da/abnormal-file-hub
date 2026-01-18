"""
Unit Tests for Monitoring Functionality
=======================================
Tests cover:
- Storage statistics endpoint
- Query logging middleware
- Query log list endpoint
- Slow queries endpoint
- Failed queries endpoint
- Query summary endpoint
- Query cleanup endpoint
"""

import hashlib
from datetime import timedelta
from io import BytesIO
from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings, RequestFactory
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.response import Response

from contracts.models import File, FileContent
from files.models import QueryLog
from files.middleware import QueryLoggingMiddleware
from files.services import DeduplicationService
import tempfile
import shutil


# Create a temporary media root for tests
TEST_MEDIA_ROOT = tempfile.mkdtemp()


class QueryLogModelTests(TestCase):
    """Tests for the QueryLog model."""
    
    def tearDown(self):
        """Clean up after each test."""
        QueryLog.objects.all().delete()
    
    def test_create_query_log(self):
        """Should create a query log entry with all fields."""
        log = QueryLog.objects.create(
            endpoint='/api/files/',
            method='GET',
            query_params={'search': 'test'},
            duration_ms=50,
            status_code=200,
            result_count=10,
            user_agent='TestAgent/1.0',
            ip_address='192.168.1.1',
        )
        
        self.assertIsNotNone(log.id)
        self.assertEqual(log.endpoint, '/api/files/')
        self.assertEqual(log.method, 'GET')
        self.assertEqual(log.query_params, {'search': 'test'})
        self.assertEqual(log.duration_ms, 50)
        self.assertEqual(log.status_code, 200)
        self.assertEqual(log.result_count, 10)
        self.assertIsNotNone(log.timestamp)
    
    def test_query_log_default_values(self):
        """Should use default values for optional fields."""
        log = QueryLog.objects.create(
            endpoint='/api/files/',
            method='GET',
            query_params={},
            duration_ms=10,
            status_code=200,
        )
        
        self.assertEqual(log.result_count, -1)
        self.assertIsNone(log.error_message)
        self.assertIsNone(log.user_agent)
        self.assertIsNone(log.ip_address)
    
    def test_query_log_with_error(self):
        """Should store error messages for failed requests."""
        log = QueryLog.objects.create(
            endpoint='/api/files/',
            method='POST',
            query_params={},
            duration_ms=20,
            status_code=400,
            error_message='No file provided',
        )
        
        self.assertEqual(log.status_code, 400)
        self.assertEqual(log.error_message, 'No file provided')
    
    def test_query_log_ordering(self):
        """Query logs should be ordered by timestamp descending."""
        # Create logs with slight delays
        log1 = QueryLog.objects.create(
            endpoint='/api/files/',
            method='GET',
            query_params={},
            duration_ms=10,
            status_code=200,
        )
        log2 = QueryLog.objects.create(
            endpoint='/api/files/',
            method='GET',
            query_params={},
            duration_ms=10,
            status_code=200,
        )
        
        logs = list(QueryLog.objects.all())
        # Most recent first
        self.assertEqual(logs[0].id, log2.id)
        self.assertEqual(logs[1].id, log1.id)
    
    def test_query_log_str_representation(self):
        """Should have a meaningful string representation."""
        log = QueryLog.objects.create(
            endpoint='/api/files/',
            method='GET',
            query_params={},
            duration_ms=50,
            status_code=200,
        )
        
        str_repr = str(log)
        self.assertIn('GET', str_repr)
        self.assertIn('/api/files/', str_repr)
        self.assertIn('200', str_repr)
        self.assertIn('50ms', str_repr)


class QueryLoggingMiddlewareTests(TestCase):
    """Tests for the QueryLoggingMiddleware."""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.get_response = MagicMock(return_value=Response(status=200))
        self.middleware = QueryLoggingMiddleware(self.get_response)
    
    def tearDown(self):
        QueryLog.objects.all().delete()
    
    def test_should_log_api_files_endpoint(self):
        """Should log requests to /api/files/."""
        self.assertTrue(self.middleware.should_log('/api/files/'))
    
    def test_should_not_log_stats_endpoints(self):
        """Should not log requests to /api/stats/ (avoid recursion)."""
        self.assertFalse(self.middleware.should_log('/api/stats/storage/'))
        self.assertFalse(self.middleware.should_log('/api/stats/queries/'))
        self.assertFalse(self.middleware.should_log('/api/stats/queries/slow/'))
    
    def test_should_not_log_health_endpoint(self):
        """Should not log health check requests."""
        self.assertFalse(self.middleware.should_log('/health/'))
    
    def test_should_not_log_admin_endpoint(self):
        """Should not log admin requests."""
        self.assertFalse(self.middleware.should_log('/admin/'))
        self.assertFalse(self.middleware.should_log('/admin/files/'))
    
    def test_should_not_log_static_files(self):
        """Should not log static file requests."""
        self.assertFalse(self.middleware.should_log('/static/js/app.js'))
        self.assertFalse(self.middleware.should_log('/media/cas/ab/cd/hash.txt'))
    
    def test_middleware_creates_log_entry(self):
        """Middleware should create a QueryLog entry for logged requests."""
        request = self.factory.get('/api/files/')
        request.META['HTTP_USER_AGENT'] = 'TestBrowser/1.0'
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        
        # Mock response with data attribute
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.data = []
        self.middleware.get_response = MagicMock(return_value=mock_response)
        
        self.middleware(request)
        
        self.assertEqual(QueryLog.objects.count(), 1)
        log = QueryLog.objects.first()
        self.assertEqual(log.endpoint, '/api/files/')
        self.assertEqual(log.method, 'GET')
        self.assertEqual(log.status_code, 200)
    
    def test_middleware_does_not_log_excluded_paths(self):
        """Middleware should not create logs for excluded paths."""
        request = self.factory.get('/api/stats/storage/')
        
        self.middleware(request)
        
        self.assertEqual(QueryLog.objects.count(), 0)
    
    def test_middleware_captures_query_params(self):
        """Middleware should capture query parameters."""
        request = self.factory.get('/api/files/', {'search': 'test', 'limit': '10'})
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.data = []
        self.middleware.get_response = MagicMock(return_value=mock_response)
        
        self.middleware(request)
        
        log = QueryLog.objects.first()
        self.assertEqual(log.query_params['search'], 'test')
        self.assertEqual(log.query_params['limit'], '10')
    
    def test_middleware_captures_duration(self):
        """Middleware should capture request duration."""
        request = self.factory.get('/api/files/')
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.data = []
        self.middleware.get_response = MagicMock(return_value=mock_response)
        
        self.middleware(request)
        
        log = QueryLog.objects.first()
        self.assertGreaterEqual(log.duration_ms, 0)
    
    def test_middleware_captures_result_count_from_list(self):
        """Middleware should capture result count from list responses."""
        request = self.factory.get('/api/files/')
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.data = [{'id': 1}, {'id': 2}, {'id': 3}]
        self.middleware.get_response = MagicMock(return_value=mock_response)
        
        self.middleware(request)
        
        log = QueryLog.objects.first()
        self.assertEqual(log.result_count, 3)
    
    def test_middleware_captures_result_count_from_paginated(self):
        """Middleware should capture result count from paginated responses."""
        request = self.factory.get('/api/files/')
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.data = {'count': 100, 'results': [{'id': 1}, {'id': 2}]}
        self.middleware.get_response = MagicMock(return_value=mock_response)
        
        self.middleware(request)
        
        log = QueryLog.objects.first()
        self.assertEqual(log.result_count, 100)
    
    def test_middleware_captures_error_message(self):
        """Middleware should capture error messages from failed requests."""
        request = self.factory.post('/api/files/')
        
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.data = {'error': 'No file provided'}
        self.middleware.get_response = MagicMock(return_value=mock_response)
        
        self.middleware(request)
        
        log = QueryLog.objects.first()
        self.assertEqual(log.status_code, 400)
        self.assertEqual(log.error_message, 'No file provided')
    
    def test_middleware_logging_failure_does_not_fail_request(self):
        """Logging failure should not fail the actual request."""
        request = self.factory.get('/api/files/')
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.data = []
        self.middleware.get_response = MagicMock(return_value=mock_response)
        
        # Mock the _log_query method to raise an exception
        with patch.object(self.middleware, '_log_query', side_effect=Exception('DB Error')):
            response = self.middleware(request)
        
        # Request should still succeed
        self.assertEqual(response.status_code, 200)
    
    def test_middleware_extracts_client_ip_from_remote_addr(self):
        """Middleware should extract client IP from REMOTE_ADDR."""
        request = self.factory.get('/api/files/')
        request.META['REMOTE_ADDR'] = '192.168.1.100'
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.data = []
        self.middleware.get_response = MagicMock(return_value=mock_response)
        
        self.middleware(request)
        
        log = QueryLog.objects.first()
        self.assertEqual(log.ip_address, '192.168.1.100')
    
    def test_middleware_extracts_client_ip_from_x_forwarded_for(self):
        """Middleware should extract client IP from X-Forwarded-For header."""
        request = self.factory.get('/api/files/')
        request.META['HTTP_X_FORWARDED_FOR'] = '10.0.0.1, 192.168.1.1'
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.data = []
        self.middleware.get_response = MagicMock(return_value=mock_response)
        
        self.middleware(request)
        
        log = QueryLog.objects.first()
        # Should use the first IP in X-Forwarded-For
        self.assertEqual(log.ip_address, '10.0.0.1')


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class StorageStatsAPITests(APITestCase):
    """API tests for the storage statistics endpoint."""
    
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)
    
    def tearDown(self):
        File.objects.all().delete()
        FileContent.objects.all().delete()
        QueryLog.objects.all().delete()
    
    def _create_test_file(self, content: bytes, filename: str = 'test.txt') -> SimpleUploadedFile:
        return SimpleUploadedFile(filename, content, content_type='text/plain')
    
    def test_storage_stats_empty(self):
        """Storage stats should return zeros when no files uploaded."""
        response = self.client.get('/api/stats/storage/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_files'], 0)
        self.assertEqual(response.data['unique_contents'], 0)
        self.assertEqual(response.data['duplicate_count'], 0)
        self.assertEqual(response.data['logical_size_bytes'], 0)
        self.assertEqual(response.data['physical_size_bytes'], 0)
        self.assertEqual(response.data['bytes_saved'], 0)
        self.assertEqual(response.data['savings_percent'], 0.0)
    
    def test_storage_stats_single_file(self):
        """Storage stats should reflect a single uploaded file."""
        content = b"Test content for storage stats"
        file_obj = self._create_test_file(content)
        DeduplicationService.upload_file(file_obj, 'test.txt', 'text/plain')
        
        response = self.client.get('/api/stats/storage/')
        
        self.assertEqual(response.data['total_files'], 1)
        self.assertEqual(response.data['unique_contents'], 1)
        self.assertEqual(response.data['duplicate_count'], 0)
        self.assertEqual(response.data['logical_size_bytes'], len(content))
        self.assertEqual(response.data['physical_size_bytes'], len(content))
        self.assertEqual(response.data['bytes_saved'], 0)
        self.assertEqual(response.data['savings_percent'], 0.0)
        self.assertEqual(response.data['deduplication_ratio'], 1.0)
    
    def test_storage_stats_with_duplicates(self):
        """Storage stats should show savings from deduplication."""
        content = b"Duplicate content for testing"
        content_size = len(content)
        
        # Upload same content 3 times
        for i in range(3):
            file_obj = self._create_test_file(content, f'file{i}.txt')
            DeduplicationService.upload_file(file_obj, f'file{i}.txt', 'text/plain')
        
        response = self.client.get('/api/stats/storage/')
        
        self.assertEqual(response.data['total_files'], 3)
        self.assertEqual(response.data['unique_contents'], 1)
        self.assertEqual(response.data['duplicate_count'], 2)
        self.assertEqual(response.data['logical_size_bytes'], content_size * 3)
        self.assertEqual(response.data['physical_size_bytes'], content_size)
        self.assertEqual(response.data['bytes_saved'], content_size * 2)
        # Savings should be ~66.67%
        self.assertAlmostEqual(response.data['savings_percent'], 66.67, places=1)
    
    def test_storage_stats_includes_timestamp(self):
        """Storage stats should include a timestamp."""
        response = self.client.get('/api/stats/storage/')
        
        self.assertIn('timestamp', response.data)
        self.assertIsNotNone(response.data['timestamp'])
    
    def test_storage_stats_deduplication_ratio(self):
        """Deduplication ratio should be unique_contents / total_files."""
        # Upload 4 files with 2 unique contents
        DeduplicationService.upload_file(
            self._create_test_file(b"Content A"), 'a1.txt', 'text/plain'
        )
        DeduplicationService.upload_file(
            self._create_test_file(b"Content A"), 'a2.txt', 'text/plain'
        )
        DeduplicationService.upload_file(
            self._create_test_file(b"Content B"), 'b1.txt', 'text/plain'
        )
        DeduplicationService.upload_file(
            self._create_test_file(b"Content B"), 'b2.txt', 'text/plain'
        )
        
        response = self.client.get('/api/stats/storage/')
        
        self.assertEqual(response.data['total_files'], 4)
        self.assertEqual(response.data['unique_contents'], 2)
        self.assertEqual(response.data['deduplication_ratio'], 0.5)


class QueryLogAPITests(APITestCase):
    """API tests for the query log endpoints."""
    
    def setUp(self):
        # Create some test query logs
        self.logs = []
        for i in range(10):
            log = QueryLog.objects.create(
                endpoint='/api/files/',
                method='GET',
                query_params={'page': str(i)},
                duration_ms=10 * (i + 1),  # 10, 20, 30, ...
                status_code=200 if i < 8 else 400,  # 2 failures
                result_count=i * 10,
                error_message='Bad request' if i >= 8 else None,
            )
            self.logs.append(log)
    
    def tearDown(self):
        QueryLog.objects.all().delete()
    
    def test_list_queries(self):
        """GET /api/stats/queries/ should list query logs."""
        response = self.client.get('/api/stats/queries/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 10)
        self.assertEqual(len(response.data['results']), 10)
    
    def test_list_queries_pagination_limit(self):
        """Should respect limit parameter."""
        response = self.client.get('/api/stats/queries/', {'limit': 5})
        
        self.assertEqual(response.data['limit'], 5)
        self.assertEqual(len(response.data['results']), 5)
    
    def test_list_queries_pagination_offset(self):
        """Should respect offset parameter."""
        response = self.client.get('/api/stats/queries/', {'limit': 5, 'offset': 5})
        
        self.assertEqual(response.data['offset'], 5)
        self.assertEqual(len(response.data['results']), 5)
    
    def test_list_queries_max_limit(self):
        """Limit should be capped at 200."""
        response = self.client.get('/api/stats/queries/', {'limit': 500})
        
        self.assertEqual(response.data['limit'], 200)
    
    def test_list_queries_filter_by_endpoint(self):
        """Should filter by endpoint."""
        # Add a log with different endpoint
        QueryLog.objects.create(
            endpoint='/api/other/',
            method='GET',
            query_params={},
            duration_ms=10,
            status_code=200,
        )
        
        response = self.client.get('/api/stats/queries/', {'endpoint': 'files'})
        
        for result in response.data['results']:
            self.assertIn('files', result['endpoint'])
    
    def test_list_queries_filter_by_status_code(self):
        """Should filter by status code."""
        response = self.client.get('/api/stats/queries/', {'status_code': 400})
        
        self.assertEqual(len(response.data['results']), 2)
        for result in response.data['results']:
            self.assertEqual(result['status_code'], 400)
    
    def test_slow_queries(self):
        """GET /api/stats/queries/slow/ should return slow queries."""
        response = self.client.get('/api/stats/queries/slow/', {'threshold_ms': 50})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('threshold_ms', response.data)
        self.assertEqual(response.data['threshold_ms'], 50)
        
        # All results should have duration >= threshold
        for result in response.data['results']:
            self.assertGreaterEqual(result['duration_ms'], 50)
    
    def test_slow_queries_default_threshold(self):
        """Slow queries should use default threshold of 500ms."""
        response = self.client.get('/api/stats/queries/slow/')
        
        self.assertEqual(response.data['threshold_ms'], 500)
    
    def test_slow_queries_ordered_by_duration_desc(self):
        """Slow queries should be ordered by duration descending."""
        # Add some slow queries
        QueryLog.objects.create(
            endpoint='/api/files/',
            method='GET',
            query_params={},
            duration_ms=1000,
            status_code=200,
        )
        QueryLog.objects.create(
            endpoint='/api/files/',
            method='GET',
            query_params={},
            duration_ms=600,
            status_code=200,
        )
        
        response = self.client.get('/api/stats/queries/slow/')
        
        results = response.data['results']
        if len(results) > 1:
            for i in range(len(results) - 1):
                self.assertGreaterEqual(
                    results[i]['duration_ms'],
                    results[i + 1]['duration_ms']
                )
    
    def test_failed_queries(self):
        """GET /api/stats/queries/failed/ should return failed queries."""
        response = self.client.get('/api/stats/queries/failed/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        
        for result in response.data['results']:
            self.assertGreaterEqual(result['status_code'], 400)
    
    def test_failed_queries_filter_by_status_code(self):
        """Failed queries should allow filtering by specific status code."""
        # Add a 500 error
        QueryLog.objects.create(
            endpoint='/api/files/',
            method='POST',
            query_params={},
            duration_ms=100,
            status_code=500,
            error_message='Internal server error',
        )
        
        response = self.client.get('/api/stats/queries/failed/', {'status_code': 500})
        
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['status_code'], 500)
    
    def test_query_summary(self):
        """GET /api/stats/queries/summary/ should return summary statistics."""
        response = self.client.get('/api/stats/queries/summary/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['period'], 'last_24_hours')
        self.assertEqual(response.data['total_queries'], 10)
        self.assertEqual(response.data['successful_queries'], 8)
        self.assertEqual(response.data['failed_queries'], 2)
        self.assertEqual(response.data['success_rate_percent'], 80.0)
    
    def test_query_summary_avg_duration(self):
        """Summary should include average duration."""
        response = self.client.get('/api/stats/queries/summary/')
        
        # Average of 10, 20, 30, ..., 100 = 55
        self.assertEqual(response.data['avg_duration_ms'], 55.0)
    
    def test_query_summary_percentiles(self):
        """Summary should include percentile durations."""
        response = self.client.get('/api/stats/queries/summary/')
        
        self.assertIn('p50_duration_ms', response.data)
        self.assertIn('p95_duration_ms', response.data)
        self.assertIn('p99_duration_ms', response.data)
    
    def test_query_summary_slowest_query(self):
        """Summary should include slowest query duration."""
        response = self.client.get('/api/stats/queries/summary/')
        
        self.assertEqual(response.data['slowest_query_ms'], 100)
    
    def test_query_summary_most_common_endpoint(self):
        """Summary should include most common endpoint."""
        response = self.client.get('/api/stats/queries/summary/')
        
        self.assertEqual(response.data['most_common_endpoint'], '/api/files/')
    
    def test_query_summary_empty(self):
        """Summary should handle empty logs gracefully."""
        QueryLog.objects.all().delete()
        
        response = self.client.get('/api/stats/queries/summary/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_queries'], 0)
        self.assertEqual(response.data['success_rate_percent'], 0.0)
        self.assertEqual(response.data['avg_duration_ms'], 0.0)


class QueryCleanupAPITests(APITestCase):
    """API tests for the query log cleanup endpoint."""
    
    def setUp(self):
        # Create logs with different ages
        now = timezone.now()
        
        # Recent logs (should not be deleted)
        for i in range(5):
            log = QueryLog.objects.create(
                endpoint='/api/files/',
                method='GET',
                query_params={},
                duration_ms=10,
                status_code=200,
            )
        
        # Old logs (should be deleted)
        for i in range(5):
            log = QueryLog.objects.create(
                endpoint='/api/files/',
                method='GET',
                query_params={},
                duration_ms=10,
                status_code=200,
            )
            # Manually set timestamp to 40 days ago
            QueryLog.objects.filter(pk=log.pk).update(
                timestamp=now - timedelta(days=40)
            )
    
    def tearDown(self):
        QueryLog.objects.all().delete()
    
    def test_cleanup_dry_run(self):
        """Cleanup with dry_run should preview without deleting."""
        response = self.client.delete(
            '/api/stats/queries/cleanup/?older_than_days=30&dry_run=true'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['dry_run'])
        self.assertEqual(response.data['logs_to_delete'], 5)
        
        # Logs should still exist
        self.assertEqual(QueryLog.objects.count(), 10)
    
    def test_cleanup_actual_delete(self):
        """Cleanup without dry_run should delete old logs."""
        response = self.client.delete(
            '/api/stats/queries/cleanup/?older_than_days=30'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['dry_run'])
        self.assertEqual(response.data['deleted_count'], 5)
        
        # Only recent logs should remain
        self.assertEqual(QueryLog.objects.count(), 5)
    
    def test_cleanup_default_retention(self):
        """Cleanup should use 30 days as default retention."""
        response = self.client.delete(
            '/api/stats/queries/cleanup/?dry_run=true'
        )
        
        self.assertEqual(response.data['older_than_days'], 30)
    
    def test_cleanup_invalid_days(self):
        """Cleanup should reject invalid older_than_days value."""
        response = self.client.delete(
            '/api/stats/queries/cleanup/?older_than_days=0'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_cleanup_includes_cutoff_date(self):
        """Cleanup response should include cutoff date."""
        response = self.client.delete(
            '/api/stats/queries/cleanup/?older_than_days=30&dry_run=true'
        )
        
        self.assertIn('cutoff_date', response.data)


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class IntegrationTests(APITestCase):
    """Integration tests for the complete monitoring flow."""
    
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)
    
    def tearDown(self):
        File.objects.all().delete()
        FileContent.objects.all().delete()
        QueryLog.objects.all().delete()
    
    def _create_test_file(self, content: bytes, filename: str = 'test.txt') -> SimpleUploadedFile:
        return SimpleUploadedFile(filename, content, content_type='text/plain')
    
    def test_file_operations_are_logged(self):
        """File operations should be logged by middleware."""
        # Upload a file
        content = b"Integration test content"
        file_obj = self._create_test_file(content)
        self.client.post('/api/files/', {'file': file_obj}, format='multipart')
        
        # List files
        self.client.get('/api/files/')
        
        # Check logs
        response = self.client.get('/api/stats/queries/')
        
        # Should have logs for POST and GET to /api/files/
        endpoints = [r['endpoint'] for r in response.data['results']]
        self.assertIn('/api/files/', endpoints)
    
    def test_stats_endpoints_not_logged(self):
        """Stats endpoints should not be logged (avoid recursion)."""
        initial_count = QueryLog.objects.count()
        
        # Call stats endpoints
        self.client.get('/api/stats/storage/')
        self.client.get('/api/stats/queries/')
        self.client.get('/api/stats/queries/summary/')
        
        # Log count should not increase
        self.assertEqual(QueryLog.objects.count(), initial_count)
    
    def test_storage_stats_after_file_operations(self):
        """Storage stats should reflect file operations."""
        # Upload files
        content = b"Test content"
        for i in range(3):
            file_obj = self._create_test_file(content, f'file{i}.txt')
            self.client.post('/api/files/', {'file': file_obj}, format='multipart')
        
        # Check storage stats
        response = self.client.get('/api/stats/storage/')
        
        self.assertEqual(response.data['total_files'], 3)
        self.assertEqual(response.data['unique_contents'], 1)
        self.assertEqual(response.data['bytes_saved'], len(content) * 2)
    
    def test_failed_requests_logged_with_errors(self):
        """Failed requests should be logged with error messages."""
        # Make a bad request
        self.client.post('/api/files/', {}, format='multipart')
        
        # Check failed queries
        response = self.client.get('/api/stats/queries/failed/')
        
        self.assertGreaterEqual(response.data['count'], 1)
        # Find the 400 error
        failed_logs = [r for r in response.data['results'] if r['status_code'] == 400]
        self.assertGreater(len(failed_logs), 0)
        self.assertIsNotNone(failed_logs[0]['error_message'])
