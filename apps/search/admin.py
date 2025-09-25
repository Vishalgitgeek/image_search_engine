from django.contrib import admin
from django.utils.html import format_html
from .models import SearchQuery, SimilarityResult


@admin.register(SearchQuery)
class SearchQueryAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'query_image_thumbnail',
        'user',
        'results_count',
        'search_time',
        'similarity_threshold',
        'created_at'
    ]
    
    list_filter = [
        'created_at',
        'user',
        'similarity_threshold'
    ]
    
    search_fields = [
        'query_image__title',
        'query_image__original_filename'
    ]
    
    readonly_fields = [
        'query_image',
        'user',
        'similarity_threshold',
        'max_results',
        'results_count',
        'search_time',
        'created_at'
    ]
    
    def query_image_thumbnail(self, obj):
        """Display thumbnail of query image"""
        if obj.query_image and obj.query_image.file:
            return format_html(
                '<img src="{}" style="width: 40px; height: 40px; object-fit: cover; border-radius: 4px;" />',
                obj.query_image.file.url
            )
        return "No Image"
    query_image_thumbnail.short_description = "Query Image"


@admin.register(SimilarityResult)
class SimilarityResultAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'search_query_id',
        'rank',
        'similar_image_thumbnail',
        'similarity_score',
        'created_at'
    ]
    
    list_filter = [
        'rank',
        'similarity_score',
        'created_at'
    ]
    
    readonly_fields = [
        'search_query',
        'similar_image',
        'similarity_score',
        'rank',
        'created_at'
    ]
    
    def similar_image_thumbnail(self, obj):
        """Display thumbnail of similar image"""
        if obj.similar_image and obj.similar_image.file:
            return format_html(
                '<img src="{}" style="width: 40px; height: 40px; object-fit: cover; border-radius: 4px;" />',
                obj.similar_image.file.url
            )
        return "No Image"
    similar_image_thumbnail.short_description = "Similar Image"
    
    def search_query_id(self, obj):
        """Display search query ID as link"""
        return format_html(
            '<a href="/admin/search/searchquery/{}/change/">{}</a>',
            obj.search_query.id,
            obj.search_query.id
        )
    search_query_id.short_description = "Search Query"