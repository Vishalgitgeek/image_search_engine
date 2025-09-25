# Seed Images Directory

## Structure
- Place your pre-stored images in category folders
- Supported formats: JPG, JPEG, PNG, GIF, BMP
- Recommended: 100-500 images per category for good results

## Categories
- `electronics/` - Phones, laptops, gadgets
- `clothing/` - Shirts, shoes, accessories  
- `furniture/` - Chairs, tables, sofas
- `nature/` - Landscapes, animals, plants
- `misc/` - Everything else

## Image Guidelines
- Resolution: 224x224 to 1024x1024 (will be resized)
- File size: Under 5MB each
- Clear, well-lit images work best
- Avoid watermarked images

## Loading Images
```bash
python manage.py load_seed_images
python manage.py extract_features