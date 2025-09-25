from django.urls import path
from . import views

app_name = 'images'

urlpatterns = [
    path('', views.ImageListView.as_view(), name='list'),
    path('<int:pk>/', views.ImageDetailView.as_view(), name='detail'),
    path('<int:pk>/delete/', views.ImageDeleteView.as_view(), name='delete'),
    path('upload/', views.ImageUploadView.as_view(), name='upload'),
    
    # API endpoints
    path('api/', views.ImageListAPIView.as_view(), name='api_list'),
    path('api/<int:pk>/', views.ImageDetailAPIView.as_view(), name='api_detail'),
]

