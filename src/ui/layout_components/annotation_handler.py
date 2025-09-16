"""
Annotation handling components for PDF viewer.

Contains functions for creating annotations from sources and handling
annotation interactions in the PDF viewer.
"""

import streamlit as st
from typing import Dict, List, Tuple, Any, Callable

from ...utils.logger import Logger
from ...utils.annotations import create_annotations_from_sources
from ..layout_state_manager import LayoutStateManager


def create_annotation_click_handler() -> Callable[[Dict[str, Any]], None]:
    """
    Create an annotation click handler function for PDF viewer.
    
    Returns:
        Callable: Function that handles annotation clicks
    """
    def annotation_click_handler(annotation: Dict[str, Any]) -> None:
        """Handle clicks on source annotations in the PDF viewer."""
        page = annotation.get('page', 'unknown')
        Logger.info(f"Annotation clicked on page {page}")
        # No further action required
    
    return annotation_click_handler


def create_annotations_for_document(current_file: str) -> Tuple[List[Dict[str, Any]], Dict[int, List[int]]]:
    """
    Create annotations for the current document based on chat history.
    
    Args:
        current_file: Name of the current document
        
    Returns:
        Tuple of (annotations list, citation_to_annotation_mapping)
    """
    annotations = []
    citation_to_annotation_mapping = {}
    
    # Check if we have a document-specific response with sources and answer
    if not LayoutStateManager.has_document_response_with_sources(current_file):
        return annotations, citation_to_annotation_mapping
    
    # Get document response data
    doc_response = LayoutStateManager.get_document_responses(current_file)
    citation_mapping = doc_response.get('citation_mapping', {})
    annotation_mode = LayoutStateManager.get_annotation_mode()
    
    # Create annotations based on the document-specific response
    annotations, citation_to_annotation_mapping = create_annotations_from_sources(
        doc_response['answer'],
        doc_response['sources'],
        citation_mapping,
        current_file,  # Pass current document name to filter sources
        annotation_mode  # Pass annotation mode
    )
    
    Logger.info(f"Created {len(annotations)} annotations for document {current_file}")
    
    # Store the mapping for scroll functionality
    LayoutStateManager.set_citation_to_annotation_mapping(citation_to_annotation_mapping)
    
    return annotations, citation_to_annotation_mapping


def get_scroll_to_annotation() -> int | None:
    """
    Get the annotation position to scroll to from session state.
    
    Returns:
        int | None: Annotation position to scroll to, or None
    """
    return LayoutStateManager.get_scroll_to_annotation()


def set_scroll_to_annotation(position: int) -> None:
    """
    Set the annotation position to scroll to and trigger rerun.
    
    Args:
        position: Annotation position to scroll to
    """
    LayoutStateManager.set_scroll_to_annotation(position)
    st.rerun()