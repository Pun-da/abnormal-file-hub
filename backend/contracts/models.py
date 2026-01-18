"""
Shared Data Contract Models
===========================
DO NOT MODIFY without explicit approval.
This module is symlinked across worktrees.

Models:
    - FileContent: Unique physical file content (content-addressable storage)
    - File: User-uploaded file metadata (references FileContent)
"""

from django.db import models
import uuid


def content_addressable_path(instance, filename):
    """
    Generate storage path for content-addressable file.
    Path structure: cas/{hash[0:2]}/{hash[2:4]}/{hash}.{ext}
    """
    hash_value = instance.hash
    ext = filename.split('.')[-1] if '.' in filename else ''
    
    if ext:
        return f"cas/{hash_value[:2]}/{hash_value[2:4]}/{hash_value}.{ext}"
    return f"cas/{hash_value[:2]}/{hash_value[2:4]}/{hash_value}"


class FileContent(models.Model):
    """
    Represents unique physical file content.
    Primary key is the SHA-256 hash of the content.
    Multiple File records can reference the same FileContent.
    """
    hash = models.CharField(
        max_length=64,
        primary_key=True,
        help_text="SHA-256 hash of file content"
    )
    file = models.FileField(
        upload_to=content_addressable_path,
        help_text="Path to physical file in content-addressable storage"
    )
    size = models.BigIntegerField(
        help_text="File size in bytes"
    )
    reference_count = models.PositiveIntegerField(
        default=1,
        help_text="Number of File records referencing this content"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this content was first uploaded"
    )

    class Meta:
        verbose_name = "File Content"
        verbose_name_plural = "File Contents"
        indexes = [
            models.Index(fields=['size'], name='filecontent_size_idx'),
        ]

    def __str__(self):
        return f"{self.hash[:12]}... ({self.size} bytes)"


class File(models.Model):
    """
    Represents user-uploaded file metadata.
    References FileContent for actual storage.
    Multiple Files can share the same content (deduplication).
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    original_filename = models.CharField(
        max_length=255,
        help_text="Original filename as uploaded by user"
    )
    file_type = models.CharField(
        max_length=100,
        help_text="MIME type of the file"
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this file was uploaded"
    )
    content = models.ForeignKey(
        FileContent,
        on_delete=models.PROTECT,
        related_name='files',
        help_text="Reference to the actual file content"
    )

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = "File"
        verbose_name_plural = "Files"
        indexes = [
            models.Index(fields=['original_filename'], name='file_filename_idx'),
            models.Index(fields=['file_type'], name='file_type_idx'),
            models.Index(fields=['uploaded_at'], name='file_uploaded_idx'),
            models.Index(fields=['file_type', 'uploaded_at'], name='file_type_date_idx'),
        ]

    def __str__(self):
        return self.original_filename

    @property
    def size(self):
        """File size accessed via content reference."""
        return self.content.size

    @property
    def file(self):
        """File field accessed via content reference."""
        return self.content.file
