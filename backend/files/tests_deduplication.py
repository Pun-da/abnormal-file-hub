"""
Unit Tests for Deduplication Functionality
==========================================
Tests cover:
- Hash computation
- File upload with deduplication
- Reference counting on delete
- Storage metrics
- File size validation
"""

import hashlib
from io import BytesIO
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile, InMemoryUploadedFile
from rest_framework.test import APITestCase
from rest_framework import status
from contracts.models import File, FileContent
from files.services import DeduplicationService
import tempfile
import shutil
import os


# Create a temporary media root for tests
TEST_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class DeduplicationServiceTests(TestCase):
    """Tests for the DeduplicationService class."""
    
    @classmethod
    def tearDownClass(cls):
        """Clean up temporary media directory after all tests."""
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)
    
    def tearDown(self):
        """Clean up after each test."""
        File.objects.all().delete()
        FileContent.objects.all().delete()
    
    def _create_test_file(self, content: bytes, filename: str = 'test.txt') -> SimpleUploadedFile:
        """Helper to create a test file."""
        content_type = 'text/plain'
        if filename.endswith('.pdf'):
            content_type = 'application/pdf'
        elif filename.endswith('.csv'):
            content_type = 'text/csv'
        return SimpleUploadedFile(filename, content, content_type=content_type)
    
    # ===================
    # Hash Computation Tests
    # ===================
    
    def test_compute_hash_returns_sha256(self):
        """Hash computation should return a valid SHA-256 hex string."""
        content = b"Hello, World!"
        file_obj = self._create_test_file(content)
        
        computed_hash = DeduplicationService.compute_hash(file_obj)
        
        # Verify it's a valid SHA-256 hash (64 hex characters)
        self.assertEqual(len(computed_hash), 64)
        self.assertTrue(all(c in '0123456789abcdef' for c in computed_hash))
    
    def test_compute_hash_matches_expected(self):
        """Hash should match independently computed SHA-256."""
        content = b"Test content for hashing"
        file_obj = self._create_test_file(content)
        
        expected_hash = hashlib.sha256(content).hexdigest()
        computed_hash = DeduplicationService.compute_hash(file_obj)
        
        self.assertEqual(computed_hash, expected_hash)
    
    def test_compute_hash_resets_file_pointer(self):
        """File pointer should be reset to beginning after hashing."""
        content = b"Test content"
        file_obj = self._create_test_file(content)
        
        DeduplicationService.compute_hash(file_obj)
        
        # File should be readable from the beginning
        self.assertEqual(file_obj.read(), content)
    
    def test_compute_hash_empty_file(self):
        """Empty files should produce the known SHA-256 empty hash."""
        file_obj = self._create_test_file(b"")
        
        computed_hash = DeduplicationService.compute_hash(file_obj)
        empty_hash = hashlib.sha256(b"").hexdigest()
        
        self.assertEqual(computed_hash, empty_hash)
    
    def test_compute_hash_identical_content_same_hash(self):
        """Identical content should produce identical hashes."""
        content = b"Identical content"
        file1 = self._create_test_file(content, 'file1.txt')
        file2 = self._create_test_file(content, 'file2.txt')
        
        hash1 = DeduplicationService.compute_hash(file1)
        hash2 = DeduplicationService.compute_hash(file2)
        
        self.assertEqual(hash1, hash2)
    
    def test_compute_hash_different_content_different_hash(self):
        """Different content should produce different hashes."""
        file1 = self._create_test_file(b"Content A")
        file2 = self._create_test_file(b"Content B")
        
        hash1 = DeduplicationService.compute_hash(file1)
        hash2 = DeduplicationService.compute_hash(file2)
        
        self.assertNotEqual(hash1, hash2)
    
    # ===================
    # Upload Tests
    # ===================
    
    def test_upload_new_file_creates_file_content(self):
        """Uploading new content should create FileContent record."""
        content = b"New unique content"
        file_obj = self._create_test_file(content)
        
        file_record, is_duplicate = DeduplicationService.upload_file(
            file_obj=file_obj,
            original_filename='test.txt',
            file_type='text/plain'
        )
        
        self.assertFalse(is_duplicate)
        self.assertEqual(FileContent.objects.count(), 1)
        self.assertEqual(File.objects.count(), 1)
    
    def test_upload_new_file_stores_correct_metadata(self):
        """File metadata should be stored correctly."""
        content = b"Test content"
        file_obj = self._create_test_file(content, 'document.txt')
        
        file_record, _ = DeduplicationService.upload_file(
            file_obj=file_obj,
            original_filename='document.txt',
            file_type='text/plain'
        )
        
        self.assertEqual(file_record.original_filename, 'document.txt')
        self.assertEqual(file_record.file_type, 'text/plain')
        self.assertEqual(file_record.content.size, len(content))
    
    def test_upload_duplicate_does_not_create_new_content(self):
        """Uploading duplicate content should not create new FileContent."""
        content = b"Duplicate content"
        file1 = self._create_test_file(content, 'first.txt')
        file2 = self._create_test_file(content, 'second.txt')
        
        DeduplicationService.upload_file(file1, 'first.txt', 'text/plain')
        _, is_duplicate = DeduplicationService.upload_file(file2, 'second.txt', 'text/plain')
        
        self.assertTrue(is_duplicate)
        self.assertEqual(FileContent.objects.count(), 1)  # Only one content
        self.assertEqual(File.objects.count(), 2)  # Two file records
    
    def test_upload_duplicate_increments_reference_count(self):
        """Duplicate upload should increment reference count."""
        content = b"Shared content"
        file1 = self._create_test_file(content)
        file2 = self._create_test_file(content)
        
        DeduplicationService.upload_file(file1, 'file1.txt', 'text/plain')
        DeduplicationService.upload_file(file2, 'file2.txt', 'text/plain')
        
        file_content = FileContent.objects.first()
        self.assertEqual(file_content.reference_count, 2)
    
    def test_upload_duplicate_returns_is_duplicate_true(self):
        """Duplicate upload should return is_duplicate=True."""
        content = b"Test"
        file1 = self._create_test_file(content)
        file2 = self._create_test_file(content)
        
        _, is_dup1 = DeduplicationService.upload_file(file1, 'a.txt', 'text/plain')
        _, is_dup2 = DeduplicationService.upload_file(file2, 'b.txt', 'text/plain')
        
        self.assertFalse(is_dup1)
        self.assertTrue(is_dup2)
    
    def test_upload_different_filename_same_content_deduplicates(self):
        """Same content with different filenames should deduplicate."""
        content = b"Same content"
        file1 = self._create_test_file(content, 'report.pdf')
        file2 = self._create_test_file(content, 'backup.pdf')
        
        record1, _ = DeduplicationService.upload_file(file1, 'report.pdf', 'application/pdf')
        record2, _ = DeduplicationService.upload_file(file2, 'backup.pdf', 'application/pdf')
        
        # Both should point to same content
        self.assertEqual(record1.content.hash, record2.content.hash)
        self.assertEqual(FileContent.objects.count(), 1)
    
    def test_upload_same_filename_different_content_creates_both(self):
        """Same filename with different content should create separate contents."""
        file1 = self._create_test_file(b"Version 1", 'data.txt')
        file2 = self._create_test_file(b"Version 2", 'data.txt')
        
        record1, _ = DeduplicationService.upload_file(file1, 'data.txt', 'text/plain')
        record2, _ = DeduplicationService.upload_file(file2, 'data.txt', 'text/plain')
        
        self.assertNotEqual(record1.content.hash, record2.content.hash)
        self.assertEqual(FileContent.objects.count(), 2)
    
    def test_upload_empty_files_deduplicate(self):
        """All empty files should share the same FileContent."""
        empty1 = self._create_test_file(b"", 'empty1.txt')
        empty2 = self._create_test_file(b"", 'empty2.txt')
        
        DeduplicationService.upload_file(empty1, 'empty1.txt', 'text/plain')
        _, is_dup = DeduplicationService.upload_file(empty2, 'empty2.txt', 'text/plain')
        
        self.assertTrue(is_dup)
        self.assertEqual(FileContent.objects.count(), 1)
    
    def test_upload_stores_file_in_cas_path(self):
        """File should be stored in content-addressable storage path."""
        content = b"CAS test"
        file_obj = self._create_test_file(content, 'test.txt')
        
        record, _ = DeduplicationService.upload_file(file_obj, 'test.txt', 'text/plain')
        
        content_hash = record.content.hash
        expected_path_pattern = f"cas/{content_hash[:2]}/{content_hash[2:4]}/{content_hash}"
        self.assertIn(expected_path_pattern, record.content.file.name)
    
    # ===================
    # Delete Tests
    # ===================
    
    def test_delete_single_reference_removes_physical_file(self):
        """Deleting last reference should remove physical file."""
        content = b"To be deleted"
        file_obj = self._create_test_file(content)
        
        record, _ = DeduplicationService.upload_file(file_obj, 'delete_me.txt', 'text/plain')
        file_path = record.content.file.path
        
        result = DeduplicationService.delete_file(record)
        
        self.assertTrue(result['physical_deleted'])
        self.assertEqual(FileContent.objects.count(), 0)
        self.assertEqual(File.objects.count(), 0)
        self.assertFalse(os.path.exists(file_path))
    
    def test_delete_cleans_up_empty_directories(self):
        """Deleting last reference should remove empty CAS directories."""
        content = b"Directory cleanup test"
        file_obj = self._create_test_file(content)
        
        record, _ = DeduplicationService.upload_file(file_obj, 'cleanup.txt', 'text/plain')
        file_path = record.content.file.path
        parent_dir = os.path.dirname(file_path)  # e.g., cas/ab/cd/
        grandparent_dir = os.path.dirname(parent_dir)  # e.g., cas/ab/
        
        # Verify directories exist before delete
        self.assertTrue(os.path.isdir(parent_dir))
        self.assertTrue(os.path.isdir(grandparent_dir))
        
        DeduplicationService.delete_file(record)
        
        # Empty directories should be removed
        self.assertFalse(os.path.exists(parent_dir))
        self.assertFalse(os.path.exists(grandparent_dir))
    
    def test_delete_with_multiple_references_keeps_physical_file(self):
        """Deleting one reference should keep physical file if others exist."""
        content = b"Shared file"
        file1 = self._create_test_file(content)
        file2 = self._create_test_file(content)
        
        record1, _ = DeduplicationService.upload_file(file1, 'file1.txt', 'text/plain')
        record2, _ = DeduplicationService.upload_file(file2, 'file2.txt', 'text/plain')
        file_path = record1.content.file.path
        
        result = DeduplicationService.delete_file(record1)
        
        self.assertFalse(result['physical_deleted'])
        self.assertEqual(FileContent.objects.count(), 1)
        self.assertEqual(File.objects.count(), 1)
        self.assertTrue(os.path.exists(file_path))
    
    def test_delete_decrements_reference_count(self):
        """Delete should decrement reference count."""
        content = b"Reference test"
        file1 = self._create_test_file(content)
        file2 = self._create_test_file(content)
        
        record1, _ = DeduplicationService.upload_file(file1, 'file1.txt', 'text/plain')
        record2, _ = DeduplicationService.upload_file(file2, 'file2.txt', 'text/plain')
        
        content_hash = record1.content.hash
        DeduplicationService.delete_file(record1)
        
        remaining_content = FileContent.objects.get(hash=content_hash)
        self.assertEqual(remaining_content.reference_count, 1)
    
    def test_delete_last_reference_removes_content_record(self):
        """Deleting last reference should remove FileContent record."""
        content = b"Temporary"
        file_obj = self._create_test_file(content)
        
        record, _ = DeduplicationService.upload_file(file_obj, 'temp.txt', 'text/plain')
        content_hash = record.content.hash
        
        DeduplicationService.delete_file(record)
        
        self.assertFalse(FileContent.objects.filter(hash=content_hash).exists())
    
    # ===================
    # Storage Metrics Tests
    # ===================
    
    def test_storage_metrics_empty_storage(self):
        """Metrics for empty storage should return zeros."""
        metrics = DeduplicationService.get_storage_metrics()
        
        self.assertEqual(metrics['total_files'], 0)
        self.assertEqual(metrics['unique_contents'], 0)
        self.assertEqual(metrics['logical_size'], 0)
        self.assertEqual(metrics['physical_size'], 0)
        self.assertEqual(metrics['storage_saved'], 0)
        self.assertEqual(metrics['deduplication_ratio'], 1.0)
    
    def test_storage_metrics_single_file(self):
        """Metrics with single file."""
        content = b"Single file content"
        file_obj = self._create_test_file(content)
        
        DeduplicationService.upload_file(file_obj, 'single.txt', 'text/plain')
        metrics = DeduplicationService.get_storage_metrics()
        
        self.assertEqual(metrics['total_files'], 1)
        self.assertEqual(metrics['unique_contents'], 1)
        self.assertEqual(metrics['logical_size'], len(content))
        self.assertEqual(metrics['physical_size'], len(content))
        self.assertEqual(metrics['storage_saved'], 0)
        self.assertEqual(metrics['deduplication_ratio'], 1.0)
    
    def test_storage_metrics_with_duplicates(self):
        """Metrics should reflect storage savings from deduplication."""
        content = b"Duplicated content here"
        content_size = len(content)
        
        for i in range(3):
            file_obj = self._create_test_file(content, f'file{i}.txt')
            DeduplicationService.upload_file(file_obj, f'file{i}.txt', 'text/plain')
        
        metrics = DeduplicationService.get_storage_metrics()
        
        self.assertEqual(metrics['total_files'], 3)
        self.assertEqual(metrics['unique_contents'], 1)
        self.assertEqual(metrics['logical_size'], content_size * 3)
        self.assertEqual(metrics['physical_size'], content_size)
        self.assertEqual(metrics['storage_saved'], content_size * 2)
    
    def test_storage_metrics_deduplication_ratio(self):
        """Deduplication ratio should be unique_contents / total_files."""
        # Upload 4 files: 2 unique contents
        DeduplicationService.upload_file(
            self._create_test_file(b"A"), 'a1.txt', 'text/plain'
        )
        DeduplicationService.upload_file(
            self._create_test_file(b"A"), 'a2.txt', 'text/plain'
        )
        DeduplicationService.upload_file(
            self._create_test_file(b"B"), 'b1.txt', 'text/plain'
        )
        DeduplicationService.upload_file(
            self._create_test_file(b"B"), 'b2.txt', 'text/plain'
        )
        
        metrics = DeduplicationService.get_storage_metrics()
        
        self.assertEqual(metrics['total_files'], 4)
        self.assertEqual(metrics['unique_contents'], 2)
        self.assertEqual(metrics['deduplication_ratio'], 0.5)


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT, FILE_UPLOAD_MAX_SIZE=1024)  # 1KB limit for tests
class FileUploadAPITests(APITestCase):
    """API integration tests for file upload endpoints."""
    
    @classmethod
    def tearDownClass(cls):
        """Clean up temporary media directory."""
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)
    
    def tearDown(self):
        """Clean up after each test."""
        File.objects.all().delete()
        FileContent.objects.all().delete()
    
    def _create_test_file(self, content: bytes, filename: str = 'test.txt') -> SimpleUploadedFile:
        """Helper to create a test file."""
        return SimpleUploadedFile(filename, content, content_type='text/plain')
    
    # ===================
    # Upload API Tests
    # ===================
    
    def test_upload_file_success(self):
        """POST /api/files/ should upload file successfully."""
        content = b"API test content"
        file_obj = self._create_test_file(content)
        
        response = self.client.post('/api/files/', {'file': file_obj}, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        self.assertEqual(response.data['original_filename'], 'test.txt')
        self.assertFalse(response.data['is_duplicate'])
    
    def test_upload_duplicate_returns_is_duplicate_true(self):
        """Uploading duplicate should return is_duplicate=true."""
        content = b"Duplicate test"
        
        self.client.post('/api/files/', {'file': self._create_test_file(content)}, format='multipart')
        response = self.client.post(
            '/api/files/',
            {'file': self._create_test_file(content, 'another.txt')},
            format='multipart'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['is_duplicate'])
    
    def test_upload_no_file_returns_400(self):
        """POST without file should return 400."""
        response = self.client.post('/api/files/', {}, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_upload_file_exceeds_max_size(self):
        """File exceeding max size should return 400."""
        # Create file larger than 1KB limit
        large_content = b"x" * 2048  # 2KB
        file_obj = self._create_test_file(large_content, 'large.txt')
        
        response = self.client.post('/api/files/', {'file': file_obj}, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('exceeds', response.data['error'].lower())
    
    def test_upload_returns_content_hash(self):
        """Upload response should include content_hash."""
        content = b"Hash test"
        file_obj = self._create_test_file(content)
        
        response = self.client.post('/api/files/', {'file': file_obj}, format='multipart')
        
        self.assertIn('content_hash', response.data)
        expected_hash = hashlib.sha256(content).hexdigest()
        self.assertEqual(response.data['content_hash'], expected_hash)
    
    # ===================
    # List API Tests
    # ===================
    
    def test_list_files_empty(self):
        """GET /api/files/ should return empty list when no files."""
        response = self.client.get('/api/files/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['results']), 0)
    
    def test_list_files_returns_all_files(self):
        """GET /api/files/ should return all uploaded files."""
        self.client.post('/api/files/', {'file': self._create_test_file(b"A", 'a.txt')}, format='multipart')
        self.client.post('/api/files/', {'file': self._create_test_file(b"B", 'b.txt')}, format='multipart')
        
        response = self.client.get('/api/files/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)
    
    # ===================
    # Delete API Tests
    # ===================
    
    def test_delete_file_success(self):
        """DELETE /api/files/{id}/ should delete file."""
        upload_response = self.client.post(
            '/api/files/',
            {'file': self._create_test_file(b"Delete me")},
            format='multipart'
        )
        file_id = upload_response.data['id']
        
        response = self.client.delete(f'/api/files/{file_id}/')
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(File.objects.count(), 0)
    
    def test_delete_duplicate_keeps_content(self):
        """Deleting one duplicate should keep content for others."""
        content = b"Shared"
        self.client.post('/api/files/', {'file': self._create_test_file(content, 'a.txt')}, format='multipart')
        response2 = self.client.post(
            '/api/files/',
            {'file': self._create_test_file(content, 'b.txt')},
            format='multipart'
        )
        
        self.client.delete(f'/api/files/{response2.data["id"]}/')
        
        self.assertEqual(File.objects.count(), 1)
        self.assertEqual(FileContent.objects.count(), 1)
    
    def test_delete_nonexistent_returns_404(self):
        """DELETE with invalid ID should return 404."""
        response = self.client.delete('/api/files/00000000-0000-0000-0000-000000000000/')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    # ===================
    # Storage Metrics API Tests
    # ===================
    
    def test_storage_metrics_endpoint(self):
        """GET /api/files/storage-metrics/ should return metrics."""
        response = self.client.get('/api/files/storage-metrics/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_files', response.data)
        self.assertIn('unique_contents', response.data)
        self.assertIn('storage_saved', response.data)
    
    def test_storage_metrics_reflects_uploads(self):
        """Storage metrics should reflect uploaded files."""
        content = b"Metrics test content"
        self.client.post('/api/files/', {'file': self._create_test_file(content, 'a.txt')}, format='multipart')
        self.client.post('/api/files/', {'file': self._create_test_file(content, 'b.txt')}, format='multipart')
        
        response = self.client.get('/api/files/storage-metrics/')
        
        self.assertEqual(response.data['total_files'], 2)
        self.assertEqual(response.data['unique_contents'], 1)
        self.assertEqual(response.data['storage_saved'], len(content))
    
    # ===================
    # Upload Limits API Tests
    # ===================
    
    def test_upload_limits_endpoint(self):
        """GET /api/files/upload-limits/ should return limits."""
        response = self.client.get('/api/files/upload-limits/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('max_file_size', response.data)
        self.assertIn('max_file_size_formatted', response.data)
    
    def test_upload_limits_returns_configured_size(self):
        """Upload limits should return configured max size."""
        response = self.client.get('/api/files/upload-limits/')
        
        # We set FILE_UPLOAD_MAX_SIZE=1024 in the test settings
        self.assertEqual(response.data['max_file_size'], 1024)


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class ReferenceCountingTests(TestCase):
    """Detailed tests for reference counting behavior."""
    
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)
    
    def tearDown(self):
        File.objects.all().delete()
        FileContent.objects.all().delete()
    
    def _create_test_file(self, content: bytes, filename: str = 'test.txt') -> SimpleUploadedFile:
        return SimpleUploadedFile(filename, content, content_type='text/plain')
    
    def test_reference_count_starts_at_one(self):
        """New FileContent should have reference_count=1."""
        file_obj = self._create_test_file(b"New content")
        record, _ = DeduplicationService.upload_file(file_obj, 'new.txt', 'text/plain')
        
        self.assertEqual(record.content.reference_count, 1)
    
    def test_reference_count_increments_on_duplicate(self):
        """Reference count should increment for each duplicate."""
        content = b"Shared"
        
        for i in range(5):
            file_obj = self._create_test_file(content, f'file{i}.txt')
            DeduplicationService.upload_file(file_obj, f'file{i}.txt', 'text/plain')
        
        file_content = FileContent.objects.first()
        self.assertEqual(file_content.reference_count, 5)
    
    def test_reference_count_decrements_on_delete(self):
        """Reference count should decrement on file deletion."""
        content = b"Counting"
        records = []
        
        for i in range(3):
            file_obj = self._create_test_file(content, f'file{i}.txt')
            record, _ = DeduplicationService.upload_file(file_obj, f'file{i}.txt', 'text/plain')
            records.append(record)
        
        # Delete one
        DeduplicationService.delete_file(records[0])
        
        file_content = FileContent.objects.first()
        self.assertEqual(file_content.reference_count, 2)
    
    def test_content_deleted_when_reference_count_zero(self):
        """FileContent should be deleted when reference_count reaches 0."""
        content = b"Will be deleted"
        file_obj = self._create_test_file(content)
        record, _ = DeduplicationService.upload_file(file_obj, 'bye.txt', 'text/plain')
        content_hash = record.content.hash
        
        DeduplicationService.delete_file(record)
        
        self.assertFalse(FileContent.objects.filter(hash=content_hash).exists())
    
    def test_multiple_uploads_and_deletes_correct_count(self):
        """Reference count should be correct after multiple operations."""
        content = b"Track me"
        
        # Upload 5 files
        records = []
        for i in range(5):
            file_obj = self._create_test_file(content, f'file{i}.txt')
            record, _ = DeduplicationService.upload_file(file_obj, f'file{i}.txt', 'text/plain')
            records.append(record)
        
        # Delete 3
        for record in records[:3]:
            DeduplicationService.delete_file(record)
        
        file_content = FileContent.objects.first()
        self.assertEqual(file_content.reference_count, 2)
        self.assertEqual(File.objects.count(), 2)
