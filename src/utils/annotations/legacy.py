"""
Legacy highlight system for backward compatibility.
"""

import streamlit as st


def prepare_source_highlight(source):
    """
    Prepare a highlight for a source in the PDF viewer.
    LEGACY FUNCTION - provided for backward compatibility.
    
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