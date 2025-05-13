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


def create_annotations_from_sources(answer_text, sources, citation_mapping=None):
    """
    Create PDF annotations from sources that are cited in the answer text.
    
    Args:
        answer_text: The answer text containing citations
        sources: List of source nodes
        citation_mapping: Optional dict mapping citation numbers (as strings) to original source indices
        
    Returns:
        A list of annotation dictionaries
    """
    import streamlit as st
    from ..utils.logger import Logger

    citations = extract_citation_indices(answer_text)
    annotations = []

    for idx in citations:
        # Use citation mapping if provided
        source_index = None
        if citation_mapping and str(idx) in citation_mapping:
            source_index = citation_mapping[str(idx)]
        else:
            continue  # Skip if no mapping available
        
        if 0 <= source_index < len(sources):
            source = sources[source_index]
            
            # Extract page number from source based on the source type
            page_num = None
            if hasattr(source, 'node'):
                page_num = source.node.metadata.get('page', 0)
            elif hasattr(source, 'metadata') and hasattr(source, 'text'):
                page_num = source.metadata.get('page', 0)
            
            # Only create annotation if we have a valid page number
            if page_num is not None:
                try:
                    page_num = int(page_num)
                except (ValueError, TypeError):
                    page_num = 0 # Fallback

                chunk_bbox = None
                if hasattr(source, 'node') and 'chunk_bbox' in source.node.metadata:
                    chunk_bbox = source.node.metadata['chunk_bbox']
                elif hasattr(source, 'metadata') and 'chunk_bbox' in source.metadata:
                    chunk_bbox = source.metadata['chunk_bbox']

                if chunk_bbox and isinstance(chunk_bbox, list) and len(chunk_bbox) == 4:
                    # We have a precise bounding box for the chunk
                    x0, y0, x1, y1 = chunk_bbox
                    precise_annotation = {
                        "page": page_num,
                        "x": x0,
                        "y": y0,
                        "width": x1 - x0,
                        "height": y1 - y0,
                        "color": "rgba(255, 0, 0, 0.3)", # Semi-transparent red
                        "title": f"Source [{idx}] (Chunk)",
                        "label": f"[{idx}]"
                    }
                    annotations.append(precise_annotation)
                    Logger.debug(f"Created precise annotation for source [{idx}] on page {page_num} with bbox: {chunk_bbox}")
                else:
                    # Fallback to page-level annotation (e.g., border or corner label)
                    Logger.debug(f"No chunk_bbox for source [{idx}] on page {page_num}. Falling back to page-level annotation.")
                    page_border_annotation = {
                        "page": page_num,
                        "x": 10,
                        "y": 10,
                        "width": 575, # Adjusted to avoid overlap with potential scrollbars
                        "height": 780, # Adjusted
                        "color": "rgba(255, 0, 0, 0.1)", # Lighter, less intrusive border
                        "title": f"Source [{idx}] (Page)",
                        "label": f"[{idx}]"
                    }
                    annotations.append(page_border_annotation)

                # The small citation corner label has been removed as per user request.
                # It was causing a persistent red box in the top right corner.
                # If a corner label is desired in the future, it should be re-evaluated.
    
    return annotations


def format_source_for_display(source):
    """
    Format a source for display in the UI with improved styling.
    
    Args:
        source: The source node        
    Returns:
        The source_text formatted for display
    """
    try:
        # Extract metadata and text based on source type
        if hasattr(source, 'node'):
            source_text = source.node.text.strip()
        elif hasattr(source, 'metadata') and hasattr(source, 'text'):
            source_text = source.text.strip()
        else:
            source_text = str(source) if source is not None else 'No text available'
    except Exception as e:
        source_text = f"Could not extract source text: {str(e)}"
    
    # Remove leading markdown headers (e.g., #, ##, ###)
    # and potential bolded titles followed by headers
    # Example: "# **Title** ## Subtitle" -> "Subtitle"
    # Example: "## Subtitle" -> "Subtitle"
    # Example: "# Title" -> "Title"
    source_text = re.sub(r"^(?:#\s*\*\*.*?\*\*\s*##\s*|#+\s*)", "", source_text, count=1)
    # Fallback for simple cases or if the above didn't catch everything,
    # e.g. if there was no space after the hash marks initially.
    source_text = re.sub(r"^\s*#+\s*", "", source_text)
    return source_text.strip() # Add strip here to clean any leading/trailing whitespace left