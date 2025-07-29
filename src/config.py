"""
Configuration settings and constants for the Chat with Docs application.
RAGFlow version - uses pre-configured chat assistants instead of local models.
"""

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import os

# Image paths and settings
IMAGES_PATH = os.environ.get("TMP_ASSETS_PATH", "/tmp/chat-with-pdfs/tmp_assets/tmp_images")

# RAGFlow Configuration
RAGFLOW_API_KEY = os.environ.get("RAGFLOW_API_KEY", "")
RAGFLOW_BASE_URL = os.environ.get("RAGFLOW_BASE_URL", "http://localhost:9380")

# Validate RAGFlow configuration
if not RAGFLOW_API_KEY:
    print("Warning: RAGFLOW_API_KEY environment variable not set")

if not RAGFLOW_BASE_URL:
    print("Warning: RAGFLOW_BASE_URL environment variable not set")

# Log level
LOG_LEVEL = os.environ.get("LOG_LEVEL", "WARNING")
