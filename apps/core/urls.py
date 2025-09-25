from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', view = views.IndexView.as_view(), name = 'home'),
    path('upload/', view = views.UploadView.as_view(), name = 'upload_image'),
    path('gallery/', view =  views.GalleryView.as_view(), name = 'gallery')
]
