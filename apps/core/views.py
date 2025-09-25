# apps/core/views.py
from django.shortcuts import render
from django.views.generic import TemplateView
from images.models import Image

class IndexView(TemplateView):
    template_name = 'core/index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add some basic stats
        context['total_images'] = Image.objects.count()
        context['processed_images'] = Image.objects.filter(features_extracted=True).count()
        context['sample_images'] = Image.objects.filter(is_seed_image=True)[:4]
        return context

class UploadView(TemplateView):
    template_name = 'core/upload.html'

class GalleryView(TemplateView):
    template_name = 'core/gallery.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['images'] = Image.objects.filter(is_seed_image=True)[:20]
        return context

