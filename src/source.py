"""
Source and citation handling for the Chat with Docs application.
"""

import re
import streamlit as st


def extract_citation_indices(answer_text: str):
    """
    Extract citation indices from the answer text.
    
    Args:
        answer_text: The text to extract citation indices from
        
    Returns:
        A list of integers representing the citation indices
    """
    # This regex returns a list of citation numbers found in the answer (as strings)
    return [int(x) for x in re.findall(r'\[(\d+)\]', answer_text)]


def prepare_source_highlight(source):
    """
    Prepare a highlight for a source in the PDF viewer.
    
    Args:
        source: The source node
        
    Returns:
        A dictionary with highlight information or None if no highlight can be created
    """
    # Get ref_id from source metadata
    try:
        if hasattr(source, 'node'):
            ref_id = source.node.metadata.get('ref_id')
            page = source.node.metadata.get('page', 0)
            source_text = source.node.text.strip()
        elif hasattr(source, 'metadata') and hasattr(source, 'text'):
            ref_id = source.metadata.get('ref_id')
            page = source.metadata.get('page', 0)
            source_text = source.text.strip()
        else:
            return None
    except:
        return None
    
    # Retrieve stored metadata using ref_id
    stored_meta = st.session_state['metadata_store'].get(ref_id, {})
    text_spans = stored_meta.get("text_spans", [])
    
    # If text_spans is not available, we can't create a highlight
    # This will happen with the PyMuPDFReader which doesn't provide text_spans
    if not text_spans:
        # Instead, use page number for a basic highlight
        page = stored_meta.get("page", 0)
        return {
            'page': page,
            'x': 0,  # Start at left edge
            'y': 0,  # Start at top
            'width': 100,  # Use arbitrary width
            'height': 100,  # Use arbitrary height
            'color': "yellow",
        }

    # Find spans that contain parts of the source text
    relevant_spans = []
    words = set(source_text.split())
    min_word_match = 3  # Minimum words that must match to consider span relevant
    
    for span in text_spans:
        span_words = set(span["text"].strip().split())
        # Check for significant word overlap
        if len(words.intersection(span_words)) >= min_word_match:
            relevant_spans.append(span)
    
    if not relevant_spans:
        return None

    # Create bounding box for relevant spans
    x0 = min(span["bbox"][0] for span in relevant_spans)
    y0 = min(span["bbox"][1] for span in relevant_spans)
    x1 = max(span["bbox"][2] for span in relevant_spans)
    y1 = max(span["bbox"][3] for span in relevant_spans)
    
    return {
        'page': page,
        'x': x0,
        'y': y0,
        'width': x1 - x0,
        'height': y1 - y0,
        'color': "red",
    }


def create_annotations_from_sources(answer_text, sources):
    """
    Create PDF annotations from sources that are cited in the answer text.
    
    Args:
        answer_text: The answer text containing citations
        sources: List of source nodes
        
    Returns:
        A list of annotation dictionaries
    """
    citations = extract_citation_indices(answer_text)
    annotations = []
    
    for idx in citations:
        if idx <= len(sources):
            source = sources[idx-1]  # Convert 1-based citation to 0-based index
            
            # Extract page number from source based on the source type
            page_num = None
            if hasattr(source, 'node'):
                page_num = source.node.metadata.get('page', 0)
            elif hasattr(source, 'metadata') and hasattr(source, 'text'):
                page_num = source.metadata.get('page', 0)
            
            # Only create annotation if we have a valid page number
            if page_num is not None:
                try:
                    # Convert page to integer if possible
                    page_num = int(page_num)
                except (ValueError, TypeError):
                    # Use 0 as fallback if conversion fails
                    page_num = 0
                # Create a border annotation for the page based on the citation
                # Position it at the top of the page with a thin border
                annotation = {
                    "page": page_num,
                    "x": 10,             # Small margin from left edge
                    "y": 10,             # Small margin from top edge
                    "width": 580,        # Wide enough to be clearly visible
                    "height": 800,       # Tall enough to frame content
                    "color": "red",      # Red border
                    "title": f"Source [{idx}]",  # Add citation number as title
                    "label": f"[{idx}]"  # Add label for identification
                }
                
                # Create a small annotation in top-right corner with the citation number
                citation_label = {
                    "page": page_num,
                    "x": 550,            # Right side of page
                    "y": 20,             # Near top
                    "width": 30,         # Small box for label
                    "height": 20,
                    "color": "red",
                    "title": f"Source [{idx}]",  # Add citation number as title
                    "label": f"[{idx}]"  # Add label for identification
                }
                
                # Add the annotations
                annotations.append(annotation)
                annotations.append(citation_label)
    
    return annotations


def format_source_for_display(source, citation_num=None):
    """
    Format a source for display in the UI with improved styling.
    
    Args:
        source: The source node
        citation_num: Optional citation number
        
    Returns:
        A tuple of (formatted_markdown, source_text)
    """
    try:
        # Extract metadata and text based on source type
        if hasattr(source, 'node'):
            page_num = source.node.metadata.get('page', 'N/A')
            text = source.node.text.strip()
        elif hasattr(source, 'metadata') and hasattr(source, 'text'):
            page_num = source.metadata.get('page', 'N/A')
            text = source.text.strip()
        else:
            page_num = 'Unknown'
            text = str(source) if source is not None else 'No text available'
    except Exception as e:
        page_num = 'Error'
        text = f"Could not extract source text: {str(e)}"
    
    # Format with citation number if provided
    if citation_num:
        source_id = f"Source [{citation_num}]"
    else:
        source_id = "Source"
    
    # Create a cleaner, more readable format without code blocks
    markdown = f"**{source_id} (Page {page_num})**:\n{text}"
    source_text = f"{source_id} (Page {page_num}):\n{text}"
    
    return markdown, source_text
