"""
Layout components for modular UI design.

This package contains focused, reusable components that together compose
the application's user interface. Each component has a single responsibility
and clear boundaries.
"""

# Import all components for easy access
from .query_suggestions import render_query_suggestions
from .pdf_utils import calculate_pdf_height, extract_page_dimensions_immediately
from .annotation_handler import create_annotation_click_handler, create_annotations_for_document
from .source_citations import render_source_citations

__all__ = [
    'render_query_suggestions',
    'calculate_pdf_height',
    'extract_page_dimensions_immediately',
    'create_annotation_click_handler',
    'create_annotations_for_document',
    'render_source_citations',
]