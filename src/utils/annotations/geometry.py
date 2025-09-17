"""
Coordinate validation and geometric operations for PDF annotations.
"""

import streamlit as st
from src.core.state_manager import StateManager


def validate_and_clamp_coordinates(x, y, width, height, page_num, document_name=""):
    """
    Validate and clamp annotation coordinates using actual PDF page dimensions.
    
    Args:
        x, y: Top-left coordinates
        width, height: Annotation dimensions
        page_num: Page number (1-based)
        document_name: Document name to get page dimensions
        
    Returns:
        Dictionary with validated coordinates or None if invalid
    """
    # Try to get actual page dimensions from stored data
    page_dimensions = {}
    if document_name:
        # Debug: print what we're looking for
        ragflow_doc_mapping = st.session_state.get('ragflow_document_mapping', {})
        
        doc_id = None
        for ragflow_id, mapped_name in ragflow_doc_mapping.items():
            if mapped_name == document_name:
                doc_id = f"ragflow_{ragflow_id}"
                print(f"DEBUG: Found doc_id: {doc_id}")
                break
        
        if doc_id:
            page_dimensions = StateManager.get_document_page_dimensions(doc_id)
            print(f"DEBUG: Retrieved {len(page_dimensions)} page dimensions for {doc_id}")
            if page_dimensions:
                print(f"DEBUG: Available pages in dimensions: {list(page_dimensions.keys())}")
        else:
            print(f"DEBUG: No doc_id found for '{document_name}'")
    
    # Get page-specific dimensions or use reasonable defaults
    if page_num in page_dimensions:
        max_width = page_dimensions[page_num]['width']
        max_height = page_dimensions[page_num]['height']
        print(f"DEBUG ANNOTATION: Using real page dimensions for page {page_num}: {max_width}x{max_height}")
    else:
        # Fallback to generous defaults for various page sizes
        max_width = 1200  # A3 landscape or large formats
        max_height = 1600  # A3 portrait or large formats
        print(f"DEBUG ANNOTATION: Using fallback dimensions for page {page_num}: {max_width}x{max_height}")
    
    print(f"DEBUG ANNOTATION: Validating coords x={x}, y={y}, width={width}, height={height} for doc='{document_name}'")
    
    # Define minimum dimensions to filter out noise
    MIN_DIMENSION = 5      # Minimum annotation size
    MAX_WIDTH_RATIO = 0.95   # Max 95% of page width (more generous for text spans)
    MAX_HEIGHT_RATIO = 0.9   # Max 90% of page height
    
    # Basic size validation - filter out noise and oversized annotations
    if width < MIN_DIMENSION or height < MIN_DIMENSION:
        print(f"DEBUG ANNOTATION: Rejected due to small size: {width}x{height} < {MIN_DIMENSION}")
        return None
    if width > max_width * MAX_WIDTH_RATIO:
        print(f"DEBUG ANNOTATION: Rejected due to excessive width: {width} > {max_width * MAX_WIDTH_RATIO}")
        return None
    if height > max_height * MAX_HEIGHT_RATIO:
        print(f"DEBUG ANNOTATION: Rejected due to excessive height: {height} > {max_height * MAX_HEIGHT_RATIO}")
        return None
    
    # Coordinate validation and clamping
    # Ensure coordinates are not negative
    x = max(0, float(x))
    y = max(0, float(y))
    
    # Clamp to actual page boundaries
    x = min(x, max_width - MIN_DIMENSION)
    y = min(y, max_height - MIN_DIMENSION)
    
    # Adjust width and height with visual padding for better appearance
    VISUAL_MARGIN = 15  # Add margin so annotations don't touch page edges
    
    if x + width > max_width - VISUAL_MARGIN:
        # Make annotation more conservative to avoid truncated appearance
        available_width = max_width - x - VISUAL_MARGIN
        # Keep at least 60% of original width, but don't exceed available space
        min_width = max(width * 0.6, MIN_DIMENSION)
        width = max(min_width, available_width) if available_width > min_width else min_width
        
    if y + height > max_height - VISUAL_MARGIN:
        # Conservative height clamping
        available_height = max_height - y - VISUAL_MARGIN
        min_height = max(height * 0.8, MIN_DIMENSION)
        height = max(min_height, available_height) if available_height > min_height else min_height
    
    # Final validation after clamping
    if width < MIN_DIMENSION or height < MIN_DIMENSION:
        return None
    
    result = {
        'page': int(page_num),
        'x': float(x),
        'y': float(y),
        'width': float(width),
        'height': float(height)
    }
    print(f"DEBUG ANNOTATION: Final validated coords: {result}")
    return result


def merge_nearby_positions(positions, merge_threshold=50):
    """
    Merge nearby annotation positions to reduce visual clutter.
    
    Args:
        positions: List of position dictionaries with x, y, width, height
        merge_threshold: Maximum distance between positions to consider for merging
        
    Returns:
        List of merged position dictionaries
    """
    if len(positions) <= 1:
        return positions
    
    # Sort positions by y coordinate (top to bottom)
    sorted_positions = sorted(positions, key=lambda p: p['y'])
    merged = []
    
    current_group = [sorted_positions[0]]
    
    for pos in sorted_positions[1:]:
        # Check if this position is close to any position in the current group
        should_merge = False
        for group_pos in current_group:
            # Calculate distance between positions
            dx = abs(pos['x'] - group_pos['x'])
            dy = abs(pos['y'] - group_pos['y'])
            
            # Merge if positions are close enough
            if dx < merge_threshold and dy < merge_threshold:
                should_merge = True
                break
        
        if should_merge:
            current_group.append(pos)
        else:
            # Finalize current group and start new one
            if current_group:
                merged.append(create_bounding_box(current_group))
            current_group = [pos]
    
    # Don't forget the last group
    if current_group:
        merged.append(create_bounding_box(current_group))
    
    return merged


def create_bounding_box(positions):
    """
    Create a bounding box that encompasses all given positions.
    
    Args:
        positions: List of position dictionaries
        
    Returns:
        Single position dictionary representing the bounding box
    """
    if len(positions) == 1:
        return positions[0]
    
    min_x = min(pos['x'] for pos in positions)
    min_y = min(pos['y'] for pos in positions)
    max_x = max(pos['x'] + pos['width'] for pos in positions)
    max_y = max(pos['y'] + pos['height'] for pos in positions)
    
    # Get page number from first position (all should be on same page)
    page_num = positions[0]['page']
    
    # Apply boundary validation to the merged bounding box
    width = max_x - min_x
    height = max_y - min_y
    
    validated_pos = validate_and_clamp_coordinates(min_x, min_y, width, height, page_num, "")
    
    # Return validated position or fallback to first position if validation fails
    return validated_pos if validated_pos else positions[0]