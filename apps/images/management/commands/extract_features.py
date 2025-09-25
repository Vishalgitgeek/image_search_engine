# apps/images/management/commands/extract_features.py
import os
import sys
import time
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from images.models import Image, ImageFeature
from ml_models.feature_extractor import get_feature_extractor


class Command(BaseCommand):
    help = 'Extract ML features from images using pre-trained models'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--model',
            type=str,
            default='resnet50',
            help='Model to use for feature extraction (resnet50, resnet18)',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=16,
            help='Batch size for processing (default: 16)',
        )
        parser.add_argument(
            '--reextract',
            action='store_true',
            help='Re-extract features for images that already have features',
        )
        parser.add_argument(
            '--seed-only',
            action='store_true',
            help='Only process seed images',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of images to process (for testing)',
        )
    
    def handle(self, *args, **options):
        model_name = options['model']
        batch_size = options['batch_size']
        reextract = options['reextract']
        seed_only = options['seed_only']
        limit = options['limit']
        
        # Get images to process
        images_query = Image.objects.all()
        
        if seed_only:
            images_query = images_query.filter(is_seed_image=True)
        
        if not reextract:
            images_query = images_query.filter(features_extracted=False)
        
        images_to_process = list(images_query.order_by('id'))
        
        if limit:
            images_to_process = images_to_process[:limit]
        
        if not images_to_process:
            self.stdout.write(
                self.style.SUCCESS('No images need feature extraction')
            )
            return
        
        self.stdout.write(f'Processing {len(images_to_process)} images')
        self.stdout.write(f'Model: {model_name}')
        self.stdout.write(f'Batch size: {batch_size}')
        
        # Initialize feature extractor
        try:
            self.stdout.write('Loading ML model...')
            extractor = get_feature_extractor(model_name)
            self.stdout.write(self.style.SUCCESS('Model loaded successfully'))
        except Exception as e:
            raise CommandError(f'Failed to load model: {str(e)}')
        
        # Process images in batches
        processed_count = 0
        error_count = 0
        total_time = 0
        
        for i in range(0, len(images_to_process), batch_size):
            batch = images_to_process[i:i + batch_size]
            batch_start_time = time.time()
            
            self.stdout.write(f'\nProcessing batch {i//batch_size + 1}...')
            
            for image_obj in batch:
                try:
                    # Check if image file exists
                    if not os.path.exists(image_obj.file.path):
                        self.stdout.write(
                            self.style.ERROR(f'File not found: {image_obj.file.path}')
                        )
                        error_count += 1
                        continue
                    
                    # Extract features
                    features, extraction_time = extractor.extract_features(image_obj.file.path)
                    
                    # Save or update features
                    feature_obj, created = ImageFeature.objects.get_or_create(
                        image=image_obj,
                        defaults={
                            'feature_vector': features,
                            'extraction_model': model_name,
                            'vector_size': len(features),
                            'extraction_time': extraction_time,
                        }
                    )
                    
                    if not created and reextract:
                        # Update existing features
                        feature_obj.feature_vector = features
                        feature_obj.extraction_model = model_name
                        feature_obj.vector_size = len(features)
                        feature_obj.extraction_time = extraction_time
                        feature_obj.save()
                    
                    # Mark image as processed
                    image_obj.features_extracted = True
                    image_obj.processing_error = ''  # Clear any previous errors
                    image_obj.save(update_fields=['features_extracted', 'processing_error'])
                    
                    processed_count += 1
                    total_time += extraction_time
                    
                    # Progress indicator
                    if processed_count % 10 == 0:
                        avg_time = total_time / processed_count
                        self.stdout.write(f'  Processed {processed_count}/{len(images_to_process)} (avg: {avg_time:.2f}s/image)')
                    
                except Exception as e:
                    error_count += 1
                    error_msg = f'Feature extraction error: {str(e)}'
                    
                    # Log error to image object
                    image_obj.processing_error = error_msg
                    image_obj.save(update_fields=['processing_error'])
                    
                    self.stdout.write(
                        self.style.ERROR(f'✗ Error processing {image_obj.original_filename}: {str(e)}')
                    )
            
            batch_time = time.time() - batch_start_time
            self.stdout.write(f'Batch completed in {batch_time:.2f}s')
        
        # Final summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS(f'✓ Successfully processed: {processed_count}'))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'✗ Errors: {error_count}'))
        
        if processed_count > 0:
            avg_time = total_time / processed_count
            self.stdout.write(f'Average extraction time: {avg_time:.3f}s per image')
            self.stdout.write(f'Total processing time: {total_time:.2f}s')
        
        self.stdout.write('='*60)
        
        # Verify results
        total_images = Image.objects.count()
        images_with_features = Image.objects.filter(features_extracted=True).count()
        self.stdout.write(f'\nDatabase status:')
        self.stdout.write(f'  Total images: {total_images}')
        self.stdout.write(f'  With features: {images_with_features}')
        self.stdout.write(f'  Pending: {total_images - images_with_features}')