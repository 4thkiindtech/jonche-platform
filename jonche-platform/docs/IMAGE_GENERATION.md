# Enhanced Product Image Generation Guide

## Overview

This integration adds AI-powered image enhancement capabilities using Pillow (PIL) for generating:
1. **360° Product Angles** - Multiple rotated views of the shoe from different angles
2. **Size Comparison Graphics** - Visual guides showing shoe size relative to common reference items

## Features Implemented

### 1. Product Angle Generation
Generates 4+ rotated views of a product image with professional drop shadows and consistent white backgrounds.

**API Endpoint:**
```
POST /api/admin/products/{product_id}/generate-angles
```

**Request Body (optional):**
```json
{
  "angles": [0, 45, 90, 135, 180, 225, 270, 315],  // Rotation angles in degrees
  "base_image_url": "https://..."  // Optional: Use specific image instead of primary
}
```

**Response:**
```json
{
  "success": true,
  "product_id": 5,
  "image_type": "angle",
  "generated_images": [
    "/static/generated-images/product_5_angle_1712702400.png",
    "/static/generated-images/product_5_angle_1712702401.png",
    ...
  ],
  "angle_count": 8
}
```

### 2. Size Comparison Graphics
Creates a visual guide showing the shoe alongside common reference objects for scale:
- Quarter (24mm)
- Credit Card (85×54mm)
- Smartphone (160×75mm)
- Size 9 Shoe (300×120mm)

**API Endpoint:**
```
POST /api/admin/products/{product_id}/generate-size-comparison
```

**Request Body (optional):**
```json
{
  "reference_type": "credit_card",  // quarter, credit_card, phone, shoe_size_9
  "base_image_url": "https://..."
}
```

**Response:**
```json
{
  "success": true,
  "product_id": 5,
  "image_type": "size_comparison",
  "reference_type": "credit_card",
  "image_url": "/static/generated-images/product_5_size_comparison_1712702402.png"
}
```

### 3. Multiview (All-in-One)
Generates both angle views and size comparison in a single request.

**API Endpoint:**
```
POST /api/admin/products/{product_id}/generate-multiview
```

**Response:**
```json
{
  "success": true,
  "product_id": 5,
  "generated_views": {
    "angles": [
      "/static/generated-images/...",
      "/static/generated-images/...",
      ...
    ],
    "size_comparison": "/static/generated-images/...",
    "created_at": "2026-04-09T12:34:56.789Z"
  },
  "images_count": 5
}
```

## Database Schema

### GeneratedProductImage Table
```sql
CREATE TABLE generated_product_images (
  id INTEGER PRIMARY KEY,
  product_id INTEGER NOT NULL REFERENCES products(id),
  image_type VARCHAR(50),  -- 'angle', 'size_comparison'
  image_url VARCHAR(500),
  parameters JSON,  -- e.g., {"angle": 45, "reference_type": "credit_card"}
  generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Frontend Integration

### JavaScript Utilities
File: `/apps/web/static/js/image-generator.js`

```javascript
// Generate angles for a product
await ImageGenerator.generateAngles(productId, {
  angles: [0, 90, 180, 270],
  baseImageUrl: 'https://...'
});

// Generate size comparison
await ImageGenerator.generateSizeComparison(productId, {
  referenceType: 'credit_card',
  baseImageUrl: 'https://...'
});

// Generate all at once
await ImageGenerator.generateMultiview(productId, {
  baseImageUrl: 'https://...'
});

// Show notification toast
ImageGenerator.showToast('Generation complete!', 'success');
```

### HTML Admin Buttons
Add these buttons to your admin product edit template:

```html
<div class="btn-group" role="group">
  <button type="button" 
          id="generateAnglesBtn" 
          class="btn btn-info"
          data-product-id="{{ product.id }}">
    <i class="fas fa-sync-alt"></i> Generate Angles
  </button>
  
  <button type="button" 
          id="generateSizeComparisonBtn" 
          class="btn btn-info"
          data-product-id="{{ product.id }}">
    <i class="fas fa-expand"></i> Size Comparison
  </button>
  
  <button type="button" 
          id="generateAllBtn" 
          class="btn btn-success"
          data-product-id="{{ product.id }}">
    <i class="fas fa-magic"></i> Generate All
  </button>
</div>

<script src="/static/js/image-generator.js"></script>
```

### Product Detail Page
Automatically displays generated images in the "Enhanced Views" section:

```html
<!-- Displayed in product_detail.html -->
<div class="enhanced-views">
  <h6><i class="fas fa-magic"></i> Enhanced Views</h6>
  
  <!-- 360° Angles (thumbnail grid) -->
  <div id="anglesContainer"></div>
  
  <!-- Size Comparison (clickable preview) -->
  <div id="sizeComparisonContainer"></div>
