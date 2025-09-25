# apps/search/algorithms.py
import numpy as np
import time
from sklearn.metrics.pairwise import cosine_similarity
from django.conf import settings
from images.models import Image, ImageFeature
from search.models import SearchQuery, SimilarityResult
from ml_models.feature_extractor import get_global_extractor


class ImageSimilaritySearcher:
    """
    Main class for finding similar images based on feature vectors
    """
    
    def __init__(self):
        self.similarity_threshold = getattr(settings, 'SIMILARITY_THRESHOLD', 0.7)
        self.max_results = getattr(settings, 'MAX_SIMILAR_RESULTS', 20)
    
    def search_similar_images(self, query_image, threshold=None, max_results=None, user=None):
        """
        Find images similar to the query image
        
        Args:
            query_image (Image): Query image object
            threshold (float): Minimum similarity threshold (0-1)
            max_results (int): Maximum number of results to return
            user (User): User making the search (for logging)
            
        Returns:
            dict: Search results with metadata
        """
        start_time = time.time()
        
        # Use defaults if not provided
        threshold = threshold or self.similarity_threshold
        max_results = max_results or self.max_results
        
        # Get query image features
        query_features = self.get_image_features(query_image)
        if query_features is None:
            return {
                'error': 'Query image features not found',
                'results': [],
                'search_time': 0,
                'query_image': query_image
            }
        
        # Get all other images with features (exclude query image)
        candidate_images = Image.objects.filter(
            features_extracted=True
        ).exclude(id=query_image.id).prefetch_related('features')
        
        if not candidate_images.exists():
            return {
                'results': [],
                'search_time': time.time() - start_time,
                'query_image': query_image,
                'message': 'No other images available for comparison'
            }
        
        # Calculate similarities
        similarities = self.calculate_similarities(query_features, candidate_images)
        
        # Filter and sort results
        filtered_results = [
            (image, score) for image, score in similarities 
            if score >= threshold
        ]
        
        # Sort by similarity score (descending)
        filtered_results.sort(key=lambda x: x[1], reverse=True)
        
        # Limit results
        final_results = filtered_results[:max_results]
        
        search_time = time.time() - start_time
        
        # Log search query
        search_query = self.log_search_query(
            query_image=query_image,
            user=user,
            threshold=threshold,
            max_results=max_results,
            results_count=len(final_results),
            search_time=search_time
        )
        
        # Log individual results
        self.log_similarity_results(search_query, final_results)
        
        return {
            'results': final_results,
            'search_time': search_time,
            'query_image': query_image,
            'threshold_used': threshold,
            'total_candidates': candidate_images.count(),
            'search_query_id': search_query.id if search_query else None
        }
    
    def get_image_features(self, image):
        """Get feature vector for an image"""
        try:
            if hasattr(image, 'features') and image.features:
                return np.array(image.features.feature_vector)
            else:
                # Try to get features from database
                feature_obj = ImageFeature.objects.filter(image=image).first()
                if feature_obj:
                    return np.array(feature_obj.feature_vector)
                return None
        except Exception as e:
            print(f"Error getting features for image {image.id}: {str(e)}")
            return None
    
    def calculate_similarities(self, query_features, candidate_images):
        """Calculate similarity scores between query and candidate images"""
        similarities = []
        
        for image in candidate_images:
            candidate_features = self.get_image_features(image)
            
            if candidate_features is not None:
                # Calculate cosine similarity
                similarity = cosine_similarity(
                    query_features.reshape(1, -1),
                    candidate_features.reshape(1, -1)
                )[0][0]
                
                similarities.append((image, float(similarity)))
        
        return similarities
    
    def log_search_query(self, query_image, user, threshold, max_results, results_count, search_time):
        """Log search query for analytics"""
        try:
            search_query = SearchQuery.objects.create(
                query_image=query_image,
                user=user,
                similarity_threshold=threshold,
                max_results=max_results,
                results_count=results_count,
                search_time=search_time
            )
            return search_query
        except Exception as e:
            print(f"Error logging search query: {str(e)}")
            return None
    
    def log_similarity_results(self, search_query, results):
        """Log individual similarity results"""
        if not search_query:
            return
        
        try:
            result_objects = []
            for rank, (image, score) in enumerate(results, 1):
                result_objects.append(
                    SimilarityResult(
                        search_query=search_query,
                        similar_image=image,
                        similarity_score=score,
                        rank=rank
                    )
                )
            
            # Bulk create for efficiency
            SimilarityResult.objects.bulk_create(result_objects)
            
        except Exception as e:
            print(f"Error logging similarity results: {str(e)}")


