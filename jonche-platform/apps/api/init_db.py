#!/usr/bin/env python
"""Initialize database tables."""

from app import app
from db import db

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print('✓ Database tables created successfully')
        print('✓ GeneratedProductImage table is ready')
