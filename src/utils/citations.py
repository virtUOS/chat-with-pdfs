"""
Citation handling utilities for the Chat with Docs application.
"""

import re

def extract_citation_indices(answer_text: str):
    """
    Extract citation indices from the answer text.
    Supports RAGFlow formats: [ID:X] and [ID:X, ID:Y].
    
    Args:
        answer_text: The text to extract citation indices from
        
    Returns:
        A list of integers representing the citation indices
    """
    # Find all ID: patterns regardless of bracket format
    # This handles both [ID:1] and [ID:2, ID:3] formats
    citation_matches = re.findall(r'ID:(\d+)', answer_text)
    citation_ids = [int(x) for x in citation_matches]
    
    # Remove duplicates and return sorted list
    return sorted(list(set(citation_ids)))


def is_source_from_current_document(source, current_document_name):
    """
    Check if a source belongs to the currently displayed document.
    
    Args:
        source: Source object with metadata
        current_document_name: Name of the currently displayed document
        
    Returns:
        bool: True if source is from current document
    """
    if not isinstance(source, dict) or 'metadata' not in source:
        print(f"DEBUG: Source invalid - not dict or no metadata: {type(source)}")
        return False
    
    source_doc_name = source['metadata'].get('document_name', '')
    
    print(f"DEBUG: Document name comparison - Source: '{source_doc_name}', Current: '{current_document_name}'")
    
    # Compare document names (handle potential variations)
    result = source_doc_name == current_document_name
    print(f"DEBUG: Document match result: {result}")
    return result