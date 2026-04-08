"""apps/api/wsgi.py — PythonAnywhere WSGI entry point for the API."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))
from app import app as application  # noqa: F401
