"""apps/api/routes/products.py — Store product management and browsing."""

import os
from datetime import datetime
from flask import Blueprint, request, jsonify, g, send_file
from werkzeug.utils import secure_filename

from db import db
from db.models import (
    Product, ProductCategory, ProductVariant, ProductImage, GeneratedProductImage,
    Commercial, Cart, CartItem
)
from services.image_processor import (
    generate_product_angles, create_size_comparison, generate_multi_view_product,
    cleanup_old_generated_images
)
from middleware.auth import require_admin, require_member

products_bp = Blueprint("products", __name__)

# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "../../..", "uploads")
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
ALLOWED_VIDEO_EXTENSIONS = {"mp4", "webm", "mov", "avi"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_VIDEO_SIZE = 500 * 1024 * 1024  # 500 MB


def _ensure_upload_dirs():
    """Ensure upload directories exist."""
    os.makedirs(os.path.join(UPLOAD_FOLDER, "products"), exist_ok=True)
    os.makedirs(os.path.join(UPLOAD_FOLDER, "commercials"), exist_ok=True)


def _allowed_image(filename: str) -> bool:
    """Check if image file is allowed."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def _allowed_video(filename: str) -> bool:
    """Check if video file is allowed."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS


# ── Admin: Categories ────────────────────────────────────────────────────────

@products_bp.route("/admin/categories", methods=["GET"])
@require_admin
def list_categories():
    """Get all product categories."""
    categories = ProductCategory.query.order_by(ProductCategory.display_order).all()
    return jsonify([cat.to_dict() for cat in categories])


@products_bp.route("/admin/categories", methods=["POST"])
@require_admin
def create_category():
    """Create a new product category."""
    data = request.get_json()
    required = ["name"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    # Auto-generate slug from name
    slug = data.get("slug", data["name"].lower().replace(" ", "-"))

    existing = ProductCategory.query.filter_by(slug=slug).first()
    if existing:
        return jsonify({"error": "Category slug already exists"}), 409

    category = ProductCategory(
        name=data["name"],
        slug=slug,
        description=data.get("description"),
        image_url=data.get("image_url"),
        display_order=data.get("display_order", 0),
        is_active=data.get("is_active", True),
    )
    db.session.add(category)
    db.session.commit()
    return jsonify(category.to_dict()), 201


@products_bp.route("/admin/categories/<int:category_id>", methods=["PUT"])
@require_admin
def update_category(category_id):
    """Update a category."""
    category = ProductCategory.query.get_or_404(category_id)
    data = request.get_json()

    if "name" in data:
        category.name = data["name"]
    if "slug" in data:
        category.slug = data["slug"]
    if "description" in data:
        category.description = data["description"]
    if "image_url" in data:
        category.image_url = data["image_url"]
    if "display_order" in data:
        category.display_order = data["display_order"]
    if "is_active" in data:
        category.is_active = data["is_active"]

    db.session.commit()
    return jsonify(category.to_dict())


@products_bp.route("/admin/categories/<int:category_id>", methods=["DELETE"])
@require_admin
def delete_category(category_id):
    """Delete a category (only if no products)."""
    category = ProductCategory.query.get_or_404(category_id)
    if category.products.count() > 0:
        return jsonify({"error": "Cannot delete category with products"}), 409
    db.session.delete(category)
    db.session.commit()
    return jsonify({"message": "Category deleted"})


# ── Admin: Products ─────────────────────────────────────────────────────────

@products_bp.route("/admin/products", methods=["GET"])
@require_admin
def list_products_admin():
    """List all products (admin view)."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    category_id = request.args.get("category_id", type=int)

    query = Product.query
    if category_id:
        query = query.filter_by(category_id=category_id)

    pagination = query.order_by(Product.display_order, Product.created_at.desc()).paginate(
        page=page, per_page=per_page
    )
    return jsonify({
        "items": [p.to_dict(include_variants=True) for p in pagination.items],
        "total": pagination.total,
        "pages": pagination.pages,
        "current_page": page,
    })


@products_bp.route("/admin/products", methods=["POST"])
@require_admin
def create_product():
    """Create a new product."""
    data = request.get_json()
    required = ["sku", "name", "category_id", "base_price"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    # Check SKU uniqueness
    existing = Product.query.filter_by(sku=data["sku"]).first()
    if existing:
        return jsonify({"error": "SKU already exists"}), 409

    # Auto-generate slug
    slug = data.get("slug", data["name"].lower().replace(" ", "-"))
    existing_slug = Product.query.filter_by(slug=slug).first()
    if existing_slug:
        return jsonify({"error": "Slug already exists"}), 409

    product = Product(
        sku=data["sku"],
        name=data["name"],
        slug=slug,
        description=data.get("description"),
        category_id=data["category_id"],
        base_price=int(data["base_price"]),  # cents
        is_available=data.get("is_available", True),
        display_order=data.get("display_order", 0),
    )
    db.session.add(product)
    db.session.commit()
    return jsonify(product.to_dict(include_variants=True)), 201


@products_bp.route("/admin/products/<int:product_id>", methods=["GET"])
@require_admin
def get_product(product_id):
    """Get product details."""
    product = Product.query.get_or_404(product_id)
    return jsonify(product.to_dict(include_variants=True))


@products_bp.route("/admin/products/<int:product_id>", methods=["PUT"])
@require_admin
def update_product(product_id):
    """Update a product."""
    product = Product.query.get_or_404(product_id)
    data = request.get_json()

    if "name" in data:
        product.name = data["name"]
    if "slug" in data:
        product.slug = data["slug"]
    if "description" in data:
        product.description = data["description"]
    if "category_id" in data:
        product.category_id = data["category_id"]
    if "base_price" in data:
        product.base_price = int(data["base_price"])
    if "is_available" in data:
        product.is_available = data["is_available"]
    if "display_order" in data:
        product.display_order = data["display_order"]

    db.session.commit()
    return jsonify(product.to_dict(include_variants=True))


@products_bp.route("/admin/products/<int:product_id>", methods=["DELETE"])
@require_admin
def delete_product(product_id):
    """Delete a product."""
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    return jsonify({"message": "Product deleted"})


# ── Admin: Product Images ────────────────────────────────────────────────────

@products_bp.route("/admin/products/<int:product_id>/images", methods=["POST"])
@require_admin
def upload_product_image(product_id):
    """Upload an image for a product."""
    _ensure_upload_dirs()
    product = Product.query.get_or_404(product_id)

    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not _allowed_image(file.filename):
        return jsonify({"error": "File type not allowed"}), 400

    # Check file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > MAX_IMAGE_SIZE:
        return jsonify({"error": f"File too large (max {MAX_IMAGE_SIZE / 1024 / 1024}MB)"}), 400

    # Save file
    filename = secure_filename(f"{product.sku}_{datetime.utcnow().timestamp()}_{file.filename}")
    filepath = os.path.join(UPLOAD_FOLDER, "products", filename)
    file.save(filepath)

    # Create database record
    is_primary = request.form.get("is_primary", "false").lower() == "true"
    if is_primary:
        # Remove primary flag from other images
        ProductImage.query.filter_by(product_id=product_id, is_primary=True).update({"is_primary": False})

    image = ProductImage(
        product_id=product_id,
        image_url=f"/uploads/products/{filename}",
        alt_text=request.form.get("alt_text", product.name),
        is_primary=is_primary,
        display_order=request.form.get("display_order", 0, type=int),
    )
    db.session.add(image)
    db.session.commit()

    return jsonify(image.to_dict()), 201


@products_bp.route("/admin/products/<int:product_id>/images/<int:image_id>", methods=["DELETE"])
@require_admin
def delete_product_image(product_id, image_id):
    """Delete a product image."""
    image = ProductImage.query.get_or_404(image_id)
    if image.product_id != product_id:
        return jsonify({"error": "Image not found on this product"}), 404

    # Delete file if it exists
    if image.image_url.startswith("/uploads/"):
        filepath = os.path.join(UPLOAD_FOLDER, image.image_url.lstrip("/uploads/"))
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception:
                pass  # Log but don't fail

    db.session.delete(image)
    db.session.commit()
    return jsonify({"message": "Image deleted"})


# ── Admin: Product Variants ──────────────────────────────────────────────────

@products_bp.route("/admin/products/<int:product_id>/variants", methods=["POST"])
@require_admin
def create_variant(product_id):
    """Create a product variant (size, color, etc.)."""
    product = Product.query.get_or_404(product_id)
    data = request.get_json()
    required = ["variant_sku", "option_name", "option_value", "quantity_in_stock"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    existing = ProductVariant.query.filter_by(variant_sku=data["variant_sku"]).first()
    if existing:
        return jsonify({"error": "Variant SKU already exists"}), 409

    variant = ProductVariant(
        product_id=product_id,
        variant_sku=data["variant_sku"],
        option_name=data["option_name"],
        option_value=data["option_value"],
        price_override=int(data["price_override"]) if data.get("price_override") else None,
        quantity_in_stock=int(data["quantity_in_stock"]),
    )
    db.session.add(variant)
    db.session.commit()
    return jsonify(variant.to_dict()), 201


@products_bp.route("/admin/products/<int:product_id>/variants/<int:variant_id>", methods=["PUT"])
@require_admin
def update_variant(product_id, variant_id):
    """Update a product variant."""
    variant = ProductVariant.query.get_or_404(variant_id)
    if variant.product_id != product_id:
        return jsonify({"error": "Variant not found on this product"}), 404

    data = request.get_json()
    if "quantity_in_stock" in data:
        variant.quantity_in_stock = int(data["quantity_in_stock"])
    if "price_override" in data:
        variant.price_override = int(data["price_override"]) if data["price_override"] else None
    if "option_value" in data:
        variant.option_value = data["option_value"]

    db.session.commit()
    return jsonify(variant.to_dict())


@products_bp.route("/admin/products/<int:product_id>/variants/<int:variant_id>", methods=["DELETE"])
@require_admin
def delete_variant(product_id, variant_id):
    """Delete a product variant."""
    variant = ProductVariant.query.get_or_404(variant_id)
    if variant.product_id != product_id:
        return jsonify({"error": "Variant not found on this product"}), 404

    db.session.delete(variant)
    db.session.commit()
    return jsonify({"message": "Variant deleted"})


# ── Admin: Commercials ───────────────────────────────────────────────────────

@products_bp.route("/admin/commercials", methods=["GET"])
@require_admin
def list_commercials():
    """Get all commercials."""
    commercials = Commercial.query.order_by(Commercial.display_order).all()
    return jsonify([c.to_dict() for c in commercials])


@products_bp.route("/admin/commercials", methods=["POST"])
@require_admin
def create_commercial():
    """Create a commercial entry."""
    data = request.get_json()
    required = ["title", "video_url"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    commercial = Commercial(
        title=data["title"],
        description=data.get("description"),
        video_url=data["video_url"],
        thumbnail_url=data.get("thumbnail_url"),
        display_order=data.get("display_order", 0),
        is_active=data.get("is_active", True),
        video_duration_seconds=data.get("video_duration_seconds"),
    )
    db.session.add(commercial)
    db.session.commit()
    return jsonify(commercial.to_dict()), 201


@products_bp.route("/admin/commercials/<int:commercial_id>", methods=["PUT"])
@require_admin
def update_commercial(commercial_id):
    """Update a commercial."""
    commercial = Commercial.query.get_or_404(commercial_id)
    data = request.get_json()

    if "title" in data:
        commercial.title = data["title"]
    if "description" in data:
        commercial.description = data["description"]
    if "video_url" in data:
        commercial.video_url = data["video_url"]
    if "thumbnail_url" in data:
        commercial.thumbnail_url = data["thumbnail_url"]
    if "display_order" in data:
        commercial.display_order = data["display_order"]
    if "is_active" in data:
        commercial.is_active = data["is_active"]
    if "video_duration_seconds" in data:
        commercial.video_duration_seconds = data["video_duration_seconds"]

    db.session.commit()
    return jsonify(commercial.to_dict())


@products_bp.route("/admin/commercials/<int:commercial_id>", methods=["DELETE"])
@require_admin
def delete_commercial(commercial_id):
    """Delete a commercial."""
    commercial = Commercial.query.get_or_404(commercial_id)
    db.session.delete(commercial)
    db.session.commit()
    return jsonify({"message": "Commercial deleted"})


@products_bp.route("/admin/commercials/<int:commercial_id>/video", methods=["POST"])
@require_admin
def upload_commercial_video(commercial_id):
    """Upload a video file for a commercial."""
    _ensure_upload_dirs()
    commercial = Commercial.query.get_or_404(commercial_id)

    if "video" not in request.files:
        return jsonify({"error": "No video file provided"}), 400

    file = request.files["video"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not _allowed_video(file.filename):
        return jsonify({"error": "File type not allowed. Allowed: mp4, webm, mov, avi"}), 400

    # Check file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > MAX_VIDEO_SIZE:
        return jsonify({"error": f"File too large (max {MAX_VIDEO_SIZE / 1024 / 1024 / 1024}GB)"}), 400

    # Save file
    filename = secure_filename(f"commercial_{commercial_id}_{datetime.utcnow().timestamp()}_{file.filename}")
    filepath = os.path.join(UPLOAD_FOLDER, "commercials", filename)
    file.save(filepath)

    # Update commercial record
    commercial.video_url = f"/uploads/commercials/{filename}"
    db.session.commit()

    return jsonify({
        "message": "Video uploaded successfully",
        "video_url": commercial.video_url,
    }), 201


# ── Public: Browse Products ──────────────────────────────────────────────────

@products_bp.route("/categories", methods=["GET"])
def get_categories():
    """Get active product categories."""
    categories = ProductCategory.query.filter_by(is_active=True).order_by(
        ProductCategory.display_order
    ).all()
    return jsonify([cat.to_dict() for cat in categories])


@products_bp.route("/", methods=["GET"])
def list_products():
    """
    List products with filters.
    Query params: category_id, search, page, per_page
    """
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    category_id = request.args.get("category_id", type=int)
    search = request.args.get("search", "")

    query = Product.query.filter_by(is_available=True)

    if category_id:
        query = query.filter_by(category_id=category_id)

    if search:
        query = query.filter(
            (Product.name.ilike(f"%{search}%")) |
            (Product.description.ilike(f"%{search}%")) |
            (Product.sku.ilike(f"%{search}%"))
        )

    pagination = query.order_by(Product.display_order, Product.created_at.desc()).paginate(
        page=page, per_page=per_page
    )

    return jsonify({
        "items": [p.to_dict() for p in pagination.items],
        "total": pagination.total,
        "pages": pagination.pages,
        "current_page": page,
    })


@products_bp.route("/<int:product_id>", methods=["GET"])
def get_product_public(product_id):
    """Get product details (public)."""
    product = Product.query.get_or_404(product_id)
    if not product.is_available:
        return jsonify({"error": "Product not available"}), 404
    return jsonify(product.to_dict(include_variants=True))


@products_bp.route("/slug/<slug>", methods=["GET"])
def get_product_by_slug(slug):
    """Get product by slug (public)."""
    product = Product.query.filter_by(slug=slug).first_or_404()
    if not product.is_available:
        return jsonify({"error": "Product not available"}), 404
    return jsonify(product.to_dict(include_variants=True))


# ── Public: Commercials ──────────────────────────────────────────────────────

@products_bp.route("/commercials", methods=["GET"])
def get_commercials():
    """Get active commercials for homepage carousel."""
    commercials = Commercial.query.filter_by(is_active=True).order_by(
        Commercial.display_order
    ).all()
    return jsonify([c.to_dict() for c in commercials])


# ── Enhanced Product Images (AI Generation) ──────────────────────────────────

@products_bp.route("/admin/products/<int:product_id>/generate-angles", methods=["POST"])
@require_admin
def admin_generate_angles(product_id):
    """
    Generate multiple rotated product angle views.
    
    POST data (optional):
      - angles: list of rotation angles (default: [0, 90, 180, 270])
      - base_image_url: URL to base image (default: product's primary image)
    """
    product = Product.query.get_or_404(product_id)
    
    data = request.get_json() or {}
    angles = data.get("angles", [0, 90, 180, 270])
    
    # Get base image URL
    base_image_url = data.get("base_image_url")
    if not base_image_url:
        if not product.primary_image:
            return jsonify({"error": "No primary image found for product"}), 400
        base_image_url = product.primary_image.image_url
    
    try:
        generated_urls = generate_product_angles(product_id, base_image_url, angles)
        cleanup_old_generated_images(product_id, keep_count=5)
        
        return jsonify({
            "success": True,
            "product_id": product_id,
            "image_type": "angle",
            "generated_images": generated_urls,
            "angle_count": len(generated_urls),
        }), 201
    except Exception as e:
        return jsonify({"error": f"Image generation failed: {str(e)}"}), 500


@products_bp.route("/admin/products/<int:product_id>/generate-size-comparison", methods=["POST"])
@require_admin
def admin_generate_size_comparison(product_id):
    """
    Generate a visual size comparison guide.
    
    POST data (optional):
      - reference_type: 'quarter', 'credit_card', 'phone', 'shoe_size_9' (default: 'credit_card')
      - base_image_url: URL to base image (default: product's primary image)
    """
    product = Product.query.get_or_404(product_id)
    
    data = request.get_json() or {}
    reference_type = data.get("reference_type", "credit_card")
    
    # Get base image URL
    base_image_url = data.get("base_image_url")
    if not base_image_url:
        if not product.primary_image:
            return jsonify({"error": "No primary image found for product"}), 400
        base_image_url = product.primary_image.image_url
    
    try:
        image_url = create_size_comparison(product_id, base_image_url, reference_type)
        cleanup_old_generated_images(product_id, keep_count=5)
        
        if not image_url:
            return jsonify({"error": "Failed to generate size comparison"}), 500
        
        return jsonify({
            "success": True,
            "product_id": product_id,
            "image_type": "size_comparison",
            "reference_type": reference_type,
            "image_url": image_url,
        }), 201
    except Exception as e:
        return jsonify({"error": f"Size comparison generation failed: {str(e)}"}), 500


@products_bp.route("/admin/products/<int:product_id>/generate-multiview", methods=["POST"])
@require_admin
def admin_generate_multiview(product_id):
    """
    Generate complete product showcase with angles and size comparison.
    
    POST data (optional):
      - base_image_url: URL to base image (default: product's primary image)
    """
    product = Product.query.get_or_404(product_id)
    
    data = request.get_json() or {}
    base_image_url = data.get("base_image_url")
    
    if not base_image_url:
        if not product.primary_image:
            return jsonify({"error": "No primary image found for product"}), 400
        base_image_url = product.primary_image.image_url
    
    try:
        result = generate_multi_view_product(product_id, base_image_url)
        cleanup_old_generated_images(product_id, keep_count=5)
        
        return jsonify({
            "success": True,
            "product_id": product_id,
            "generated_views": result,
            "images_count": len(result.get("angles", [])) + (1 if result.get("size_comparison") else 0),
        }), 201
    except Exception as e:
        return jsonify({"error": f"Multiview generation failed: {str(e)}"}), 500


@products_bp.route("/products/<int:product_id>/generated-images", methods=["GET"])
def get_generated_images(product_id):
    """Get all generated images for a product (public)."""
    product = Product.query.get_or_404(product_id)
    
    generated = GeneratedProductImage.query.filter_by(product_id=product_id).order_by(
        GeneratedProductImage.generated_at.desc()
    ).all()
    
    # Group by type
    by_type = {}
    for img in generated:
        if img.image_type not in by_type:
            by_type[img.image_type] = []
        by_type[img.image_type].append(img.to_dict())
    
    return jsonify({
        "product_id": product_id,
        "generated_images_by_type": by_type,
        "total_generated": len(generated),
    })


@products_bp.route("/products/<int:product_id>/images/full", methods=["GET"])
def get_product_images_full(product_id):
    """Get product with all standard and generated images (public)."""
    product = Product.query.get_or_404(product_id)
    if not product.is_available:
        return jsonify({"error": "Product not available"}), 404
    
    generated = GeneratedProductImage.query.filter_by(product_id=product_id).order_by(
        GeneratedProductImage.generated_at.desc()
    ).all()
    
    # Group by type
    generated_by_type = {}
    for img in generated:
        if img.image_type not in generated_by_type:
            generated_by_type[img.image_type] = []
        generated_by_type[img.image_type].append(img.to_dict())
    
    product_dict = product.to_dict(include_variants=True)
    product_dict["generated_images"] = generated_by_type
    
    return jsonify(product_dict)
