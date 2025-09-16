"""
Citation handling utilities for the Chat with Docs application.
"""

import re

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
        return False
    
    source_doc_name = source['metadata'].get('document_name', '')
    
    # Compare document names (handle potential variations)
    return source_doc_name == current_document_name