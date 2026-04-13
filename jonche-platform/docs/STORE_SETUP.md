# 🛍️ Jonche Platform - Store System Setup Guide

## Overview

Your Jonche platform now includes a complete e-commerce store system with:
- **Product Management** - Upload and manage products with images and variants
- **Product Categories** - Organize products into collections
- **Shopping Cart** - Full cart management with real-time updates
- **Commercials** - Homepage video carousel for showcasing commercials
- **Admin Dashboard** - Comprehensive store management interface

---

## Quick Start

### 1. Access Admin Store Management

Navigate to: **`/admin/store`**

This is where you'll manage all store content. You'll see three tabs:
- **Products** - Create, edit, and delete products
- **Categories** - Organize products into collections
- **Commercials** - Upload and manage commercials

### 2. Create Your First Category

1. Go to the **Categories** tab
2. Click **"New Category"**
3. Enter:
   - **Category Name** (e.g., "T-Shirts", "Limited Drops", "Accessories")
   - **Description** (optional)
   - Check **Active** to make it visible

Click **Create Category**

### 3. Create Your First Product

1. Click the **"New Product"** button (top right)
2. Fill in the following fields:

| Field | Description |
|-------|-------------|
| **SKU** | Unique stock-keeping unit (e.g., `TSHIRT-001`) |
| **Product Name** | Display name (e.g., "Jonche Classic T-Shirt") |
| **Category** | Select from created categories |
| **Base Price** | Price in USD (e.g., `29.99`) |
| **Description** | Product details and specs |
| **Available** | Check to make visible to customers |

3. Click **Create Product**
4. Once created, you can:
   - **Upload Images** - Add multiple product photos
   - **Create Variants** - Add sizes, colors, or other options
   - Each variant can have different prices and inventory levels

### 4. Upload Product Images

After creating a product:

1. Go to the product detail page (Admin Store → Products → Edit)
2. Click **"Upload Image"**
3. Select an image file (JPG, PNG, GIF, WebP)
4. Enter alt text for accessibility
5. Check **"Primary Image"** if this is the main product photo
6. Click **Upload**

Upload multiple images and arrange them in order.

### 5. Create Product Variants

Variants allow you to offer options like sizes, colors, or materials:

1. In product details, scroll to **"Variants"** section
2. Click **"Add Variant"**
3. Fill in:
   - **Option Name** (e.g., "Size" or "Color")
   - **Option Value** (e.g., "Medium" or "Blue")
   - **Variant SKU** (unique identifier)
   - **Quantity in Stock** (inventory count)
   - **Price Override** (optional - leave blank to use base price)

4. Click **Create Variant**

**Example**: For a T-Shirt, create variants like:
- Size: Small (100 in stock)
- Size: Medium (150 in stock)
- Size: Large (120 in stock)
- Size: XL (80 in stock)

### 6. Create & Upload Commercials

**Step 1: Create Commercial Entry**
1. Go to **`/admin/store`** → **Commercials** tab
2. Click **"New Commercial"**
3. Fill in:
   - **Title** (e.g., "Summer Campaign 2024")
   - **Description** (optional)
   - **Video URL** (link to your video)
   - **Thumbnail URL** (optional preview image)
   - Check **Active** to display on homepage

**Step 2: Upload Video File (Optional)**
- If you have a video file, you can upload it directly
- Open the commercial and click **"Upload Video"**
- Supported formats: MP4, WebM, MOV, AVI
- Max file size: 500MB

**Homepage Display**: Commercials appear as a carousel on the store homepage (`/store`)

---

## Customer-Facing Pages

### 📄 Store Homepage
**URL**: `/store`
- Displays active commercials in an auto-rotating carousel
- Shows featured products
- Category navigation
- Call-to-action buttons

### 🛒 Browse Products
**URL**: `/store/products`
- Full product catalog
- Search and filter by category
- Sort by: newest, name, price
- Responsive grid layout

### 📦 Product Detail
**URL**: `/store/product/{product-id}`
- Full product information
- Multiple images with gallery
- Select variants (sizes/colors/etc)
- Add to cart functionality
- Shipping and return info

### 🛍️ Shopping Cart
**URL**: `/store/cart`
- View all items in cart
- Modify quantities
- Remove items
- Order summary with totals
- Proceed to checkout

### 💳 Checkout
**URL**: `/store/checkout` (requires login)
- Shipping information form
- Billing address
- Payment processing
- Order summary

---

## API Endpoints

### Admin Endpoints (Requires Authentication)

#### Categories
```bash
GET    /api/products/admin/categories          # List all categories
POST   /api/products/admin/categories          # Create category
PUT    /api/products/admin/categories/{id}    # Update category
DELETE /api/products/admin/categories/{id}    # Delete category
```

#### Products
```bash
GET    /api/products/admin/products            # List products (paginated)
POST   /api/products/admin/products            # Create product
GET    /api/products/admin/products/{id}      # Get product details
PUT    /api/products/admin/products/{id}      # Update product
DELETE /api/products/admin/products/{id}      # Delete product
```

#### Product Images
```bash
POST   /api/products/admin/products/{id}/images              # Upload image
DELETE /api/products/admin/products/{id}/images/{image_id}  # Delete image
```