</div>
```

## Getting All Generated Images for a Product

**Public API:**
```
GET /api/products/{product_id}/generated-images
```

**Response:**
```json
{
  "product_id": 5,
  "generated_images_by_type": {
    "angle": [
      {
        "id": 1,
        "image_url": "/static/generated-images/...",
        "parameters": {"angle": 0},
        "generated_at": "2026-04-09T12:34:56Z"
      },
      ...
    ],
    "size_comparison": [
      {
        "id": 2,
        "image_url": "/static/generated-images/...",
        "parameters": {"reference_type": "credit_card"},
        "generated_at": "2026-04-09T12:34:57Z"
      }
    ]
  },
  "total_generated": 5
}
```

**Full Product with Images:**
```
GET /api/products/{product_id}/images/full
```

Returns complete product data + generated images grouped by type.

## Image Storage

- **Location:** `apps/api/static/generated-images/`
- **Naming:** `product_{id}_{type}_{timestamp}.png`
- **Cleanup:** Automatic retention of 5 most recent per type per product
- **Size:** Optimized (~100-200KB per image)

## Configuration

### Environment Variables
```env
# None required - uses built-in defaults
```

### Reference Object Sizes
Edit in `/apps/api/services/image_processor.py`:

```python
SIZE_REFERENCES = {
    "quarter": {"width": 24, "height": 24, "label": "Quarter"},
    "credit_card": {"width": 85, "height": 54, "label": "Credit Card"},
    "phone": {"width": 160, "height": 75, "label": "Smartphone"},
    "shoe_size_9": {"width": 300, "height": 120, "label": "Size 9 Shoe"},
}
```

## Performance Considerations

- **Generation Time:** 2-5 seconds per set (4 angles + 1 size comparison)
- **File Size:** ~150KB per angle image, ~200KB per comparison
- **Recommended:** Generate during off-peak hours for bulk updates
- **Caching:** Images served directly from `/static/generated-images/`
- **CDN:** Can be cached via edge providers for fast delivery

## Installation & Dependencies

### Requirements
```
Pillow==10.1.0
requests==2.31.0
```

### Migration
Run database migration to create `generated_product_images` table:
```bash
flask db upgrade
```

### Static Directory
Ensure `/apps/api/static/generated-images/` exists with write permissions:
```bash
mkdir -p apps/api/static/generated-images
chmod 755 apps/api/static/generated-images
```

## Troubleshooting

### Images Not Generating
- Check product has a primary image set
- Verify base image URL is accessible
- Check `/apps/api/static/generated-images/` permissions
- Review `/apps/api/services/image_processor.py` logs

### Generated Images Not Showing in Frontend
- Clear browser cache
- Verify API endpoint: `/api/products/{id}/generated-images`
- Check network tab for 404 errors
- Verify JavaScript file `/apps/web/static/js/image-generator.js` is loaded

### Slow Generation
- Large base images = slower processing
- First generation is slower (disk I/O)
- Consider batch generation during off-hours
- Check available disk space

## Future Enhancements

- **Batch Processing:** Generate for multiple products at once
- **3D Integration:** Combine with Panda3D for interactive 3D
- **AR Preview:** Save angle images for AR/VR integration
- **Custom Reference Objects:** Admin-defined size references
- **Watermarking:** Auto-add branding to generated images
- **Alternative Backgrounds:** Lifestyle/context backgrounds
- **Animation:** Create GIFs from angle sequences

## API Usage Examples

### cURL
```bash
# Generate angles
curl -X POST http://localhost:5001/api/admin/products/5/generate-angles \
  -H "Content-Type: application/json" \
  -d 'Angles: [0, 90, 180, 270]}'

# Generate size comparison
curl -X POST http://localhost:5001/api/admin/products/5/generate-size-comparison \
  -H "Content-Type: application/json" \
  -d '{"reference_type": "credit_card"}'
```

### Python
```python
import requests

# Generate multiview
response = requests.post(
    'http://localhost:5001/api/admin/products/5/generate-multiview',
    json={'base_image_url': 'https://...'},
    headers={'Authorization': 'Bearer YOUR_TOKEN'}
)
print(response.json())
```

### JavaScript
```javascript
// Use ImageGenerator utility
await ImageGenerator.generateAngles(5);
await ImageGenerator.generateSizeComparison(5);
ImageGenerator.showToast('Done!', 'success');
```

## Support & Questions

For issues or feature requests, check:
1. `apps/api/services/image_processor.py` - Image generation logic
2. `apps/api/routes/products.py` - API endpoints
3. `apps/web/static/js/image-generator.js` - Frontend utilities
4. `apps/web/templates/product_detail.html` - Display template
