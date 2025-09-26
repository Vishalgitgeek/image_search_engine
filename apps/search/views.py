# apps/search/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import TemplateView, View
from django.http import JsonResponse
from django.contrib import messages
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from images.models import Image, ImageFeature
from .models import SearchQuery, SimilarityResult
from .algorithms import search_similar_images, extract_features_for_uploaded_image
import tempfile
import os
import time

class SearchView(View):
    """Handle image upload and search"""
    
    def get(self, request):
        """Show search form"""
        return render(request, 'search/search.html')
    
    def post(self, request):
        """Handle search form submission"""
        if 'query_image' not in request.FILES:
            messages.error(request, 'Please select an image to search with.')
            return redirect('search:search')
        
        uploaded_file = request.FILES['query_image']
        similarity_threshold = float(request.POST.get('similarity_threshold', 0.7))
        max_results = int(request.POST.get('max_results', 20))
        
        try:
            # Create temporary image record
            query_image = Image.objects.create(
                file=uploaded_file,
                title=f"Search_{int(time.time())}",
                uploaded_by=request.user if request.user.is_authenticated else None
            )
            
            # Extract features
            features, extraction_time = extract_features_for_uploaded_image(query_image.file.path)
            
            if features:
                # Save features
                ImageFeature.objects.create(
                    image=query_image,
                    feature_vector=features,
                    extraction_time=extraction_time
                )
                query_image.features_extracted = True
                query_image.save()
                
                # Perform search
                search_results = search_similar_images(
                    query_image=query_image,
                    threshold=similarity_threshold,
                    max_results=max_results,
                    user=request.user if request.user.is_authenticated else None
                )
                
                # Store search results in session for results page
                request.session['search_results'] = {
                    'query_image_id': query_image.id,
                    'results': [(img.id, score) for img, score in search_results['results']],
                    'search_time': search_results['search_time'],
                    'threshold_used': search_results['threshold_used'],
                    'total_candidates': search_results['total_candidates'],
                }
                
                return redirect('search:results')
            else:
                messages.error(request, 'Failed to process uploaded image.')
                query_image.delete()
                
        except Exception as e:
            messages.error(request, f'Search error: {str(e)}')
        
        return redirect('search:search')

class SimilarImagesView(TemplateView):
    """Show similar images for a specific image"""
    template_name = 'search/results.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        image_id = kwargs.get('image_id')
        
        try:
            query_image = get_object_or_404(Image, id=image_id)
            
            # Get search parameters from URL
            threshold = float(self.request.GET.get('threshold', 0.7))
            max_results = int(self.request.GET.get('max_results', 20))
            
            # Perform search
            search_results = search_similar_images(
                query_image=query_image,
                threshold=threshold,
                max_results=max_results,
                user=self.request.user if self.request.user.is_authenticated else None
            )
            
            context['search_data'] = search_results
            
        except Exception as e:
            messages.error(self.request, f'Error finding similar images: {str(e)}')
            context['search_data'] = {'results': [], 'error': str(e)}
        
        return context

class SearchResultsView(TemplateView):
    """Display search results from session"""
    template_name = 'search/results.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get search results from session
        search_data = self.request.session.get('search_results')
        
        if not search_data:
            messages.error(self.request, 'No search results found. Please perform a new search.')
            return context
        
        try:
            # Reconstruct search results
            query_image = Image.objects.get(id=search_data['query_image_id'])
            
            # Get result images with scores
            results = []
            for img_id, score in search_data['results']:
                try:
                    image = Image.objects.get(id=img_id)
                    results.append((image, score))
                except Image.DoesNotExist:
                    continue
            
            context['search_data'] = {
                'query_image': query_image,
                'results': results,
                'search_time': search_data['search_time'],
                'threshold_used': search_data['threshold_used'],
                'total_candidates': search_data['total_candidates'],
            }
            
        except Exception as e:
            messages.error(self.request, f'Error loading search results: {str(e)}')
            context['search_data'] = {'results': [], 'error': str(e)}
        
        return context


# API Views
class SimilarImagesAPIView(View):
    """API endpoint for finding similar images"""
    
    def get(self, request, image_id):
        try:
            image = get_object_or_404(Image, id=image_id)
            threshold = float(request.GET.get('threshold', 0.7))
            max_results = int(request.GET.get('max_results', 20))
            
            search_results = search_similar_images(
                query_image=image,
                threshold=threshold,
                max_results=max_results
            )
            
            # Format for JSON response
            results_data = []
            for img, score in search_results['results']:
                results_data.append({
                    'id': img.id,
                    'title': img.title or img.original_filename,
                    'image_url': img.file.url if img.file else None,
                    'similarity_score': score,
                    'uploaded_at': img.uploaded_at.isoformat(),
                })
            
            return JsonResponse({
                'success': True,
                'query_image_id': image.id,
                'results': results_data,
                'search_time': search_results['search_time'],
                'total_results': len(results_data),
                'threshold_used': search_results['threshold_used'],
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

class SearchAPIView(View):
    """API endpoint for image upload and search"""
    
    def post(self, request):
        if 'image' not in request.FILES:
            return JsonResponse({
                'success': False,
                'error': 'No image file provided'
            }, status=400)
        
        try:
            uploaded_file = request.FILES['image']
            threshold = float(request.POST.get('threshold', 0.7))
            max_results = int(request.POST.get('max_results', 20))
            
            # Create temporary image
            query_image = Image.objects.create(
                file=uploaded_file,
                title=f"API_Search_{int(time.time())}",
            )
            
            # Extract features and search
            features, _ = extract_features_for_uploaded_image(query_image.file.path)
            
            if features:
                ImageFeature.objects.create(
                    image=query_image,
                    feature_vector=features
                )
                query_image.features_extracted = True
                query_image.save()
                
                search_results = search_similar_images(
                    query_image=query_image,
                    threshold=threshold,
                    max_results=max_results
                )
                
                # Format results
                results_data = []
                for img, score in search_results['results']:
                    results_data.append({
                        'id': img.id,
                        'title': img.title or img.original_filename,
                        'image_url': img.file.url,
                        'similarity_score': score,
                    })
                
                return JsonResponse({
                    'success': True,
                    'results': results_data,
                    'search_time': search_results['search_time'],
                    'total_results': len(results_data),
                })
            else:
                query_image.delete()
                return JsonResponse({
                    'success': False,
                    'error': 'Failed to process uploaded image'
                }, status=500)
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
        


        