class BatchSimilaritySearcher:
    """
    Optimized searcher for batch operations or large datasets
    """
    
    def __init__(self):
        self.feature_cache = {}
        self.all_features_matrix = None
        self.all_images_list = None
        self.cache_built = False
    
    def build_feature_cache(self):
        """Build cache of all image features for faster batch searching"""
        print("Building feature cache...")
        start_time = time.time()
        
        # Get all images with features
        images_with_features = Image.objects.filter(
            features_extracted=True
        ).prefetch_related('features')
        
        features_list = []
        images_list = []
        
        for image in images_with_features:
            features = self.get_image_features(image)
            if features is not None:
                features_list.append(features)
                images_list.append(image)
        
        if features_list:
            self.all_features_matrix = np.vstack(features_list)
            self.all_images_list = images_list
            self.cache_built = True
        
        cache_time = time.time() - start_time
        print(f"Feature cache built in {cache_time:.2f}s ({len(features_list)} images)")
    
    def search_with_cache(self, query_features, threshold=0.7, max_results=20):
        """Search using cached features for better performance"""
        if not self.cache_built:
            self.build_feature_cache()
        
        if self.all_features_matrix is None:
            return []
        
        # Calculate similarities with all images at once
        similarities = cosine_similarity(
            query_features.reshape(1, -1),
            self.all_features_matrix
        )[0]
        
        # Create results with images and scores
        results = [
            (self.all_images_list[i], float(similarities[i]))
            for i in range(len(similarities))
            if similarities[i] >= threshold
        ]
        
        # Sort by similarity (descending)
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[:max_results]
    
    def get_image_features(self, image):
        """Get feature vector for an image (with caching)"""
        if image.id in self.feature_cache:
            return self.feature_cache[image.id]
        
        features = None
        try:
            if hasattr(image, 'features') and image.features:
                features = np.array(image.features.feature_vector)
            else:
                feature_obj = ImageFeature.objects.filter(image=image).first()
                if feature_obj:
                    features = np.array(feature_obj.feature_vector)
        except Exception as e:
            print(f"Error getting features for image {image.id}: {str(e)}")
        
        # Cache the result
        self.feature_cache[image.id] = features
        return features


def search_similar_images(query_image, threshold=None, max_results=None, user=None):
    """
    Convenience function for similarity search
    
    Args:
        query_image (Image): Query image object
        threshold (float): Minimum similarity threshold
        max_results (int): Maximum results to return
        user (User): User making the search
        
    Returns:
        dict: Search results
    """
    searcher = ImageSimilaritySearcher()
    return searcher.search_similar_images(
        query_image=query_image,
        threshold=threshold,
        max_results=max_results,
        user=user
    )


def extract_features_for_uploaded_image(image_path, model_name='resnet50'):
    """
    Extract features for a newly uploaded image
    
    Args:
        image_path (str): Path to image file
        model_name (str): Model to use for extraction
        
    Returns:
        tuple: (feature_vector, extraction_time) or (None, 0) on error
    """
    try:
        extractor = get_global_extractor()
        return extractor.extract_features(image_path)
    except Exception as e:
        print(f"Error extracting features: {str(e)}")
        return None, 0
    
    