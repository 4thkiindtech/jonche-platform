"""
apps/api/db/__init__.py
SQLAlchemy instance — imported by all models and the app factory.
"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
