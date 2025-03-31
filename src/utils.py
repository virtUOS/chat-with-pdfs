"""
Utility functions for the Chat with Docs application.
"""

import os
import time
import uuid
import streamlit as st
from llama_index.core import Settings
from llama_index.llms.openai import OpenAI

from .config import MODELS, DEFAULT_MODEL


def generate_unique_component_key(prefix, component_type, identifier, context=None):
    """
    Generate a guaranteed unique key for Streamlit UI components.
    
    Args:
        prefix: A prefix for this key (e.g., 'resp', 'src')
        component_type: Type of component (e.g., 'btn', 'input')
        identifier: Specific identifier for this component (e.g., citation number)
        context: Optional context information (e.g., message index in chat history)
        
    Returns:
        A string key guaranteed to be unique across reruns
    """
    # Use a combination of:
    # 1. Session-specific random string (create if not exists)
    if 'component_key_random' not in st.session_state:
        st.session_state.component_key_random = str(uuid.uuid4())[:8]
    
    # 2. Component counter that increments with use
    if 'component_key_counter' not in st.session_state:
        st.session_state.component_key_counter = 0
    st.session_state.component_key_counter += 1
    
    # 3. Timestamp (milliseconds)
    timestamp = int(time.time() * 1000)
    
    # 4. Context string if provided
    context_str = f"_{context}" if context else ""
    
    # Combine all parts
    return f"{prefix}_{st.session_state.component_key_random}_{st.session_state.component_key_counter}_{timestamp}{context_str}_{component_type}_{identifier}"


def generate_stable_component_key(prefix, component_type, identifier, context=None):
    """
    Generate a unique key for Streamlit UI components that remains stable across reruns.
    
    Args:
        prefix: A prefix for this key (e.g., 'resp', 'src')
        component_type: Type of component (e.g., 'btn', 'input')
        identifier: Specific identifier for this component (e.g., citation number)
        context: Optional context information (e.g., message index in chat history)
        
    Returns:
        A string key that is unique but stable for the same component
    """
    # Use a combination of:
    # 1. Session-specific random string (create if not exists)
    if 'component_key_random' not in st.session_state:
        st.session_state.component_key_random = str(uuid.uuid4())[:8]
    
    # 2. Context string if provided (e.g., response index in chat history)
    context_str = f"_{context}" if context is not None else ""
    
    # 3. Create a stable key without timestamps or incrementing counters
    return f"{prefix}_{st.session_state.component_key_random}{context_str}_{component_type}_{identifier}"


def initialize_session_state():
    """Initialize the session state variables."""
    if 'query_engine' not in st.session_state:
        st.session_state['query_engine'] = {}
    
    if 'pdf_data' not in st.session_state:
        st.session_state['pdf_data'] = {}
    
    if 'chat_history' not in st.session_state:
        st.session_state['chat_history'] = {}
    elif not isinstance(st.session_state['chat_history'], dict):
        # Ensure proper type if deserialization issues occur
        print("Warning: chat_history is not a dictionary. Resetting it.")
        st.session_state['chat_history'] = {}
    
    if 'metadata_store' not in st.session_state:
        st.session_state['metadata_store'] = {}
    
    if 'file_document_id' not in st.session_state:
        st.session_state['file_document_id'] = {}
    
    if 'document_image_map' not in st.session_state:
        st.session_state['document_image_map'] = {}
    
    if 'citation_mode' not in st.session_state:
        st.session_state['citation_mode'] = True
    
    if 'model_name' not in st.session_state:
        st.session_state['model_name'] = DEFAULT_MODEL

    if 'processed_files' not in st.session_state:
        st.session_state['processed_files'] = set()
        
    if 'just_processed_file' not in st.session_state:
        st.session_state['just_processed_file'] = False
        
    if 'interaction_id' not in st.session_state:
        st.session_state['interaction_id'] = 0

    if 'uploader_id' not in st.session_state:
        st.session_state['uploader_id'] = 0
        
    if 'document_summaries' not in st.session_state:
        st.session_state['document_summaries'] = {}

    if 'document_responses' not in st.session_state:
        st.session_state['document_responses'] = {}
    
    if 'document_query_suggestions' not in st.session_state:
        st.session_state['document_query_suggestions'] = {}
        
    # The following variables are kept for compatibility but are no longer used for annotation jumping
    # They were previously used for citation button functionality that has been removed
    if 'selected_annotation_index' not in st.session_state:
        st.session_state['selected_annotation_index'] = None
    
    if 'highlighted_citation' not in st.session_state:
        st.session_state['highlighted_citation'] = None
    
    if 'auto_expand_sources' not in st.session_state:
        st.session_state['auto_expand_sources'] = False


def initialize_llm_settings():
    """Initialize LLM settings."""
    model_name = st.session_state.get('model_name', DEFAULT_MODEL)
    model_settings = MODELS.get(model_name, MODELS[DEFAULT_MODEL])
    
    # Initialize LLM
    llm = OpenAI(
        model=model_name,
        temperature=model_settings["temperature"]
    )
    
    # Update the global settings
    Settings.llm = llm
    
    # Ensure OpenAI API key is set in environment
    os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "")
    
    return model_name


def create_empty_directories():
    """Create necessary directories if they don't exist."""
    # Create temp directories if they don't exist
    os.makedirs("temp_files", exist_ok=True)
    os.makedirs("tmp_assets/tmp_images", exist_ok=True)


def format_chat_history(history):
    """
    Format chat history for display.
    
    Args:
        history: List of message dictionaries
        
    Returns:
        Formatted chat history as HTML
    """
    html = ""
    for msg in history:
        role_style = "user-message" if msg["role"] == "user" else "assistant-message"
        msg_text = msg.get("content", "")
        sources_text = ""
        
        # Add sources if present
        if msg.get("sources"):
            sources_text = "<div class='sources'><strong>Sources:</strong><ul>"
            for source in msg["sources"]:
                sources_text += f"<li>{source}</li>"
            sources_text += "</ul></div>"
        
        html += f"<div class='{role_style}'><p>{msg_text}</p>{sources_text}</div>"
    
    return html
