"""
Common utility functions for the Chat with Docs application.
"""

import os
import time
import uuid
import streamlit as st

from llama_index.core import Settings
from llama_index.llms.openai import OpenAI
from llama_index.llms.openai_like import OpenAILike

from ..config import MODELS, DEFAULT_MODEL, OLLAMA_MODELS, CUSTOM_MODELS, OLLAMA_ENDPOINT, CUSTOM_API_ENDPOINT, CUSTOM_API_KEY
from ..utils.logger import Logger

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


def initialize_llm_settings():
    """Initialize LLM settings."""
    
    model_name = st.session_state.get('model_name', DEFAULT_MODEL)
    model_settings = MODELS.get(model_name, MODELS[DEFAULT_MODEL])
    temperature = model_settings.get("temperature", 0.2)
    
    # Initialize LLM based on model type
    Logger.info(f"[LLM INIT] Requested model: {model_name}")
    if model_name in OLLAMA_MODELS:
        try:
            Logger.info(f"Initializing Ollama model: {model_name} at {OLLAMA_ENDPOINT}")
            from llama_index.llms.ollama import Ollama
            
            # Use the full model name including any version/parameter suffix
            llm = Ollama(
                model=model_name,  # Use complete model name with version/parameters
                temperature=temperature,
                base_url=OLLAMA_ENDPOINT,
                request_timeout=60.0
            )
            Logger.info(f"[LLM INIT] Ollama LLM instance created: {llm}")
        except ImportError:
            Logger.error("Failed to import Ollama. Make sure llama-index-llms-ollama is installed.")
            # Fallback to OpenAI
            llm = OpenAI(model=DEFAULT_MODEL, temperature=temperature)
    elif model_name in CUSTOM_MODELS:
        try:
            Logger.info(f"Initializing OpenAI-like model for vLLM: {model_name} at {CUSTOM_API_ENDPOINT}")
            # Use OpenAI-like client for vLLM with authentication
            llm = OpenAILike(
                model=model_name,
                api_base=CUSTOM_API_ENDPOINT,
                api_key=CUSTOM_API_KEY,
                temperature=temperature,
                is_chat_model=True
            )
            Logger.info(f"[LLM INIT] OpenAI-like vLLM LLM instance created: {llm}")
        except Exception as e:
            Logger.error(f"Failed to initialize OpenAI-like vLLM model: {e}")
            # Fallback to default OpenAI
            llm = OpenAI(model=DEFAULT_MODEL, temperature=temperature)
    else:
        Logger.info(f"Initializing OpenAI model: {model_name}")
        # Regular OpenAI model
        llm = OpenAI(
            model=model_name,
            temperature=temperature
        )
        Logger.info(f"[LLM INIT] OpenAI LLM instance created: {llm}")
    
    # Update the global settings
    Settings.llm = llm
    Logger.info(f"[LLM INIT] Settings.llm set to: {Settings.llm}")
    
    # Ensure OpenAI API key is set in environment
    os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "")
    
    return model_name


def create_empty_directories():
    """Create necessary directories if they don't exist."""
    # Use environment variables for temp directories, default to /tmp subdirectories
    temp_files_path = os.environ.get("TEMP_FILES_PATH", "/tmp/chat-with-pdfs/temp_files")
    tmp_assets_path = os.environ.get("TMP_ASSETS_PATH", "/tmp/chat-with-pdfs/tmp_assets/tmp_images")
    
    # Create temp directories if they don't exist
    os.makedirs(temp_files_path, exist_ok=True)
    os.makedirs(tmp_assets_path, exist_ok=True)


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