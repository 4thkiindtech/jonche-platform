"""
apps/web/wsgi.py
WSGI entry point for PythonAnywhere deployment.

In PythonAnywhere WSGI config, set:
    WSGI file → /home/yourusername/jonche-platform/apps/web/wsgi.py
"""

import sys
import os

# Add the web app to the path
sys.path.insert(0, os.path.dirname(__file__))

# Load env vars
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

from app import app as application  # noqa: F401
