import os
import shutil
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.core.files import File
from images.models import Image
from PIL import Image as PILImage


class Command(BaseCommand):
    help = 'Load seed images from data/seed_images directory into database'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing seed images before loading new ones',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of images to load (for testing)',
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='Skip images that already exist (based on filename)',
        )
    
    def handle(self, *args, **options):
        # Get seed images directory
        seed_dir = settings.SEED_IMAGES_DIR
        
        if not seed_dir.exists():
            raise CommandError(f'Seed directory not found: {seed_dir}')
        
        # Clear existing seed images if requested
        if options['clear']:
            self.stdout.write('Clearing existing seed images...')
            deleted_count = Image.objects.filter(is_seed_image=True).count()
            Image.objects.filter(is_seed_image=True).delete()
            self.stdout.write(
                self.style.SUCCESS(f'Deleted {deleted_count} existing seed images')
            )
        
        # Get all image files from seed directory
        image_files = self.get_image_files(seed_dir)
        
        if not image_files:
            self.stdout.write(
                self.style.WARNING('No image files found in seed directory')
            )
            return
        
        # Apply limit if specified
        if options['limit']:
            image_files = image_files[:options['limit']]
            self.stdout.write(f'Processing first {len(image_files)} images (limit applied)')
        
        self.stdout.write(f'Found {len(image_files)} images to process')
        
        # Process each image
        processed_count = 0
        skipped_count = 0
        error_count = 0
        
        for image_path in image_files:
            try:
                result = self.process_image(
                    image_path, 
                    skip_existing=options['skip_existing']
                )
                
                if result == 'processed':
                    processed_count += 1
                elif result == 'skipped':
                    skipped_count += 1
                    
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'Error processing {image_path}: {str(e)}')
                )
        
        # Print summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS(f'✓ Processed: {processed_count}'))
        if skipped_count > 0:
            self.stdout.write(self.style.WARNING(f'⚠ Skipped: {skipped_count}'))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'✗ Errors: {error_count}'))
        self.stdout.write('='*50)
    
    def get_image_files(self, directory):
        """Get all image files from directory"""
        image_extensions = {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'}
        image_files = []
        
        for file_path in directory.rglob('*'):
            if file_path.is_file() and file_path.suffix in image_extensions:
                image_files.append(file_path)
        
        return sorted(image_files)
    
    def process_image(self, image_path, skip_existing=False):
        """Process a single image file"""
        filename = image_path.name
        
        # Check if image already exists
        if skip_existing:
            existing = Image.objects.filter(
                original_filename=filename,
                is_seed_image=True
            ).first()
            
            if existing:
                self.stdout.write(f'Skipping existing: {filename}')
                return 'skipped'
        
        # Validate image
        if not self.validate_image(image_path):
            raise Exception(f'Invalid image: {filename}')
        
        # Create database record
        image_obj = Image()
        
        # Set basic info
        image_obj.title = filename.split('.')[0]  # Use filename without extension as title
        image_obj.original_filename = filename
        image_obj.is_seed_image = True
        
        # Open and save the image file
        with open(image_path, 'rb') as f:
            django_file = File(f, name=filename)
            image_obj.file.save(filename, django_file, save=False)
        
        # Save the object (this will trigger metadata extraction)
        image_obj.save()
        
        self.stdout.write(f'✓ Loaded: {filename} (ID: {image_obj.id})')
        return 'processed'
    
    def validate_image(self, image_path):
        """Validate image file"""
        try:
            # Check file size (max 2MB as per your requirement)
            file_size = image_path.stat().st_size
            max_size = getattr(settings, 'MAX_UPLOAD_SIZE', 2 * 1024 * 1024)
            
            if file_size > max_size:
                self.stdout.write(
                    self.style.WARNING(
                        f'Image {image_path.name} is {file_size/1024/1024:.1f}MB '
                        f'(max: {max_size/1024/1024:.1f}MB)'
                    )
                )
                return False
            
            # Try to open with PIL to verify it's a valid image
            with PILImage.open(image_path) as img:
                img.verify()  # Verify image integrity
                
                # Check dimensions (optional - prevent tiny images)
                width, height = img.size
                if width < 50 or height < 50:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Image {image_path.name} is too small ({width}x{height})'
                        )
                    )
                    return False
            
            return True
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Validation failed for {image_path.name}: {str(e)}')
            )
            return False