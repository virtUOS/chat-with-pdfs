"""
PDF utility functions for layout components.

Contains helper functions for PDF rendering, height calculation, 
and page dimension extraction.
"""

import os
import tempfile
import fitz
import streamlit as st
from streamlit_js_eval import streamlit_js_eval
from typing import Optional

from ...utils.logger import Logger


def calculate_pdf_height(screen_height: Optional[int] = None) -> int:
    """
    Calculate optimal PDF viewer height based on screen dimensions.
    
    Args:
        screen_height: Screen height in pixels. If None, will try to get from JS.
        
    Returns:
        int: Optimal PDF viewer height in pixels.
    """
    if screen_height is None:
        screen_height = streamlit_js_eval(js_expressions='screen.height', key='pdf_screen_height')
    
    return int(screen_height * 0.8) if screen_height else 900


def extract_page_dimensions_immediately(pdf_data: bytes, ragflow_doc: dict) -> None:
    """
    Extract page dimensions immediately after PDF download.
    
    This function extracts and caches page dimensions for annotation positioning.
    
    Args:
        pdf_data: PDF file data as bytes
        ragflow_doc: RAGFlow document information dictionary
    """
    try:
        # Create a temporary file to work with PyMuPDF
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(pdf_data)
            temp_file.flush()
            
            try:
                # Open the PDF and extract page dimensions
                doc = fitz.open(temp_file.name)
                
                page_dimensions = []
                for page_num in range(len(doc)):
                    page = doc.load_page(page_num)
                    rect = page.rect
                    page_dimensions.append({
                        'page_num': page_num,
                        'width': rect.width,
                        'height': rect.height
                    })
                
                # Store dimensions in session state for annotation positioning
                doc_id = ragflow_doc.get('id', '')
                if doc_id:
                    if 'ragflow_page_dimensions' not in st.session_state:
                        st.session_state.ragflow_page_dimensions = {}
                    st.session_state.ragflow_page_dimensions[doc_id] = page_dimensions
                    Logger.info(f"Extracted {len(page_dimensions)} page dimensions for document {doc_id}")
                
                doc.close()
                
            finally:
                # Clean up the temporary file
                try:
                    os.unlink(temp_file.name)
                except OSError:
                    pass  # File might already be deleted
                    
    except Exception as e:
        Logger.error(f"Error extracting page dimensions: {str(e)}")


def get_page_count_from_pdf_data(pdf_data: bytes) -> Optional[int]:
    """
    Get page count from PDF data.
    
    Args:
        pdf_data: PDF file data as bytes
        
    Returns:
        int: Number of pages in the PDF, or None if error
    """
    try:
        doc = fitz.open(stream=pdf_data, filetype="pdf")
        page_count = len(doc)
        doc.close()
        return page_count
    except Exception as e:
        Logger.warning(f"Could not get page count from PDF data: {e}")
        return None