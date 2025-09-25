# apps/images/views.py
from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView, DeleteView, TemplateView
from django.http import JsonResponse
from .models import Image

class ImageListView(ListView):
    model = Image
    template_name = 'images/list.html'
    context_object_name = 'images'
    paginate_by = 20

class ImageDetailView(DetailView):
    model = Image
    template_name = 'images/detail.html'
    context_object_name = 'image'

class ImageDeleteView(DeleteView):
    model = Image
    success_url = '/images/'

class ImageUploadView(TemplateView):
    template_name = 'images/upload.html'

# Basic API views (minimal)
class ImageListAPIView(ListView):
    model = Image
    
    def get(self, request, *args, **kwargs):
        images = Image.objects.all()[:20]
        data = [{'id': img.id, 'title': img.title} for img in images]
        return JsonResponse({'images': data})

class ImageDetailAPIView(DetailView):
    model = Image
    
    def get(self, request, *args, **kwargs):
        image = get_object_or_404(Image, pk=kwargs['pk'])
        data = {
            'id': image.id,
            'title': image.title,
            'file_url': image.file.url if image.file else None
        }
        return JsonResponse(data)
