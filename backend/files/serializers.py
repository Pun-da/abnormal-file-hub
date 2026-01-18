from rest_framework import serializers
from contracts.models import File, FileContent


class FileContentSerializer(serializers.ModelSerializer):
    """Serializer for FileContent (internal use)."""
    
    class Meta:
        model = FileContent
        fields = ['hash', 'size', 'reference_count', 'created_at']
        read_only_fields = ['hash', 'size', 'reference_count', 'created_at']


class FileSerializer(serializers.ModelSerializer):
    """
    Serializer for File model.
    Maintains backward-compatible API response format.
    """
    # Expose size from FileContent
    size = serializers.IntegerField(source='content.size', read_only=True)
    
    # Expose file URL from FileContent
    file = serializers.FileField(source='content.file', read_only=True)
    
    # Expose content hash for deduplication transparency
    content_hash = serializers.CharField(source='content.hash', read_only=True)
    
    # Flag indicating if this upload was a duplicate
    is_duplicate = serializers.SerializerMethodField()

    class Meta:
        model = File
        fields = [
            'id',
            'file',
            'original_filename',
            'file_type',
            'size',
            'uploaded_at',
            'content_hash',
            'is_duplicate',
        ]
        read_only_fields = ['id', 'uploaded_at', 'content_hash', 'is_duplicate']

    def get_is_duplicate(self, obj):
        """Check if this file shares content with other files."""
        return obj.content.reference_count > 1
