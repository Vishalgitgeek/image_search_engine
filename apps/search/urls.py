from django.urls import path
from . import views

app_name = 'search'

urlpatterns = [
    path('', views.SearchView.as_view(), name='search'),
    path('similar/<int:image_id>/', views.SimilarImagesView.as_view(), name='similar'),
    path('results/', views.SearchResultsView.as_view(), name='results'),
    
    # API endpoints
    path('api/similar/<int:image_id>/', views.SimilarImagesAPIView.as_view(), name='api_similar'),
    path('api/search/', views.SearchAPIView.as_view(), name='api_search'),
]