import torch
import torch.nn as nn
import torchvision.transforms as transforms
import torchvision.models as models
from PIL import Image
import numpy as np
import time
import os
from django.conf import settings


class ImageFeatureExtractor:
    """
    Feature extractor using pre-trained ResNet50 model
    Converts images into 2048-dimensional feature vectors
    """
    
    def __init__(self, model_name='resnet50', device=None):
        self.model_name = model_name
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.transform = None
        self._load_model()
        self._setup_transforms()
    
    def _load_model(self):
        """Load pre-trained ResNet50 model"""
        print(f"Loading {self.model_name} model...")
        
        if self.model_name == 'resnet50':
            # Load pre-trained ResNet50
            model = models.resnet50(pretrained=True)
            
            # Remove the final classification layer to get features
            self.model = nn.Sequential(*list(model.children())[:-1])
            
        elif self.model_name == 'resnet18':
            # Lighter alternative for faster processing
            model = models.resnet18(pretrained=True)
            self.model = nn.Sequential(*list(model.children())[:-1])
            
        else:
            raise ValueError(f"Unsupported model: {self.model_name}")
        
        # Set to evaluation mode and move to device
        self.model.eval()
        self.model.to(self.device)
        print(f"Model loaded on {self.device}")
    
    def _setup_transforms(self):
        """Setup image preprocessing transforms"""
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),  # ResNet input size
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],  # ImageNet normalization
                std=[0.229, 0.224, 0.225]
            )
        ])
    
    def extract_features(self, image_path):
        """
        Extract feature vector from image
        
        Args:
            image_path (str): Path to image file
            
        Returns:
            tuple: (feature_vector, extraction_time)
        """
        start_time = time.time()
        
        try:
            # Load and preprocess image
            image = Image.open(image_path).convert('RGB')
            image_tensor = self.transform(image).unsqueeze(0)  # Add batch dimension
            image_tensor = image_tensor.to(self.device)
            
            # Extract features
            with torch.no_grad():
                features = self.model(image_tensor)
                
                # Flatten the features and convert to numpy
                features = features.view(features.size(0), -1)  # Flatten
                features = features.cpu().numpy()[0]  # Remove batch dim and move to CPU
                
                # Normalize features (L2 normalization)
                features = features / np.linalg.norm(features)
            
            extraction_time = time.time() - start_time
            return features.tolist(), extraction_time
            
        except Exception as e:
            print(f"Error extracting features from {image_path}: {str(e)}")
            raise
    
    def extract_features_batch(self, image_paths, batch_size=32):
        """
        Extract features from multiple images in batches
        
        Args:
            image_paths (list): List of image file paths
            batch_size (int): Number of images to process at once
            
        Yields:
            tuple: (image_path, feature_vector, extraction_time)
        """
        for i in range(0, len(image_paths), batch_size):
            batch_paths = image_paths[i:i + batch_size]
            batch_images = []
            valid_paths = []
            
            # Load and preprocess batch
            for path in batch_paths:
                try:
                    image = Image.open(path).convert('RGB')
                    image_tensor = self.transform(image)
                    batch_images.append(image_tensor)
                    valid_paths.append(path)
                except Exception as e:
                    print(f"Error loading {path}: {str(e)}")
                    continue
            
            if not batch_images:
                continue
            
            # Stack into batch tensor
            batch_tensor = torch.stack(batch_images).to(self.device)
            
            start_time = time.time()
            
            # Extract features for batch
            with torch.no_grad():
                features = self.model(batch_tensor)
                features = features.view(features.size(0), -1)  # Flatten
                features = features.cpu().numpy()
                
                # Normalize each feature vector
                for j in range(features.shape[0]):
                    features[j] = features[j] / np.linalg.norm(features[j])
            
            batch_time = time.time() - start_time
            avg_time = batch_time / len(valid_paths)
            
            # Yield results
            for path, feature_vector in zip(valid_paths, features):
                yield path, feature_vector.tolist(), avg_time


def get_feature_extractor(model_name='resnet50'):
    """
    Factory function to get feature extractor instance
    
    Args:
        model_name (str): Name of the model to use
        
    Returns:
        ImageFeatureExtractor: Configured feature extractor
    """
    return ImageFeatureExtractor(model_name=model_name)


def extract_single_image_features(image_path, model_name='resnet50'):
    """
    Convenience function to extract features from a single image
    
    Args:
        image_path (str): Path to image file
        model_name (str): Model to use for extraction
        
    Returns:
        tuple: (feature_vector, extraction_time)
    """
    extractor = get_feature_extractor(model_name)
    return extractor.extract_features(image_path)


# Global extractor instance (lazy loaded)
_global_extractor = None

def get_global_extractor():
    """Get or create global feature extractor instance"""
    global _global_extractor
    if _global_extractor is None:
        _global_extractor = get_feature_extractor()
    return _global_extractor