# apps/search/models.py
from django.db import models
from django.contrib.auth.models import User
from images.models import Image


class SearchQuery(models.Model):
    """Model to log search queries for analytics"""
    
    query_image = models.ForeignKey(Image, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Search parameters
    similarity_threshold = models.FloatField(default=0.7)
    max_results = models.PositiveIntegerField(default=20)
    
    # Results
    results_count = models.PositiveIntegerField(default=0)
    search_time = models.FloatField(null=True, blank=True)  # Time in seconds
    
    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Search query {self.id} - {self.results_count} results"


class SimilarityResult(models.Model):
    """Model to store similarity search results"""
    
    search_query = models.ForeignKey(
        SearchQuery, 
        on_delete=models.CASCADE, 
        related_name='results'
    )
    similar_image = models.ForeignKey(
        Image, 
        on_delete=models.CASCADE,
        related_name='similarity_results'
    )
    
    similarity_score = models.FloatField()  # Between 0 and 1
    rank = models.PositiveIntegerField()    # Position in results (1, 2, 3...)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['search_query', 'rank']
        unique_together = ['search_query', 'similar_image']
        indexes = [
            models.Index(fields=['similarity_score']),
            models.Index(fields=['rank']),
        ]
    
    def __str__(self):
        return f"Result {self.rank}: {self.similarity_score:.3f} similarity"