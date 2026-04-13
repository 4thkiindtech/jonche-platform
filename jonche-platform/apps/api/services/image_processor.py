"""
apps/api/services/image_processor.py
Generate enhanced product images using Pillow for Pygame-based transformations.

Features:
  - product_angles: Generate multiple rotated views from a base image
  - size_comparison: Create visual size guides showing shoe next to common items
  - image_with_shadow: Add drop shadow for professional appearance
"""

from __future__ import annotations

import io
import os
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter
import requests

from db import db
from db.models import GeneratedProductImage, Product


# Reference object sizes for comparison (in mm, approximate)
SIZE_REFERENCES = {
    "quarter": {"width": 24, "height": 24, "label": "Quarter"},
    "credit_card": {"width": 85, "height": 54, "label": "Credit Card"},
    "phone": {"width": 160, "height": 75, "label": "Smartphone"},
    "shoe_size_9": {"width": 300, "height": 120, "label": "Size 9 Shoe"},
}


def _download_image(url: str) -> Image.Image | None:
    """Download image from URL and return PIL Image object."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return Image.open(io.BytesIO(response.content)).convert("RGBA")
    except Exception as e:
        print(f"Error downloading image from {url}: {e}")
        return None


def _ensure_output_directory() -> Path:
    """Ensure generated images directory exists."""
    base_dir = Path(__file__).parent.parent / "static" / "generated-images"
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def _save_generated_image(image: Image.Image, product_id: int, image_type: str, parameters: dict) -> str:
    """Save generated image and return relative URL."""
    output_dir = _ensure_output_directory()
    filename = f"product_{product_id}_{image_type}_{datetime.utcnow().timestamp()}.png"
    filepath = output_dir / filename
    
    # Convert RGBA to RGB for PNG
    if image.mode == "RGBA":
        rgb_image = Image.new("RGB", image.size, (255, 255, 255))
        rgb_image.paste(image, mask=image.split()[3])
        rgb_image.save(filepath, "PNG", quality=95)
    else:
        image.save(filepath, "PNG", quality=95)
    
    # Store in database
    generated = GeneratedProductImage(
        product_id=product_id,
        image_type=image_type,
        image_url=f"/static/generated-images/{filename}",
        parameters=parameters,
        generated_at=datetime.utcnow(),
    )
    db.session.add(generated)
    db.session.commit()
    
    return f"/static/generated-images/{filename}"


def add_drop_shadow(image: Image.Image, offset: tuple = (5, 5), blur: int = 10, opacity: int = 100) -> Image.Image:
    """Add drop shadow to image."""
    # Create shadow layer
    shadow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    
    # Create shadow effect
    shadow_layer = Image.new("RGBA", (image.size[0] + 20, image.size[1] + 20), (0, 0, 0, 0))
    shadow_draw_layer = ImageDraw.Draw(shadow_layer)
    shadow_draw_layer.rectangle(
        [(10, 10), (image.size[0] + 10, image.size[1] + 10)],
        fill=(0, 0, 0, opacity)
    )
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=blur))
    
    # Composite shadow first, then image
    result = Image.new("RGBA", (image.size[0] + 20, image.size[1] + 20), (255, 255, 255, 0))
    result.paste(shadow_layer, (0, 0), shadow_layer)
    result.paste(image, (10, 10), image if image.mode == "RGBA" else None)
    
    return result


def generate_product_angles(product_id: int, base_image_url: str, angles: list = None) -> list[str]:
    """
    Generate multiple rotated product angles from a base image.
    
    Args:
        product_id: Product database ID
        base_image_url: URL to base product image
        angles: List of rotation angles (default: [0, 90, 180, 270]) for 4-view
    
    Returns:
        List of generated image URLs
    """
    if angles is None:
        angles = [0, 90, 180, 270]
    
    base_image = _download_image(base_image_url)
    if not base_image:
        return []
    
    # Resize for consistency
    base_image.thumbnail((400, 400), Image.Resampling.LANCZOS)
    
    generated_urls = []
    
    for angle in angles:
        # Rotate image
        rotated = base_image.rotate(angle, expand=True, fillcolor=(255, 255, 255, 0))
        
        # Add shadow
        with_shadow = add_drop_shadow(rotated, offset=(4, 4), blur=8, opacity=80)
        
        # Create white background canvas
        canvas = Image.new("RGB", (500, 500), (255, 255, 255))
        canvas.paste(with_shadow, (250 - with_shadow.width // 2, 250 - with_shadow.height // 2), with_shadow)
        
        # Save and store
        url = _save_generated_image(
            canvas,
            product_id,
            "angle",
            {"angle": angle, "rotation_count": len(angles)}
        )
        generated_urls.append(url)
    
    return generated_urls


def create_size_comparison(product_id: int, base_image_url: str, reference_type: str = "credit_card") -> str:
    """
    Create visual size comparison showing shoe next to common reference objects.
    
    Args:
        product_id: Product database ID
        base_image_url: URL to product image
        reference_type: Type of reference object ('quarter', 'credit_card', 'phone', 'shoe_size_9')
    
    Returns:
        URL to generated comparison image
    """
    if reference_type not in SIZE_REFERENCES:
        reference_type = "credit_card"
    
    base_image = _download_image(base_image_url)
    if not base_image:
        return ""
    
    base_image.thumbnail((250, 300), Image.Resampling.LANCZOS)
    ref = SIZE_REFERENCES[reference_type]
    
    # Calculate reference object size proportional to shoe
    shoe_width = base_image.width
    ref_width = int((ref["width"] / 300) * shoe_width)  # 300mm ≈ typical shoe width
    ref_height = int((ref["height"] / 300) * shoe_width)
    
    # Create canvas for comparison
    canvas_width = shoe_width + ref_width + 80  # shoe + ref + padding
    canvas_height = max(base_image.height, ref_height) + 100
    
    canvas = Image.new("RGB", (canvas_width, canvas_height), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    
    # Add title
    try:
        from PIL import ImageFont
        font = ImageFont.load_default()
    except:
        font = None
    
    title = f"Size Comparison ({ref['label']})"
    draw.text((20, 10), title, fill=(0, 0, 0), font=font)
    
    # Paste shoe
    shoe_y = (canvas_height - base_image.height) // 2
    canvas.paste(base_image, (20, shoe_y), base_image if base_image.mode == "RGBA" else None)
    
    # Draw reference object (as colored rectangle with label)
    ref_x = shoe_width + 40
    ref_y = (canvas_height - ref_height) // 2
    
    # Draw colored rectangle for reference
    draw.rectangle(
        [(ref_x, ref_y), (ref_x + ref_width, ref_y + ref_height)],
        fill=(200, 220, 255),
        outline=(50, 100, 200),
        width=2
    )
    
    # Add reference label
    ref_label_y = ref_y + ref_height + 10
    draw.text((ref_x, ref_label_y), ref["label"], fill=(0, 0, 0), font=font)
    
    # Add dimension line
    draw.line([(ref_x - 10, ref_y - 5), (ref_x - 10, ref_y + ref_height + 5)], fill=(100, 100, 100), width=2)
    draw.line([(ref_x - 15, ref_y - 5), (ref_x - 5, ref_y - 5)], fill=(100, 100, 100), width=2)
    draw.line([(ref_x - 15, ref_y + ref_height + 5), (ref_x - 5, ref_y + ref_height + 5)], fill=(100, 100, 100), width=2)
    
    url = _save_generated_image(
        canvas,
        product_id,
        "size_comparison",
        {"reference_type": reference_type}
    )
    
    return url


def generate_multi_view_product(product_id: int, base_image_url: str) -> dict[str, str]:
    """
    Generate a complete product showcase with angles and size comparison.
    
    Returns:
        Dictionary with generated image URLs:
        {
            "angles": [url1, url2, url3, url4],
            "size_comparison": url,
            "created_at": timestamp
        }
    """
    result = {
        "angles": generate_product_angles(product_id, base_image_url, [0, 45, 90, 135]),
        "size_comparison": create_size_comparison(product_id, base_image_url, "credit_card"),
        "created_at": datetime.utcnow().isoformat(),
    }
    
    return result


def cleanup_old_generated_images(product_id: int, keep_count: int = 5) -> int:
    """
    Clean up old generated images for a product, keeping only the most recent N.
    
    Returns:
        Number of images deleted
    """
    # Get old images (ordered by generated_at, oldest first)
    old_images = GeneratedProductImage.query.filter_by(product_id=product_id).order_by(
        GeneratedProductImage.generated_at
    ).all()
    
    if len(old_images) <= keep_count:
        return 0
    
    images_to_delete = old_images[:-keep_count]
    deleted_count = 0
    
    for img in images_to_delete:
        try:
            # Delete file
            filepath = Path(__file__).parent.parent / "static" / img.image_url.lstrip("/")
            if filepath.exists():
                filepath.unlink()
            
            # Delete database record
            db.session.delete(img)
            deleted_count += 1
        except Exception as e:
            print(f"Error deleting image {img.image_url}: {e}")
    
    db.session.commit()
    return deleted_count
