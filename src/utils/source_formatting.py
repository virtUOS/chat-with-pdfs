"""
Source display and formatting utilities for the Chat with Docs application.
"""

import re


def format_source_for_display(source):
    """
    Format a source for display in the UI with improved styling.
    
    Args:
        source: The source node (RAGFlow format: dict with 'text' key)
    Returns:
        The source_text formatted for display
    """
    try:
        # Handle RAGFlow source format (dictionary)
        if isinstance(source, dict):
            # RAGFlow sources have 'text' field
            source_text = source.get('text', '')
            if not source_text:
                source_text = 'No text available'
        # Handle LlamaIndex source format (object with attributes)
        elif hasattr(source, 'node'):
            source_text = source.node.text.strip()
        elif hasattr(source, 'metadata') and hasattr(source, 'text'):
            source_text = source.text.strip()
        else:
            source_text = str(source) if source is not None else 'No text available'
        
        # Clean up the text for better display
        if source_text:
            source_text = source_text.strip()
            # Limit length for better readability (show first 300 chars)
            if len(source_text) > 300:
                source_text = source_text[:300] + "..."
        
    except Exception as e:
        source_text = f"Could not extract source text: {str(e)}"
    
    return source_text


def get_source_page_numbers_for_display(source):
    """
    Extract all page numbers that a source spans, converted to PDF viewer page numbers for consistent display.
    Only works with RAGFlow sources that have positions data.
    
    Args:
        source: The source object (RAGFlow format: dict with metadata)
        
    Returns:
        A list of page numbers (PDF viewer numbering: 1-based) that this source spans
    """
    try:
        if isinstance(source, dict) and 'metadata' in source:
            # Only use RAGFlow positions data - no fallbacks
            positions = source['metadata'].get('positions', [])
            if positions:
                # Extract unique page numbers from positions
                ragflow_pages = set()
                for position in positions:
                    if len(position) >= 1:
                        page_num = position[0]  # First element is page number
                        if isinstance(page_num, int) and page_num > 0:
                            ragflow_pages.add(page_num)
                
                if ragflow_pages:
                    # Keep RAGFlow's original page numbers - these are the actual document page numbers
                    # If text appears on document page 2, show "Page 2" in sources
                    return sorted(list(ragflow_pages))
        
        return ['N/A']
        
    except Exception as e:
        return ['Error']


def format_page_numbers_for_display(page_numbers):
    """
    Format a list of page numbers for display.
    
    Args:
        page_numbers: List of page numbers
        
    Returns:
        Formatted string like "Page 1", "Pages 1-2", or "Pages 1, 3-4"
    """
    if not page_numbers or page_numbers == ['N/A'] or page_numbers == ['Error']:
        return page_numbers[0] if page_numbers else 'N/A'
    
    # Remove any non-numeric values
    numeric_pages = [p for p in page_numbers if isinstance(p, int)]
    if not numeric_pages:
        return str(page_numbers[0]) if page_numbers else 'N/A'
    
    numeric_pages = sorted(numeric_pages)
    
    if len(numeric_pages) == 1:
        return f"Page {numeric_pages[0]}"
    elif len(numeric_pages) == 2 and numeric_pages[1] == numeric_pages[0] + 1:
        return f"Pages {numeric_pages[0]}-{numeric_pages[1]}"
    else:
        # For non-consecutive pages, show them all
        return f"Pages {', '.join(map(str, numeric_pages))}"

