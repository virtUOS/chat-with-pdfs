"""
Main annotation creation factory for PDF highlighting.
"""

from .geometry import validate_and_clamp_coordinates, merge_nearby_positions
from ..citations import extract_citation_indices, is_source_from_current_document


def create_annotations_from_sources(answer_text, sources, citation_mapping=None, current_document_name=None, annotation_mode="smart"):
    """
    Create PDF annotations from sources that are cited in the answer text.
    Uses RAGFlow position coordinates for precise highlighting only.
    Only creates annotations for sources from the currently displayed document.
    
    Args:
        answer_text: The answer text containing citations
        sources: List of source nodes
        citation_mapping: Optional dict mapping citation numbers (as strings) to original source indices
        current_document_name: Name of the currently displayed document
        annotation_mode: String controlling annotation behavior:
            - "smart" (default): Intelligent merging and filtering
            - "minimal": Only one annotation per source (largest/most relevant segment)
            - "detailed": All segments but with better colors and smaller boxes
            - "off": No annotations
        
    Returns:
        A tuple of (annotations_list, citation_to_annotation_mapping)
        where citation_to_annotation_mapping maps citation_num -> [annotation_positions]
    """
    if annotation_mode == "off":
        return [], {}
        
    citations = extract_citation_indices(answer_text)
    if not citations:
        return [], {}
    
    # Deduplicate citations to avoid creating multiple annotations for the same source
    unique_citations = sorted(list(set(citations)))
    
    # Collect all citation data first, preserving citation ID order
    citation_data = {}
    
    for citation_idx in unique_citations:
        # Use citation mapping if provided
        source_index = None
        if citation_mapping and str(citation_idx) in citation_mapping:
            source_index = citation_mapping[str(citation_idx)]
        else:
            continue  # Skip if no mapping available
        
        if 0 <= source_index < len(sources):
            source = sources[source_index]
            
            # Only create annotations for sources from the current document
            if current_document_name and is_source_from_current_document(source, current_document_name):
                # Create annotations based on mode - use original citation_idx for consistency
                if annotation_mode == "minimal":
                    ragflow_annotations = _create_minimal_annotations(source, citation_idx, answer_text)
                elif annotation_mode == "detailed":
                    ragflow_annotations = _create_detailed_annotations(source, citation_idx, answer_text)
                else:  # "smart" mode (default)
                    ragflow_annotations = _create_ragflow_position_annotations(source, citation_idx, answer_text)
                
                if ragflow_annotations:
                    citation_data[citation_idx] = ragflow_annotations
    
    # Now build final annotations list in citation ID order
    annotations = []
    citation_to_annotation_mapping = {}
    
    # Process citations in sorted order to ensure consistent annotation positioning
    for citation_idx in sorted(citation_data.keys()):
        ragflow_annotations = citation_data[citation_idx]
        
        # Track starting position for this citation
        start_annotation_pos = len(annotations)
        
        # Add annotations to the final list
        annotations.extend(ragflow_annotations)
        
        # Map this citation to its annotation positions (1-indexed for streamlit-pdf-viewer)
        annotation_positions = []
        for i in range(len(ragflow_annotations)):
            annotation_positions.append(start_annotation_pos + i + 1)
        citation_to_annotation_mapping[citation_idx] = annotation_positions
        
        print(f"DEBUG: Citation {citation_idx} assigned positions {annotation_positions}")
    
    return annotations, citation_to_annotation_mapping


def _create_ragflow_position_annotations(source, citation_idx, answer_text):
    """
    Create smart annotations using RAGFlow position coordinates.
    Merges nearby positions and filters small segments for cleaner visual appearance.
    
    Args:
        source: Source object with RAGFlow metadata
        citation_idx: Citation index number (display number, starting from 1)
        answer_text: Answer text for citation format detection
        
    Returns:
        List of annotation dictionaries or None if positions not available
    """
    # Check if this is a RAGFlow source with positions
    if not isinstance(source, dict) or 'metadata' not in source:
        return None
    
    positions = source['metadata'].get('positions')
    if not positions:
        return None
    
    # Use simple citation format with display number
    citation_format = f"[{citation_idx}]"
    
    try:
        # First, collect and validate all positions
        valid_positions = []
        for position in positions:
            if len(position) >= 5:
                page_num, coord1, coord2, coord3, coord4 = position[:5]
                x0, x1, y0, y1 = coord1, coord2, coord3, coord4
                
                # Ensure proper ordering (min, max)
                x_min, x_max = min(x0, x1), max(x0, x1)
                y_min, y_max = min(y0, y1), max(y0, y1)
                
                width = x_max - x_min
                height = y_max - y_min
                
                # Apply boundary validation and coordinate clamping
                validated_pos = validate_and_clamp_coordinates(
                    x_min, y_min, width, height, page_num, source.get('metadata', {}).get('document_name', '')
                )
                
                if validated_pos:
                    valid_positions.append(validated_pos)
        
        if not valid_positions:
            return None
        
        # Group positions by page for intelligent merging
        page_groups = {}
        for pos in valid_positions:
            page = pos['page']
            if page not in page_groups:
                page_groups[page] = []
            page_groups[page].append(pos)
        
        # Create smart annotations per page
        annotations = []
        color_options = ["lightcoral", "lightblue", "lightgreen", "lightsalmon", "plum"]
        base_color = color_options[citation_idx % len(color_options)]
        
        for page, page_positions in page_groups.items():
            # Strategy 1: If many small segments on same page, create one large bounding box
            if len(page_positions) > 5:
                # Merge all positions on this page into one large annotation
                min_x = min(pos['x'] for pos in page_positions)
                min_y = min(pos['y'] for pos in page_positions)
                max_x = max(pos['x'] + pos['width'] for pos in page_positions)
                max_y = max(pos['y'] + pos['height'] for pos in page_positions)
                
                annotation = {
                    "page": page,
                    "x": min_x,
                    "y": min_y,
                    "width": max_x - min_x,
                    "height": max_y - min_y,
                    "color": base_color,
                    "title": f"Source {citation_format}",
                    "label": f"{citation_format}"
                }
                annotations.append(annotation)
                
            # Strategy 2: If few segments, merge nearby ones
            else:
                merged_positions = merge_nearby_positions(page_positions)
                
                for i, pos in enumerate(merged_positions):
                    annotation = {
                        "page": page,
                        "x": pos['x'],
                        "y": pos['y'],
                        "width": pos['width'],
                        "height": pos['height'],
                        "color": base_color,
                        "title": f"Source {citation_format}",
                        "label": f"{citation_format}" + (f"-{i+1}" if len(merged_positions) > 1 else "")
                    }
                    annotations.append(annotation)
        
        return annotations if annotations else None
        
    except (ValueError, TypeError, IndexError) as e:
        print(f"Error processing RAGFlow positions: {e}")
        return None


