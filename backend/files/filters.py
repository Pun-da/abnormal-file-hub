"""
File filtering module implementing search algorithm from docs/search_core_algorithm.md

Filter Types:
- search: Case-insensitive substring match on original_filename
- file_type: Exact MIME type match
- type_category: MIME prefix match (e.g., 'image/')
- size_min/size_max: File size range (via content__size)
- date_from/date_to: Upload date range

All filters use AND logic when combined.
"""

from django_filters import rest_framework as filters
from django.core.exceptions import ValidationError
from contracts.models import File


class FileFilter(filters.FilterSet):
    """
    FilterSet for File model with comprehensive search and filtering.
    
    Query Parameters:
        search: Substring match on filename (case-insensitive)
        file_type: Exact MIME type (e.g., 'application/pdf')
        type_category: MIME prefix (e.g., 'image' matches 'image/*')
        size_min: Minimum file size in bytes
        size_max: Maximum file size in bytes
        date_from: Files uploaded on or after this date (ISO 8601)
        date_to: Files uploaded on or before this date (ISO 8601)
    """
    
    # Text search on filename - case-insensitive contains
    search = filters.CharFilter(
        field_name='original_filename',
        lookup_expr='icontains',
        max_length=255,
        help_text='Case-insensitive substring match on filename'
    )
    
    # Exact MIME type match
    file_type = filters.CharFilter(
        field_name='file_type',
        lookup_expr='exact',
        help_text='Exact MIME type match (e.g., application/pdf)'
    )
    
    # MIME type category prefix match (e.g., 'image' matches 'image/*')
    type_category = filters.CharFilter(
        method='filter_type_category',
        help_text='MIME type prefix (e.g., image, application)'
    )
    
    # Size range filters - via related FileContent
    size_min = filters.NumberFilter(
        field_name='content__size',
        lookup_expr='gte',
        help_text='Minimum file size in bytes'
    )
    size_max = filters.NumberFilter(
        field_name='content__size',
        lookup_expr='lte',
        help_text='Maximum file size in bytes'
    )
    
    # Date range filters
    date_from = filters.DateFilter(
        field_name='uploaded_at',
        lookup_expr='gte',
        help_text='Files uploaded on or after this date (ISO 8601)'
    )
    date_to = filters.DateFilter(
        field_name='uploaded_at',
        lookup_expr='lte',
        help_text='Files uploaded on or before this date (ISO 8601)'
    )
    
    class Meta:
        model = File
        fields = [
            'search',
            'file_type',
            'type_category',
            'size_min',
            'size_max',
            'date_from',
            'date_to',
        ]
    
    def filter_type_category(self, queryset, name, value):
        """
        Filter by MIME type category prefix.
        
        Example: 'image' matches 'image/png', 'image/jpeg', etc.
        """
        if not value:
            return queryset
        # Ensure we match the category followed by '/'
        return queryset.filter(file_type__istartswith=f'{value}/')
    
    @property
    def qs(self):
        """
        Override to add custom validation for filter combinations.
        """
        parent_qs = super().qs
        
        # Validate size range
        size_min = self.data.get('size_min')
        size_max = self.data.get('size_max')
        
        if size_min is not None and size_max is not None:
            try:
                min_val = int(size_min)
                max_val = int(size_max)
                if min_val < 0 or max_val < 0:
                    raise ValidationError({'size': 'Size values must be non-negative'})
            except (ValueError, TypeError):
                pass  # Let django-filter handle invalid type errors
        
        return parent_qs
