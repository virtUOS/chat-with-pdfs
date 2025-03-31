"""
Query engine and response synthesis for the Chat with Docs application.
"""

import streamlit as st
import re, os
from typing import List, Dict, Any, Optional

from llama_index.core import Settings, QueryBundle
from llama_index.core.response_synthesizers import ResponseMode, get_response_synthesizer
from llama_index.core.query_engine import RetrieverQueryEngine

from .config import CITATION_CHAT_PROMPT, GENERAL_CHAT_PROMPT
from .source import extract_citation_indices
from .image import process_source_for_images, get_document_images


def create_query_engine(vector_index, keyword_index, doc_id, citation_mode=False):
    """
    Create a query engine for a document.
    
    Args:
        vector_index: The vector index for the document
        keyword_index: The keyword index for the document
        doc_id: The document ID
        citation_mode: Whether to use citation mode
        
    Returns:
        A RetrieverQueryEngine instance
    """
    from .custom_retriever import CustomRetriever
    
    # Initialize retriever
    vector_retriever = vector_index.as_retriever(similarity_top_k=3)
    keyword_retriever = keyword_index.as_retriever(similarity_top_k=3)
    
    # Create custom retriever that combines both methods
    retriever = CustomRetriever(
        vector_retriever=vector_retriever,
        keyword_retriever=keyword_retriever,
        mode="OR",
    )
    
    # Select appropriate prompt template based on citation mode
    prompt_template_str = CITATION_CHAT_PROMPT if citation_mode else GENERAL_CHAT_PROMPT
    
    # Convert string template to PromptTemplate
    from llama_index.core import PromptTemplate
    prompt_template = PromptTemplate(prompt_template_str)
    
    # Create response synthesizer with the selected template
    response_synthesizer = get_response_synthesizer(
        response_mode=ResponseMode.COMPACT,
        text_qa_template=prompt_template,
    )
    
    # Create and return query engine
    query_engine = RetrieverQueryEngine(
        retriever=retriever,
        response_synthesizer=response_synthesizer
    )
    
    return query_engine


def process_query(prompt: str, file_name: str, citation_mode: bool = False) -> Dict[str, Any]:
    """
    Process a query and return the response with sources and images.
    
    Args:
        prompt: The user query
        file_name: The name of the file to query
        citation_mode: Whether citation mode is enabled
        
    Returns:
        Dictionary containing answer, sources, and images
    """
    # Check if file_name exists in the session state
    if file_name not in st.session_state.query_engine:
        return {
            'answer': "Error: File not loaded or processed correctly.",
            'sources': [],
            'images': []
        }
    
    # Execute query
    response = st.session_state.query_engine[file_name].query(prompt)
    
    # Get the answer text
    if hasattr(response, 'response'):
        synthesized_answer = response.response
    else:
        synthesized_answer = str(response)
    
    # Get source nodes if available
    source_nodes = []
    if hasattr(response, 'source_nodes'):
        source_nodes = response.source_nodes
    elif 'source_nodes' in dir(response):
        source_nodes = response.source_nodes

    
    # Check if we're in citation mode and verify citations
    if citation_mode:
        # Verify that citation numbers are in the response when citation mode is on
        citation_numbers = extract_citation_indices(synthesized_answer)
        if not citation_numbers:
            # If no citations found, append a warning to the response
            warning_message = "\n\n**Warning: No citations were found in this response. " \
                              "The information may not be directly from your documents.**"
            synthesized_answer += warning_message
    
    # Look for image references in relevant text nodes
    images = []
    if source_nodes:
        # Get the document ID for the current file
        doc_id = st.session_state.file_document_id.get(file_name)
        if doc_id:
            # Get all available images for this document
            available_images = get_document_images(doc_id)
            
            # Process each source node for images
            for source in source_nodes:
                source_images = process_source_for_images(source, doc_id, available_images)
                for img_info in source_images:
                    if not any(img['path'] == img_info['path'] for img in images):
                        images.append(img_info)

    return {
        'answer': synthesized_answer,
        'sources': source_nodes,
        'images': images
    }