def _create_minimal_annotations(source, citation_idx, answer_text):
    """
    Create minimal annotations - only one per source using the largest or most central segment.
    
    Args:
        source: Source object with RAGFlow metadata
        citation_idx: Citation index number
        answer_text: Answer text for citation format detection
        
    Returns:
        List with a single annotation dictionary or None
    """
    if not isinstance(source, dict) or 'metadata' not in source:
        return None
    
    positions = source['metadata'].get('positions')
    if not positions:
        return None
    
    # Determine citation format
    citation_format = f"[ID:{citation_idx}]" if "[ID:" in answer_text else f"[{citation_idx}]"
    
    try:
        # Find the largest valid segment (by area)
        best_position = None
        max_area = 0
        
        for position in positions:
            if len(position) >= 5:
                page_num, coord1, coord2, coord3, coord4 = position[:5]
                x0, x1, y0, y1 = coord1, coord2, coord3, coord4
                
                # Ensure proper ordering (min, max)
                x_min, x_max = min(x0, x1), max(x0, x1)
                y_min, y_max = min(y0, y1), max(y0, y1)
                
                width = x_max - x_min
                height = y_max - y_min
                
                # Apply boundary validation
                validated_pos = validate_and_clamp_coordinates(
                    x_min, y_min, width, height, page_num, source.get('metadata', {}).get('document_name', '')
                )
                
                if validated_pos:
                    area = validated_pos['width'] * validated_pos['height']
                    if area > max_area:
                        max_area = area
                        best_position = validated_pos
        
        if best_position:
            color_options = ["lightcoral", "lightblue", "lightgreen", "lightsalmon", "plum"]
            return [{
                **best_position,
                "color": color_options[citation_idx % len(color_options)],
                "title": f"Source {citation_format}",
                "label": f"{citation_format}"
            }]
        
        return None
        
    except (ValueError, TypeError, IndexError) as e:
        print(f"Error creating minimal annotation: {e}")
        return None


def _create_detailed_annotations(source, citation_idx, answer_text):
    """
    Create detailed annotations - all segments but with improved visual styling.
    
    Args:
        source: Source object with RAGFlow metadata
        citation_idx: Citation index number
        answer_text: Answer text for citation format detection
        
    Returns:
        List of annotation dictionaries with improved styling
    """
    if not isinstance(source, dict) or 'metadata' not in source:
        return None
    
    positions = source['metadata'].get('positions')
    if not positions:
        return None
    
    # Determine citation format
    citation_format = f"[ID:{citation_idx}]" if "[ID:" in answer_text else f"[{citation_idx}]"
    
    try:
        annotations = []
        color_options = ["lightcoral", "lightblue", "lightgreen", "lightsalmon", "plum"]
        base_color = color_options[citation_idx % len(color_options)]
        
        for i, position in enumerate(positions):
            if len(position) >= 5:
                page_num, coord1, coord2, coord3, coord4 = position[:5]
                x0, x1, y0, y1 = coord1, coord2, coord3, coord4
                
                # Ensure proper ordering (min, max)
                x_min, x_max = min(x0, x1), max(x0, x1)
                y_min, y_max = min(y0, y1), max(y0, y1)
                
                width = x_max - x_min
                height = y_max - y_min
                
                # Apply boundary validation
                validated_pos = validate_and_clamp_coordinates(
                    x_min, y_min, width, height, page_num, source.get('metadata', {}).get('document_name', '')
                )
                
                if validated_pos:
                    annotation = {
                        **validated_pos,
                        "color": base_color,
                        "title": f"Source {citation_format}",
                        "label": f"{citation_format}-{i+1}" if len(positions) > 1 else f"{citation_format}"
                    }
                    annotations.append(annotation)
        
        return annotations if annotations else None
        
    except (ValueError, TypeError, IndexError) as e:
        print(f"Error creating detailed annotations: {e}")
        return None