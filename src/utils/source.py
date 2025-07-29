"""
Source and citation handling for the Chat with Docs application.
"""

import re
import streamlit as st


def extract_citation_indices(answer_text: str):
    """
    Extract citation indices from the answer text.
    Only supports RAGFlow format [ID:X].
    
    Args:
        answer_text: The text to extract citation indices from
        
    Returns:
        A list of integers representing the citation indices
    """
    # Extract RAGFlow format [ID:X] citations
    ragflow_citations = re.findall(r'\[ID:(\d+)\]', answer_text)
    return [int(x) for x in ragflow_citations]


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


def create_annotations_from_sources(answer_text, sources, citation_mapping=None, current_document_name=None):
    """
    Create PDF annotations from sources that are cited in the answer text.
    Uses RAGFlow position coordinates for precise highlighting only.
    Only creates annotations for sources from the currently displayed document.
    
    Args:
        answer_text: The answer text containing citations
        sources: List of source nodes
        citation_mapping: Optional dict mapping citation numbers (as strings) to original source indices
        current_document_name: Name of the currently displayed document
        
    Returns:
        A list of annotation dictionaries
    """
    citations = extract_citation_indices(answer_text)
    if not citations:
        return []
    
    # Deduplicate citations to avoid creating multiple annotations for the same source
    unique_citations = list(set(citations))
    
    print(f"DEBUG: Found citations: {citations}")
    print(f"DEBUG: Unique citations: {unique_citations}")
    print(f"DEBUG: Current document: {current_document_name}")
    
    annotations = []

    for idx in unique_citations:
        # Use citation mapping if provided
        source_index = None
        if citation_mapping and str(idx) in citation_mapping:
            source_index = citation_mapping[str(idx)]
            print(f"DEBUG: Citation {idx} maps to source index {source_index}")
        else:
            print(f"DEBUG: No mapping found for citation {idx}")
            continue  # Skip if no mapping available
        
        if 0 <= source_index < len(sources):
            source = sources[source_index]
            
            # Only create annotations for sources from the current document
            if current_document_name and _is_source_from_current_document(source, current_document_name):
                print(f"DEBUG: Source {source_index} matches current document, creating annotations")
                # Only create precise annotations using RAGFlow positions
                ragflow_annotations = _create_ragflow_position_annotations(source, idx, answer_text)
                if ragflow_annotations:
                    print(f"DEBUG: Created {len(ragflow_annotations)} annotations for citation {idx}")
                    annotations.extend(ragflow_annotations)
            else:
                print(f"DEBUG: Source {source_index} does not match current document")
            # No fallback - only precise annotations
        else:
            print(f"DEBUG: Source index {source_index} out of range")
    
    return annotations


def _is_source_from_current_document(source, current_document_name):
    """
    Check if a source belongs to the currently displayed document.
    
    Args:
        source: Source object with metadata
        current_document_name: Name of the currently displayed document
        
    Returns:
        bool: True if source is from current document
    """
    if not isinstance(source, dict) or 'metadata' not in source:
        return False
    
    source_doc_name = source['metadata'].get('document_name', '')
    
    # Compare document names (handle potential variations)
    return source_doc_name == current_document_name


def _create_ragflow_position_annotations(source, citation_idx, answer_text):
    """
    Create precise annotations using RAGFlow position coordinates.
    RAGFlow format appears to be: [page, x0, y0, x1, y1] where (x0,y0) is top-left, (x1,y1) is bottom-right.
    
    Args:
        source: Source object with RAGFlow metadata
        citation_idx: Citation index number
        answer_text: Answer text for citation format detection
        
    Returns:
        List of annotation dictionaries or None if positions not available
    """
    annotations = []
    
    # Check if this is a RAGFlow source with positions
    if not isinstance(source, dict) or 'metadata' not in source:
        return None
    
    positions = source['metadata'].get('positions')
    if not positions:
        return None
    
    # Determine citation format
    citation_format = f"[ID:{citation_idx}]" if "[ID:" in answer_text else f"[{citation_idx}]"
    
    try:
        for i, position in enumerate(positions):
            if len(position) >= 5:
                # RAGFlow coordinate format: [page, x0, x1, y0, y1]
                page_num, coord1, coord2, coord3, coord4 = position[:5]
                
                # Keep RAGFlow's 1-based page numbering for PDF viewer
                # If RAGFlow says page 2, annotation should appear on page 2 in PDF viewer
                # No conversion needed - PDF viewer should handle 1-based page numbers
                
                # RAGFlow coordinate format: [x0, x1, y0, y1] where:
                # - x0, x1 are horizontal coordinates (left, right)
                # - y0, y1 are vertical coordinates (top, bottom)
                x0, x1, y0, y1 = coord1, coord2, coord3, coord4
                
                # Ensure proper ordering (min, max)
                x_min, x_max = min(x0, x1), max(x0, x1)
                y_min, y_max = min(y0, y1), max(y0, y1)
                
                width = x_max - x_min
                height = y_max - y_min
                
                # Only create annotation if dimensions are reasonable
                if width > 0 and height > 0 and width < 1000 and height < 1000:
                    annotation = {
                        "page": int(page_num),
                        "x": float(x_min),
                        "y": float(y_min),
                        "width": float(width),
                        "height": float(height),
                        "color": "red",
                        "title": f"Source {citation_format}",
                        "label": f"{citation_format}-{i+1}"
                    }
                    
                    annotations.append(annotation)
        
        return annotations if annotations else None
        
    except (ValueError, TypeError, IndexError) as e:
        print(f"Error processing RAGFlow positions: {e}")
        return None


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


def get_source_annotation_snippets(source):
    """
    Extract individual text snippets for each annotation position in a RAGFlow source.
    
    Args:
        source: The source object (RAGFlow format: dict with metadata)
        
    Returns:
        A list of dictionaries with 'page', 'text' for each annotation position
    """
    try:
        if isinstance(source, dict) and 'metadata' in source:
            positions = source['metadata'].get('positions', [])
            if positions and len(positions) > 1:  # Only split if multiple positions
                # For now, we'll split the main text roughly by the number of positions
                # This is a simple approach - ideally RAGFlow would provide text per position
                main_text = source.get('text', '')
                if main_text:
                    # Split text into roughly equal parts based on number of positions
                    text_length = len(main_text)
                    snippet_length = max(100, text_length // len(positions))
                    
                    snippets = []
                    for i, position in enumerate(positions):
                        if len(position) >= 1:
                            page_num = position[0]
                            
                            # Extract a snippet from the main text
                            start_pos = i * snippet_length
                            end_pos = min(start_pos + snippet_length + 50, text_length)  # Add overlap
                            
                            snippet_text = main_text[start_pos:end_pos].strip()
                            if snippet_text:
                                # Clean up snippet boundaries (try to end at word boundaries)
                                if end_pos < text_length and not snippet_text.endswith('.'):
                                    last_space = snippet_text.rfind(' ')
                                    if last_space > len(snippet_text) * 0.8:  # Only if we don't lose too much
                                        snippet_text = snippet_text[:last_space]
                                
                                if len(snippet_text) > 150:
                                    snippet_text = snippet_text[:150] + "..."
                                
                                snippets.append({
                                    'page': page_num,
                                    'text': snippet_text
                                })
                    
                    return snippets if snippets else None
        
        return None
        
    except Exception as e:
        return None