#### Variants
```bash
POST   /api/products/admin/products/{id}/variants              # Create variant
PUT    /api/products/admin/products/{id}/variants/{var_id}    # Update variant
DELETE /api/products/admin/products/{id}/variants/{var_id}    # Delete variant
```

#### Commercials
```bash
GET    /api/products/admin/commercials        # List all commercials
POST   /api/products/admin/commercials        # Create commercial
PUT    /api/products/admin/commercials/{id}  # Update commercial
DELETE /api/products/admin/commercials/{id}  # Delete commercial
POST   /api/products/admin/commercials/{id}/video  # Upload video
```

### Public Endpoints (No Authentication)

#### Browse
```bash
GET    /api/products/categories               # List active categories
GET    /api/products/                         # List products (filtered/paginated)
GET    /api/products/{id}                    # Get product details
GET    /api/products/slug/{slug}             # Get product by slug
GET    /api/products/commercials             # List active commercials
```

#### Store
```bash
GET    /api/store/cart                        # Get current cart
POST   /api/store/cart/init                   # Initialize cart
POST   /api/store/cart/items                  # Add item to cart
PUT    /api/store/cart/items/{item_id}       # Update cart item
DELETE /api/store/cart/items/{item_id}        # Remove from cart
POST   /api/store/cart/clear                  # Clear cart
```

---

## Database Schema

### New Tables

**product_categories**
- id (PK)
- name
- slug
- description
- image_url
- display_order
- is_active
- created_at

**products**
- id (PK)
- sku (unique)
- name
- slug
- description
- category_id (FK)
- base_price (cents)
- is_available
- display_order
- created_at
- updated_at

**product_variants**
- id (PK)
- product_id (FK)
- variant_sku (unique)
- option_name (e.g., "size", "color")
- option_value (e.g., "M", "Blue")
- price_override (cents, nullable)
- quantity_in_stock
- created_at

**product_images**
- id (PK)
- product_id (FK)
- image_url
- alt_text
- is_primary
- display_order
- uploaded_at

**commercials**
- id (PK)
- title
- description
- video_url
- thumbnail_url
- display_order
- is_active
- video_duration_seconds
- created_at

**carts**
- id (PK)
- member_id (FK, nullable for guests)
- session_token (unique, nullable for members)
- status (active/completed/abandoned)
- expires_at
- created_at
- updated_at

**cart_items**
- id (PK)
- cart_id (FK)
- product_id (FK)
- variant_id (FK, nullable)
- quantity
- unit_price_cents
- created_at

---

## File Storage

Uploaded files are stored locally in:

```
uploads/
├── products/          # Product images
│   └── [sku]_[timestamp]_[filename]
└── commercials/       # Commercial videos
    └── commercial_[id]_[timestamp]_[filename]
```

To change storage to cloud (Azure Blob, AWS S3):
1. Edit `apps/api/routes/products.py`
2. Replace file save logic with cloud SDK calls
3. Update file URLs to point to cloud storage

---

## Features & Capabilities

✅ **Multi-Image Support** - Upload multiple photos per product with ordering

✅ **Flexible Variants** - Create any type of option (size, color, material, etc.)

✅ **Real-time Inventory** - Track stock for each variant

✅ **Price Flexibility** - Base price + per-variant overrides

✅ **Category Organization** - Organize products into logical collections

✅ **Video Carousel** - Auto-rotating commercial videos on homepage

✅ **Shopping Cart** - Guest and member cart support with session persistence

✅ **Search & Filter** - Find products by category, price range, search terms

✅ **Responsive Design** - Mobile-friendly UI for all pages

✅ **Admin Dashboard** - Complete store management interface

---

## Next Steps

### Enhancement Ideas

1. **Payment Integration**
   - Integrate Stripe for real payment processing
   - Webhook handling for payment confirmations

2. **Order Management**
   - Create Order model to track store purchases
   - Order history for members
   - Admin order dashboard

3. **Inventory Management**
   - Low stock alerts
   - Automatic reorder points
   - Stock movement reports

4. **Customer Reviews**
   - Rating and review system
   - Photo uploads with reviews
   - moderation tools

5. **Email Notifications**
   - Order confirmation emails
   - Shipping notifications
   - Inventory alerts

6. **Analytics**
   - Product performance metrics
   - Sales reports
   - Customer insights

7. **Promotions**
   - Discount codes
   - Bulk pricing
   - Flash sales

---

## Troubleshooting

### Images Not Displaying
- Ensure `uploads/` directory exists and is writable
- Check file paths in the database
- Verify image URLs are accessible

### Cart Not Persisting
- Check browser cookies are enabled
- Verify session token is being set
- Check database cart records

### Products Not Showing Up
- Ensure category is active and product is marked available
- Check category_id is valid
- Verify product has at least one active variant with stock > 0

### Video Upload Fails
- Check file size (max 500MB)
- Verify file format (mp4, webm, mov, avi)
- Ensure `uploads/commercials/` directory is writable

---

## Support

For issues or questions:
1. Check the API error responses for detailed error messages
2. Review server logs: `make dev` output
3. Verify database connectivity
4. Check file permissions on `uploads/` directory

---

**Store System Built For Jonche Platform** ✨
Version 1.0 | April 2024
