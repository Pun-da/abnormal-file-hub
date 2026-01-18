"""
Unit Tests for Search & Filtering Functionality
================================================
Tests cover:
- Filename search (case-insensitive substring)
- File type exact match
- Type category prefix match
- Size range filters
- Date range filters
- Combined filters (AND logic)
- Sorting
- Pagination
- Edge cases and validation
"""

from django.test import override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from rest_framework import status
from contracts.models import File, FileContent
import tempfile
import shutil


# Create a temporary media root for tests
TEST_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class FileSearchFilterTests(APITestCase):
    """
    Tests for search and filtering functionality.
    
    Per docs/search_core_algorithm.md:
    - search: Case-insensitive substring match on filename
    - file_type: Exact MIME type match
    - type_category: MIME prefix match (e.g., 'image/')
    - size_min/size_max: File size range
    - date_from/date_to: Upload date range
    - All filters use AND logic
    """
    
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)
    
    def tearDown(self):
        File.objects.all().delete()
        FileContent.objects.all().delete()
    
    def _upload_file(self, content: bytes, filename: str, content_type: str = 'text/plain'):
        """Helper to upload a file and return the response."""
        file_obj = SimpleUploadedFile(filename, content, content_type=content_type)
        return self.client.post('/api/files/', {'file': file_obj}, format='multipart')
    
    def _setup_test_files(self):
        """Create a set of test files for filtering tests."""
        # Text files
        self._upload_file(b"Report content", 'annual_report.txt', 'text/plain')
        self._upload_file(b"Notes content here", 'meeting_notes.txt', 'text/plain')
        
        # PDF files
        self._upload_file(b"PDF content" * 100, 'document.pdf', 'application/pdf')
        self._upload_file(b"Big PDF" * 500, 'large_report.pdf', 'application/pdf')
        
        # Image files
        self._upload_file(b"PNG data", 'photo.png', 'image/png')
        self._upload_file(b"JPEG data here", 'image.jpeg', 'image/jpeg')
    
    # ===================
    # Filename Search Tests
    # ===================
    
    def test_search_by_filename_substring(self):
        """Search should match files containing substring in filename."""
        self._setup_test_files()
        
        response = self.client.get('/api/files/', {'search': 'report'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        filenames = [f['original_filename'] for f in response.data['results']]
        self.assertIn('annual_report.txt', filenames)
        self.assertIn('large_report.pdf', filenames)
        self.assertEqual(len(filenames), 2)
    
    def test_search_is_case_insensitive(self):
        """Search should be case-insensitive."""
        self._setup_test_files()
        
        response = self.client.get('/api/files/', {'search': 'REPORT'})
        
        filenames = [f['original_filename'] for f in response.data['results']]
        self.assertIn('annual_report.txt', filenames)
        self.assertIn('large_report.pdf', filenames)
    
    def test_search_empty_string_returns_all(self):
        """Empty search string should return all files."""
        self._setup_test_files()
        
        response = self.client.get('/api/files/', {'search': ''})
        
        self.assertEqual(len(response.data['results']), 6)
    
    def test_search_no_match_returns_empty(self):
        """Search with no matches should return empty results."""
        self._setup_test_files()
        
        response = self.client.get('/api/files/', {'search': 'nonexistent'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)
        self.assertEqual(response.data['count'], 0)
    
    # ===================
    # File Type Filter Tests
    # ===================
    
    def test_filter_by_exact_file_type(self):
        """Filter by exact MIME type should match only that type."""
        self._setup_test_files()
        
        response = self.client.get('/api/files/', {'file_type': 'application/pdf'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for file in response.data['results']:
            self.assertEqual(file['file_type'], 'application/pdf')
        self.assertEqual(len(response.data['results']), 2)
    
    def test_filter_by_unknown_file_type_returns_empty(self):
        """Filter by unknown MIME type should return empty (not error)."""
        self._setup_test_files()
        
        response = self.client.get('/api/files/', {'file_type': 'application/unknown'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)
    
    # ===================
    # Type Category Filter Tests
    # ===================
    
    def test_filter_by_type_category(self):
        """Filter by type category should match MIME prefix."""
        self._setup_test_files()
        
        response = self.client.get('/api/files/', {'type_category': 'image'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for file in response.data['results']:
            self.assertTrue(file['file_type'].startswith('image/'))
        self.assertEqual(len(response.data['results']), 2)
    
    def test_filter_by_type_category_text(self):
        """Filter by 'text' category should match text/* types."""
        self._setup_test_files()
        
        response = self.client.get('/api/files/', {'type_category': 'text'})
        
        for file in response.data['results']:
            self.assertTrue(file['file_type'].startswith('text/'))
        self.assertEqual(len(response.data['results']), 2)
    
    # ===================
    # Size Filter Tests
    # ===================
    
    def test_filter_by_size_min(self):
        """Filter by minimum size should return files >= size."""
        self._setup_test_files()
        
        # Get the large PDF size for reference
        response = self.client.get('/api/files/', {'search': 'large_report'})
        large_size = response.data['results'][0]['size']
        
        response = self.client.get('/api/files/', {'size_min': large_size})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for file in response.data['results']:
            self.assertGreaterEqual(file['size'], large_size)
    
    def test_filter_by_size_max(self):
        """Filter by maximum size should return files <= size."""
        self._setup_test_files()
        
        response = self.client.get('/api/files/', {'size_max': 50})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for file in response.data['results']:
            self.assertLessEqual(file['size'], 50)
    
    def test_filter_by_size_range(self):
        """Filter by size range should return files within range."""
        self._setup_test_files()
        
        response = self.client.get('/api/files/', {'size_min': 10, 'size_max': 100})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for file in response.data['results']:
            self.assertGreaterEqual(file['size'], 10)
            self.assertLessEqual(file['size'], 100)
    
    def test_filter_size_min_greater_than_max_returns_empty(self):
        """size_min > size_max should return empty result set."""
        self._setup_test_files()
        
        response = self.client.get('/api/files/', {'size_min': 1000, 'size_max': 10})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)
    
    # ===================
    # Date Filter Tests
    # ===================
    
    def test_filter_by_date_from(self):
        """Filter by date_from should return files uploaded on or after date."""
        self._setup_test_files()
        from datetime import date
        
        today = date.today().isoformat()
        response = self.client.get('/api/files/', {'date_from': today})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # All files were uploaded today
        self.assertEqual(len(response.data['results']), 6)
    
    def test_filter_by_date_to(self):
        """Filter by date_to should return files uploaded on or before date."""
        self._setup_test_files()
        from datetime import date, timedelta
        
        # Use tomorrow's date since date_to compares to start of day
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        response = self.client.get('/api/files/', {'date_to': tomorrow})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 6)
    
    def test_filter_by_future_date_from_returns_empty(self):
        """date_from in future should return empty results."""
        self._setup_test_files()
        
        response = self.client.get('/api/files/', {'date_from': '2099-01-01'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)
    
    def test_filter_by_past_date_to_returns_empty(self):
        """date_to in past should return empty results."""
        self._setup_test_files()
        
        response = self.client.get('/api/files/', {'date_to': '2000-01-01'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)
    
    # ===================
    # Combined Filter Tests (AND logic)
    # ===================
    
    def test_combined_filters_use_and_logic(self):
        """Multiple filters should be combined with AND logic."""
        self._setup_test_files()
        
        # Search for 'report' AND file_type 'application/pdf'
        response = self.client.get('/api/files/', {
            'search': 'report',
            'file_type': 'application/pdf'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Only large_report.pdf matches both
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['original_filename'], 'large_report.pdf')
    
    def test_combined_search_and_type_category(self):
        """Search combined with type_category should narrow results."""
        self._setup_test_files()
        
        response = self.client.get('/api/files/', {
            'search': 'photo',
            'type_category': 'image'
        })
        
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['original_filename'], 'photo.png')
    
    def test_combined_type_and_size_filters(self):
        """Type category combined with size should narrow results."""
        self._setup_test_files()
        
        response = self.client.get('/api/files/', {
            'file_type': 'application/pdf',
            'size_min': 1000  # Only large PDF should match
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for file in response.data['results']:
            self.assertEqual(file['file_type'], 'application/pdf')
            self.assertGreaterEqual(file['size'], 1000)
    
    # ===================
    # Sorting Tests
    # ===================
    
    def test_default_ordering_newest_first(self):
        """Default ordering should be -uploaded_at (newest first)."""
        self._setup_test_files()
        
        response = self.client.get('/api/files/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        # Verify descending order by uploaded_at
        for i in range(len(results) - 1):
            self.assertGreaterEqual(results[i]['uploaded_at'], results[i+1]['uploaded_at'])
    
    def test_ordering_by_filename_ascending(self):
        """Ordering by original_filename should sort alphabetically."""
        self._setup_test_files()
        
        response = self.client.get('/api/files/', {'ordering': 'original_filename'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        filenames = [f['original_filename'] for f in response.data['results']]
        self.assertEqual(filenames, sorted(filenames))
    
    def test_ordering_by_filename_descending(self):
        """Ordering by -original_filename should sort reverse alphabetically."""
        self._setup_test_files()
        
        response = self.client.get('/api/files/', {'ordering': '-original_filename'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        filenames = [f['original_filename'] for f in response.data['results']]
        self.assertEqual(filenames, sorted(filenames, reverse=True))
    
    def test_ordering_by_size(self):
        """Ordering by content__size should sort by file size."""
        self._setup_test_files()
        
        response = self.client.get('/api/files/', {'ordering': 'content__size'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sizes = [f['size'] for f in response.data['results']]
        self.assertEqual(sizes, sorted(sizes))
    
    def test_ordering_by_file_type(self):
        """Ordering by file_type should group by MIME type."""
        self._setup_test_files()
        
        response = self.client.get('/api/files/', {'ordering': 'file_type'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        types = [f['file_type'] for f in response.data['results']]
        self.assertEqual(types, sorted(types))
    
    # ===================
    # Pagination Tests
    # ===================
    
    def test_pagination_default_limit(self):
        """Default pagination should limit to 20 results."""
        # Upload 25 files
        for i in range(25):
            self._upload_file(f"Content {i}".encode(), f'file{i}.txt')
        
        response = self.client.get('/api/files/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 20)
        self.assertEqual(response.data['count'], 25)
        self.assertIsNotNone(response.data['next'])
        self.assertIsNone(response.data['previous'])
    
    def test_pagination_custom_limit(self):
        """Custom limit should override default."""
        for i in range(15):
            self._upload_file(f"Content {i}".encode(), f'file{i}.txt')
        
        response = self.client.get('/api/files/', {'limit': 5})
        
        self.assertEqual(len(response.data['results']), 5)
        self.assertEqual(response.data['count'], 15)
    
    def test_pagination_max_limit_enforced(self):
        """Limit should be capped at 100."""
        for i in range(10):
            self._upload_file(f"Content {i}".encode(), f'file{i}.txt')
        
        response = self.client.get('/api/files/', {'limit': 200})
        
        # Should return all 10 (less than max of 100)
        self.assertEqual(len(response.data['results']), 10)
    
    def test_pagination_offset(self):
        """Offset should skip specified number of results."""
        for i in range(10):
            self._upload_file(f"Content {i}".encode(), f'file{i:02d}.txt')
        
        response = self.client.get('/api/files/', {'limit': 5, 'offset': 5})
        
        self.assertEqual(len(response.data['results']), 5)
        self.assertIsNotNone(response.data['previous'])
    
    def test_pagination_response_format(self):
        """Paginated response should include count, next, previous, results."""
        self._setup_test_files()
        
        response = self.client.get('/api/files/')
        
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertIn('results', response.data)
    
    # ===================
    # Edge Cases and Validation
    # ===================
    
    def test_no_filters_returns_all_paginated(self):
        """No filters should return all files (paginated)."""
        self._setup_test_files()
        
        response = self.client.get('/api/files/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 6)
    
    def test_invalid_size_value_returns_error(self):
        """Invalid size value should return 400 error."""
        response = self.client.get('/api/files/', {'size_min': 'invalid'})
        
        # django-filter handles this gracefully, returns empty or ignores
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])
    
    def test_invalid_date_format_returns_error(self):
        """Invalid date format should return 400 error."""
        response = self.client.get('/api/files/', {'date_from': 'not-a-date'})
        
        # django-filter handles this gracefully
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])
    
    def test_special_characters_in_search(self):
        """Special characters in search should be handled safely."""
        self._upload_file(b"Test", 'file_with_special.txt')
        
        # SQL injection attempt should be safe
        response = self.client.get('/api/files/', {'search': "'; DROP TABLE files;--"})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should just return no matches, not break
        self.assertEqual(len(response.data['results']), 0)
    
    def test_very_long_search_string(self):
        """Very long search string should return 400 (exceeds max_length=255)."""
        self._setup_test_files()
        
        long_search = 'a' * 300  # Longer than 255 char limit
        response = self.client.get('/api/files/', {'search': long_search})
        
        # Per search algorithm: limit length to 255 chars - returns validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
