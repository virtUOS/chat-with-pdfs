"""
Layout components for the Chat with Docs application.

This module contains modular components extracted from the main layouts.py file
to improve maintainability, testability, and readability.
"""

from .assistant_selector import render_assistant_selector
from .document_list import render_document_list
from .settings_panel import render_settings_panel
from .pdf_viewer import render_pdf_viewer
from .chat_interface import render_chat_interface
from .message_renderer import render_chat_messages
from .tab_container import render_content_tabs
from .pdf_utils import calculate_pdf_height, extract_page_dimensions_immediately
from .annotation_handler import create_annotation_click_handler, create_annotations_for_document
from .query_suggestions import render_query_suggestions
from .source_citations import render_source_citations

__all__ = [
    # Sidebar components
    'render_assistant_selector',
    'render_document_list', 
    'render_settings_panel',
    
    # Main content components
    'render_pdf_viewer',
    'render_chat_interface',
    'render_chat_messages',
    'render_content_tabs',
    
    # Utility components
    'calculate_pdf_height',
    'extract_page_dimensions_immediately',
    'create_annotation_click_handler',
    'create_annotations_for_document',
    'render_query_suggestions',
    'render_source_citations',
]