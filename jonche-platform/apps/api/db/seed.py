"""
apps/api/db/seed.py
Seeds the database with initial data for development.
Run: python -m db.seed
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from app import app
from db import db
from db.models import (
    Admin, Member, Retailer, Drop,
    WaitlistEntry, Certificate, QRCampaign, RetailerAllocation,
    ProductCategory, Product, ProductVariant, ProductImage, Commercial
)


def seed():
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("✓ Tables created")

        # ── Admins ──────────────────────────────────────────────────────────
        admin_email = os.getenv("DEV_ADMIN_EMAIL", "admin@jonche.com")
        admin_password = os.getenv("DEV_ADMIN_PASSWORD", "jonche-admin-2026")
        admin = Admin(
            email=admin_email,
            password_hash=generate_password_hash(admin_password),
            name="Jonche Admin",
            is_superadmin=True,
        )
        db.session.add(admin)
        print("✓ Admin seeded")

        # ── Members ─────────────────────────────────────────────────────────
        members_data = [
            ("jordan@example.com", "Jordan V.",    "gold",   12840.0),
            ("marcus@example.com", "Marcus R.",    "gold",   9200.0),
            ("aisha@example.com",  "Aisha K.",     "silver", 5640.0),
            ("tyler@example.com",  "Tyler N.",     "silver", 3100.0),
            ("sofia@example.com",  "Sofia P.",     "bronze", 1200.0),
        ]
        members = []
        for email, name, tier, spend in members_data:
            m = Member(
                email=email,
                password_hash=generate_password_hash(os.getenv("DEV_MEMBER_PASSWORD", "member-pass-2026")),
                name=name,
                tier=tier,
                lifetime_spend=spend,
            )
            db.session.add(m)
            members.append(m)
        print(f"✓ {len(members)} members seeded")

        # ── Retailers ────────────────────────────────────────────────────────
        retailers_data = [
            ("buyer@kith.com",         "Kith NYC",       "Alex Kim",    "premier", "active"),
            ("buyer@unionla.com",      "Union LA",       "Chris Lee",   "premier", "active"),
            ("buyer@doverstreet.com",  "Dover Street",   "Sam Park",    "select",  "pending"),
            ("buyer@ssense.com",       "SSENSE",         "Jordan Wu",   "select",  "pending"),
            ("buyer@localconcept.com", "Local Concept",  "Tyler Moss",  "basic",   "review"),
        ]
        retailers = []
        for email, name, contact, tier, status in retailers_data:
            r = Retailer(
                email=email,
                password_hash=generate_password_hash(os.getenv("DEV_RETAILER_PASSWORD", "retailer-pass-2026")),
                name=name,
                contact_name=contact,
                tier=tier,
                status=status,
            )
            db.session.add(r)
            retailers.append(r)
        print(f"✓ {len(retailers)} retailers seeded")

        db.session.flush()  # get IDs before creating related records

        # ── Drops ────────────────────────────────────────────────────────────
        drops_data = [
            {
                "slug": "eclipse-001",
                "name": "Jonche Eclipse 001",
                "colorway": "Obsidian / Gold",
                "sizes": "7-14",
                "price": 48000,  # cents
                "total_units": 150,
                "units_reserved": 50,
                "status": "live",
                "use_raffle": False,
                "max_per_member": 1,
                "drop_at": datetime.utcnow() - timedelta(days=3),
            },
            {
                "slug": "void-low",
                "name": "Jonche Void Low",
                "colorway": "All Black",
                "sizes": "8-12",
                "price": 32000,
                "total_units": 100,
                "units_reserved": 20,
                "status": "upcoming",
                "use_raffle": True,
                "max_per_member": 1,
                "drop_at": datetime.utcnow() + timedelta(days=2),
            },
            {
                "slug": "fragment-iii",
                "name": "Jonche Fragment III",
                "colorway": "Chalk / Ivory",
                "sizes": "6-13",
                "price": 56000,
                "total_units": 80,
                "units_reserved": 15,
                "status": "draft",
                "use_raffle": True,
                "max_per_member": 1,
                "drop_at": datetime.utcnow() + timedelta(days=14),
            },
            {
                "slug": "mirage-002",
                "name": "Jonche Mirage 002",
                "colorway": "Earth / Rust",
                "sizes": "7-11",
                "price": 39500,
                "total_units": 80,
                "units_reserved": 10,
                "status": "sold_out",
                "use_raffle": False,
                "max_per_member": 1,
                "drop_at": datetime.utcnow() - timedelta(days=30),
            },
        ]
        drops = []
        for d in drops_data:
            drop = Drop(**d)
            db.session.add(drop)
            drops.append(drop)
        print(f"✓ {len(drops)} drops seeded")

        db.session.flush()

        # ── Retailer Allocations ──────────────────────────────────────────────
        allocs = [
            (retailers[0], drops[0], 30, "confirmed"),
            (retailers[1], drops[0], 20, "confirmed"),
            (retailers[2], drops[1], 15, "pending"),
            (retailers[3], drops[1], 10, "pending"),
            (retailers[4], drops[2],  5, "pending"),
        ]
        for retailer, drop, units, status in allocs:
            alloc = RetailerAllocation(
                retailer_id=retailer.id,
                drop_id=drop.id,
                allocated_units=units,
                status=status,
            )
            db.session.add(alloc)
        print("✓ Retailer allocations seeded")

        # ── Waitlist Entries ──────────────────────────────────────────────────
        for member in members[:3]:
            entry = WaitlistEntry(
                drop_id=drops[1].id,  # Void Low (raffle drop)
                member_id=member.id,
                size="10",
                status="entered",
            )
            db.session.add(entry)
        print("✓ Waitlist entries seeded")

        # ── QR Campaigns ─────────────────────────────────────────────────────
        qr_data = [
            ("Eclipse Launch — NYC Pop-Up",    drops[0].id, "https://jonche.com/drops/eclipse-001", "active"),
            ("Fragment III — Instagram Story", drops[2].id, "https://jonche.com/drops/fragment-iii","active"),
            ("VIP Early Access — Email",       drops[3].id, "https://jonche.com/vip",               "ended"),
            ("Retail Partner — Kith Collab",   drops[0].id, "https://jonche.com/drops/eclipse-001", "active"),
        ]
        for name, drop_id, url, status in qr_data:
            qr = QRCampaign(name=name, drop_id=drop_id, destination_url=url, status=status)
            db.session.add(qr)
        print("✓ QR campaigns seeded")

        # ── Certificates ──────────────────────────────────────────────────────
        for i, member in enumerate(members[:2]):
            cert = Certificate(
                cert_number=f"JNC-2025-{800 + i + 1:04d}",
                drop_id=drops[0].id,
                member_id=member.id,
                size="10",
                run_number=i + 1,
                total_run=150,
            )
            db.session.add(cert)
        print("✓ Certificates seeded")

        # ── Store categories/products (for storefront UI dev) ────────────────
        apparel = ProductCategory(
            name="Apparel",
            slug="apparel",
            description="Essentials and seasonal pieces.",
            display_order=1,
            is_active=True,
        )
        accessories = ProductCategory(
            name="Accessories",
            slug="accessories",
            description="Add-ons and limited accessories.",
            display_order=2,
            is_active=True,
        )
        db.session.add_all([apparel, accessories])
        db.session.flush()

        tee = Product(
            sku="JNC-TEE-001",
            name="Jonche Classic Tee",
            slug="jonche-classic-tee",
            description="Heavyweight cotton tee with Jonche wordmark.",
            category_id=apparel.id,
            base_price=3500,
            is_available=True,
            display_order=1,
        )
        cap = Product(
            sku="JNC-CAP-001",
            name="Jonche Signature Cap",
            slug="jonche-signature-cap",
            description="Embroidered cap with adjustable strap.",
            category_id=accessories.id,
            base_price=4200,
            is_available=True,
            display_order=2,
        )
        db.session.add_all([tee, cap])
        db.session.flush()

        db.session.add_all([
            ProductVariant(product_id=tee.id, variant_sku="JNC-TEE-001-S", option_name="size", option_value="S", quantity_in_stock=25),
            ProductVariant(product_id=tee.id, variant_sku="JNC-TEE-001-M", option_name="size", option_value="M", quantity_in_stock=40),
            ProductVariant(product_id=tee.id, variant_sku="JNC-TEE-001-L", option_name="size", option_value="L", quantity_in_stock=35),
            ProductVariant(product_id=cap.id, variant_sku="JNC-CAP-001-BLK", option_name="color", option_value="Black", quantity_in_stock=30),
        ])

        placeholder_tee = "https://placehold.co/900x900/png?text=JONCHE+TEE"
        placeholder_cap = "https://placehold.co/900x900/png?text=JONCHE+CAP"
        db.session.add_all([
            ProductImage(product_id=tee.id, image_url=placeholder_tee, alt_text="Jonche Classic Tee", is_primary=True, display_order=1),
            ProductImage(product_id=cap.id, image_url=placeholder_cap, alt_text="Jonche Signature Cap", is_primary=True, display_order=1),
        ])
        print("✓ Store products seeded")

        # ── Commercials (for store hero) ─────────────────────────────────────
        commercial = Commercial(
            title="Jonche — Launch Reel",
            description="A quick look at the latest collection.",
            video_url="https://www.w3schools.com/html/mov_bbb.mp4",
            thumbnail_url="https://placehold.co/1600x900/png?text=JONCHE+LAUNCH",
            display_order=1,
            is_active=True,
        )
        db.session.add(commercial)
        print("✓ Store commercials seeded")

        db.session.commit()
        print("\n🖤 Jonche database seeded successfully.")
        print(f"   Admin login: {admin_email} / {admin_password}")
        print(f"   Member login: jordan@example.com / {os.getenv('DEV_MEMBER_PASSWORD', 'member-pass-2026')}")
        print(f"   Retailer login: buyer@kith.com / {os.getenv('DEV_RETAILER_PASSWORD', 'retailer-pass-2026')}")


if __name__ == "__main__":
    seed()
