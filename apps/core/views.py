# apps/core/views.py
from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from images.models import Image
from django.contrib import messages
from django.conf import settings
from images.models import Image, ImageFeature
from search.models import SearchQuery
from search.algorithms import search_similar_images, extract_features_for_uploaded_image
from datetime import datetime, timedelta
import tempfile
import os

class IndexView(TemplateView):
    template_name = 'core/index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Database statistics
        context['total_images'] = Image.objects.count()
        context['processed_images'] = Image.objects.filter(features_extracted=True).count()
        
        # Recent searches (last 7 days)
        week_ago = datetime.now() - timedelta(days=7)
        context['recent_searches'] = SearchQuery.objects.filter(
            created_at__gte=week_ago
        ).count()
        
        # Sample images for homepage
        context['sample_images'] = Image.objects.filter(
            is_seed_image=True,
            features_extracted=True
        ).order_by('?')[:4]  # Random 4 images
        
        return context


class UploadView(TemplateView):
    template_name = 'core/upload.html'
    
    def post(self, request, *args, **kwargs):
        """Handle image upload and redirect to search"""
        if 'image' not in request.FILES:
            messages.error(request, 'Please select an image to upload.')
            return redirect('core:upload')
        
        uploaded_file = request.FILES['image']
        
        # Validate file
        if not self.validate_uploaded_file(uploaded_file):
            return redirect('core:upload')
        
        # Create temporary image record
        try:
            image = Image.objects.create(
                file=uploaded_file,
                title=f"Query_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                uploaded_by=request.user if request.user.is_authenticated else None
            )
            
            # Extract features immediately
            features, extraction_time = extract_features_for_uploaded_image(image.file.path)
            
            if features:
                # Save features
                ImageFeature.objects.create(
                    image=image,
                    feature_vector=features,
                    extraction_time=extraction_time
                )
                image.features_extracted = True
                image.save()
                
                # Redirect to search results
                return redirect('search:similar', image_id=image.id)
            else:
                messages.error(request, 'Failed to process image. Please try again.')
                image.delete()  # Clean up failed upload
                
        except Exception as e:
            messages.error(request, f'Error uploading image: {str(e)}')
        
        return redirect('core:upload')
    
    def validate_uploaded_file(self, uploaded_file):
        """Validate uploaded image file"""
        # Check file size
        max_size = getattr(settings, 'MAX_UPLOAD_SIZE', 2 * 1024 * 1024)  # 2MB
        if uploaded_file.size > max_size:
            messages.error(
                self.request, 
                f'File size ({uploaded_file.size/1024/1024:.1f}MB) exceeds maximum allowed size ({max_size/1024/1024:.1f}MB).'
            )
            return False
        
        # Check file extension
        allowed_extensions = getattr(settings, 'ALLOWED_IMAGE_EXTENSIONS', ['.jpg', '.jpeg', '.png'])
        file_extension = os.path.splitext(uploaded_file.name)[1].lower()
        if file_extension not in allowed_extensions:
            messages.error(
                self.request,
                f'File type "{file_extension}" is not allowed. Please use: {", ".join(allowed_extensions)}'
            )
            return False
        
        return True

class GalleryView(TemplateView):
    template_name = 'core/gallery.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all processed images
        images = Image.objects.filter(
            features_extracted=True
        ).order_by('-uploaded_at')
        
        # Pagination parameters
        page = self.request.GET.get('page', 1)
        per_page = 24
        
        try:
            page = int(page)
        except ValueError:
            page = 1
        
        start_index = (page - 1) * per_page
        end_index = start_index + per_page
        
        context['images'] = images[start_index:end_index]
        context['total_images'] = images.count()
        context['current_page'] = page
        context['per_page'] = per_page
        context['has_next'] = end_index < images.count()
        context['has_previous'] = page > 1
        context['next_page'] = page + 1 if context['has_next'] else None
        context['previous_page'] = page - 1 if context['has_previous'] else None
        
        return context
    