"""
Deduplication Service
=====================
Handles file hashing, duplicate detection, and content-addressable storage.
"""

import hashlib
import os
from django.db import transaction
from django.conf import settings
from contracts.models import File, FileContent


CHUNK_SIZE = 65536  # 64KB for memory-efficient hashing


class DeduplicationService:
    """
    Service for handling file deduplication using content-addressable storage.
    
    Upload Algorithm:
    1. Size-first check: Query FileContent by size (optimization)
    2. Hash computation: Only compute if potential matches exist OR storing new content
    3. Duplicate detection: Check FileContent by hash
    4. Reference increment: If duplicate, increment reference_count
    5. New content: If unique, save file to CAS path, create FileContent
    6. Metadata: Always create new File record pointing to content
    """
    
    @staticmethod
    def compute_hash(file_obj) -> str:
        """
        Compute SHA-256 hash of file content.
        
        Uses chunked reading for memory efficiency.
        Resets file pointer after hashing.
        
        Args:
            file_obj: Django UploadedFile or file-like object
            
        Returns:
            str: Hexadecimal SHA-256 hash
        """
        sha256 = hashlib.sha256()
        for chunk in iter(lambda: file_obj.read(CHUNK_SIZE), b''):
            sha256.update(chunk)
        file_obj.seek(0)  # Reset for subsequent operations
        return sha256.hexdigest()
    
    @classmethod
    def upload_file(cls, file_obj, original_filename: str, file_type: str) -> tuple[File, bool]:
        """
        Upload a file with deduplication.
        
        Args:
            file_obj: Django UploadedFile
            original_filename: Original filename from user
            file_type: MIME type of the file
            
        Returns:
            tuple: (File instance, is_duplicate boolean)
        """
        file_size = file_obj.size
        
        with transaction.atomic():
            # Size-first check: Query for existing content with matching size
            potential_matches = FileContent.objects.filter(size=file_size)
            
            # Compute hash (needed if potential matches exist OR for new content)
            content_hash = cls.compute_hash(file_obj)
            
            # Check if content already exists
            existing_content = FileContent.objects.filter(hash=content_hash).first()
            
            if existing_content:
                # Duplicate detected: increment reference count
                existing_content.reference_count += 1
                existing_content.save(update_fields=['reference_count'])
                
                # Create File metadata pointing to existing content
                file_record = File.objects.create(
                    original_filename=original_filename,
                    file_type=file_type,
                    content=existing_content
                )
                
                return file_record, True
            
            else:
                # New content: create FileContent with CAS storage
                # Generate the storage filename using extension from original
                ext = original_filename.rsplit('.', 1)[-1] if '.' in original_filename else ''
                storage_filename = f"{content_hash}.{ext}" if ext else content_hash
                
                # Create FileContent with hash set before save (for upload_to function)
                file_content = FileContent(
                    hash=content_hash,
                    size=file_size,
                    reference_count=1
                )
                
                # Save the file content to CAS path
                file_content.file.save(storage_filename, file_obj, save=True)
                
                # Create File metadata pointing to new content
                file_record = File.objects.create(
                    original_filename=original_filename,
                    file_type=file_type,
                    content=file_content
                )
                
                return file_record, False
    
    @staticmethod
    def _cleanup_empty_directories(file_path: str) -> None:
        """
        Remove empty parent directories up to the CAS root.
        
        For path like: media/cas/ab/cd/abcd1234.txt
        Will try to remove: media/cas/ab/cd/, then media/cas/ab/
        Stops at media/cas/ (the CAS root).
        
        Args:
            file_path: Full path to the deleted file
        """
        cas_root = os.path.join(settings.MEDIA_ROOT, 'cas')
        
        # Get the directory containing the file
        parent_dir = os.path.dirname(file_path)
        
        # Walk up the directory tree, removing empty dirs
        while parent_dir and parent_dir != cas_root and parent_dir.startswith(cas_root):
            try:
                if os.path.isdir(parent_dir) and not os.listdir(parent_dir):
                    os.rmdir(parent_dir)
                else:
                    # Directory not empty, stop climbing
                    break
            except OSError:
                # Permission error or dir not empty, stop
                break
            parent_dir = os.path.dirname(parent_dir)
    
    @classmethod
    def delete_file(cls, file_record: File) -> dict:
        """
        Delete a file with proper reference counting.
        
        If this is the last reference to the content, the physical file
        is also deleted from storage, and empty parent directories are cleaned up.
        
        Args:
            file_record: File instance to delete
            
        Returns:
            dict: Deletion result with physical_deleted flag
        """
        with transaction.atomic():
            content = file_record.content
            
            # Delete the File metadata record
            file_record.delete()
            
            # Refresh content from DB to get latest reference_count
            # (avoids stale cached values from earlier queries)
            content.refresh_from_db()
            
            # Decrement reference count
            content.reference_count -= 1
            
            if content.reference_count == 0:
                # Last reference: delete physical file and FileContent
                file_path = content.file.path
                content.file.delete(save=False)
                content.delete()
                
                # Clean up empty CAS directories
                cls._cleanup_empty_directories(file_path)
                
                return {'physical_deleted': True}
            else:
                # Other references exist: just save the updated count
                content.save(update_fields=['reference_count'])
                return {'physical_deleted': False}
    
    @staticmethod
    def get_storage_metrics() -> dict:
        """
        Calculate storage metrics for deduplication.
        
        Returns:
            dict: Contains:
                - total_files: Count of all File records
                - unique_contents: Count of unique FileContent records
                - logical_size: Total size if all files stored separately
                - physical_size: Actual storage used
                - storage_saved: Bytes saved via deduplication
                - deduplication_ratio: unique_contents / total_files
        """
        from django.db.models import Sum, Count
        
        # Get unique content stats
        content_stats = FileContent.objects.aggregate(
            unique_contents=Count('hash'),
            physical_size=Sum('size')
        )
        
        # Get logical size (what we'd use without deduplication)
        # This is sum of (size * reference_count) for each FileContent
        logical_size = 0
        for fc in FileContent.objects.all():
            logical_size += fc.size * fc.reference_count
        
        total_files = File.objects.count()
        unique_contents = content_stats['unique_contents'] or 0
        physical_size = content_stats['physical_size'] or 0
        
        storage_saved = logical_size - physical_size
        deduplication_ratio = unique_contents / total_files if total_files > 0 else 1.0
        
        return {
            'total_files': total_files,
            'unique_contents': unique_contents,
            'logical_size': logical_size,
            'physical_size': physical_size,
            'storage_saved': storage_saved,
            'deduplication_ratio': deduplication_ratio
        }
