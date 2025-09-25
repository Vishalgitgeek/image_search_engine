from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
import os
import hashlib
from PIL import Image as PILImage


class Image(models.Model):
    """Model to store image information and metadata"""
    
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    file = models.ImageField(
        upload_to='uploads/%Y/%m/',
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])]
    )
    
    # Metadata
    original_filename = models.CharField(max_length=255, blank=True)
    file_size = models.PositiveIntegerField(null=True, blank=True)  # Size in bytes
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    image_hash = models.CharField(max_length=64, unique=True, null=True, blank=True)
    
    # Classification
    is_seed_image = models.BooleanField(default=False)  # Loaded from seed data
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Processing status
    features_extracted = models.BooleanField(default=False)
    processing_error = models.TextField(blank=True)
    
    # Timestamps
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['features_extracted']),
            models.Index(fields=['is_seed_image']),
            models.Index(fields=['image_hash']),
        ]
    
    def __str__(self):
        return self.title or self.original_filename or f"Image {self.id}"
    
    def save(self, *args, **kwargs):
        # Extract metadata before saving
        if self.file and not self.pk:  # Only on create
            self.extract_metadata()
        super().save(*args, **kwargs)
    
    def extract_metadata(self):
        """Extract image metadata and generate hash"""
        if self.file:
            # Get original filename
            self.original_filename = os.path.basename(self.file.name)
            
            # Get file size
            self.file_size = self.file.size
            
            # Get image dimensions and generate hash
            try:
                with PILImage.open(self.file) as img:
                    self.width, self.height = img.size
                    
                    # Generate hash from image content
                    img_bytes = self.file.read()
                    self.image_hash = hashlib.md5(img_bytes).hexdigest()
                    self.file.seek(0)  # Reset file pointer
                    
            except Exception as e:
                self.processing_error = f"Metadata extraction error: {str(e)}"
    
    @property
    def file_size_mb(self):
        """Return file size in MB"""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return 0
    
    @property
    def aspect_ratio(self):
        """Return aspect ratio as string"""
        if self.width and self.height:
            return f"{self.width}x{self.height}"
        return "Unknown"


class ImageFeature(models.Model):
    """Model to store extracted ML features for each image"""
    
    image = models.OneToOneField(
        Image, 
        on_delete=models.CASCADE, 
        related_name='features'
    )
    
    # Feature data
    feature_vector = models.JSONField()  # Store numpy array as list
    extraction_model = models.CharField(max_length=50, default='resnet50')
    vector_size = models.PositiveIntegerField(default=2048)
    
    # Processing info
    extraction_time = models.FloatField(null=True, blank=True)  # Time in seconds
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['extraction_model']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Features for {self.image.title or self.image.id}"
    
    @property
    def feature_vector_length(self):
        """Return length of feature vector"""
        if self.feature_vector:
            return len(self.feature_vector)
        return 0


# SearchQuery and SimilarityResult models moved to apps/search/models.py