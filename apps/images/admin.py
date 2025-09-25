# apps/images/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Image, ImageFeature


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'title',
        'image_thumbnail',
        'original_filename',
        'file_size_mb',
        'aspect_ratio',
        'is_seed_image',
        'features_extracted',
        'uploaded_at'
    ]
    
    list_filter = [
        'is_seed_image',
        'features_extracted',
        'uploaded_at',
        'uploaded_by'
    ]
    
    search_fields = [
        'title',
        'original_filename',
        'description'
    ]
    
    readonly_fields = [
        'file_size',
        'width',
        'height',
        'image_hash',
        'uploaded_at',
        'updated_at',
        'image_preview'
    ]
    
    fieldsets = [
        ('Basic Information', {
            'fields': ['title', 'description', 'file']
        }),
        ('Metadata', {
            'fields': ['original_filename', 'file_size', 'width', 'height', 'image_hash'],
            'classes': ['collapse']
        }),
        ('Classification', {
            'fields': ['is_seed_image', 'uploaded_by']
        }),
        ('Processing', {
            'fields': ['features_extracted', 'processing_error']
        }),
        ('Timestamps', {
            'fields': ['uploaded_at', 'updated_at'],
            'classes': ['collapse']
        }),
        ('Preview', {
            'fields': ['image_preview']
        })
    ]
    
    actions = ['extract_features', 'mark_as_seed', 'mark_as_not_seed']
    
    def image_thumbnail(self, obj):
        """Display small thumbnail in list view"""
        if obj.file:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;" />',
                obj.file.url
            )
        return "No Image"
    image_thumbnail.short_description = "Thumbnail"
    
    def image_preview(self, obj):
        """Display larger preview in detail view"""
        if obj.file:
            return format_html(
                '<img src="{}" style="max-width: 300px; max-height: 300px; border-radius: 8px;" />',
                obj.file.url
            )
        return "No Image"
    image_preview.short_description = "Preview"
    
    def extract_features(self, request, queryset):
        """Admin action to extract features for selected images"""
        from django.core.management import call_command
        from io import StringIO
        import sys
        
        # Capture command output
        out = StringIO()
        sys.stdout = out
        
        try:
            # Get IDs of selected images
            image_ids = list(queryset.values_list('id', flat=True))
            
            # Run feature extraction (we'll implement this)
            count = 0
            for image in queryset:
                if not image.features_extracted:
                    # This would call the feature extraction logic
                    count += 1
            
            self.message_user(request, f'Started feature extraction for {count} images.')
            
        except Exception as e:
            self.message_user(request, f'Error: {str(e)}', level='ERROR')
        finally:
            sys.stdout = sys.__stdout__
    
    extract_features.short_description = "Extract features for selected images"
    
    def mark_as_seed(self, request, queryset):
        """Mark selected images as seed images"""
        updated = queryset.update(is_seed_image=True)
        self.message_user(request, f'{updated} images marked as seed images.')
    mark_as_seed.short_description = "Mark as seed images"
    
    def mark_as_not_seed(self, request, queryset):
        """Mark selected images as not seed images"""
        updated = queryset.update(is_seed_image=False)
        self.message_user(request, f'{updated} images unmarked as seed images.')
    mark_as_not_seed.short_description = "Unmark as seed images"


@admin.register(ImageFeature)
class ImageFeatureAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'image_title',
        'extraction_model',
        'vector_size',
        'feature_vector_length',
        'extraction_time',
        'created_at'
    ]
    
    list_filter = [
        'extraction_model',
        'created_at'
    ]
    
    search_fields = [
        'image__title',
        'image__original_filename'
    ]
    
    readonly_fields = [
        'image',
        'feature_vector',
        'extraction_model',
        'vector_size',
        'extraction_time',
        'created_at',
        'feature_vector_preview'
    ]
    
    fieldsets = [
        ('Image', {
            'fields': ['image']
        }),
        ('Feature Data', {
            'fields': ['extraction_model', 'vector_size', 'extraction_time']
        }),
        ('Vector Preview', {
            'fields': ['feature_vector_preview'],
            'classes': ['collapse']
        }),
        ('Raw Data', {
            'fields': ['feature_vector'],
            'classes': ['collapse']
        })
    ]
    
    def image_title(self, obj):
        """Display image title or filename"""
        return obj.image.title or obj.image.original_filename
    image_title.short_description = "Image"
    
    def feature_vector_preview(self, obj):
        """Display first few values of feature vector"""
        if obj.feature_vector:
            preview = obj.feature_vector[:10]  # First 10 values
            return f"{preview}... (showing first 10 of {len(obj.feature_vector)} values)"
        return "No feature vector"
    feature_vector_preview.short_description = "Feature Vector Preview"

