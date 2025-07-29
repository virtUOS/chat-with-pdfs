"""
RAGFlow-compatible common utility functions for the Chat with Docs application.
"""

import os
import time
import uuid
import streamlit as st

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


def initialize_ragflow_settings():
    """Initialize RAGFlow settings and store model configuration."""
    
    model_name = st.session_state.get('model_name', DEFAULT_MODEL)
    model_settings = MODELS.get(model_name, MODELS[DEFAULT_MODEL])
    temperature = model_settings.get("temperature", 0.2)
    
    # Store model configuration for RAGFlow usage
    Logger.info(f"[RAGFlow INIT] Requested model: {model_name}")
    
    # Store model settings in session state for RAGFlow to use
    st.session_state.ragflow_model_config = {
        'model_name': model_name,
        'temperature': temperature,
        'model_type': 'openai'  # Default type
    }
    
    # Determine model type for RAGFlow configuration
    if model_name in OLLAMA_MODELS:
        st.session_state.ragflow_model_config['model_type'] = 'ollama'
        st.session_state.ragflow_model_config['base_url'] = OLLAMA_ENDPOINT
        Logger.info(f"[RAGFlow INIT] Configured for Ollama model: {model_name} at {OLLAMA_ENDPOINT}")
    elif model_name in CUSTOM_MODELS:
        st.session_state.ragflow_model_config['model_type'] = 'custom'
        st.session_state.ragflow_model_config['api_base'] = CUSTOM_API_ENDPOINT
        st.session_state.ragflow_model_config['api_key'] = CUSTOM_API_KEY
        Logger.info(f"[RAGFlow INIT] Configured for custom model: {model_name} at {CUSTOM_API_ENDPOINT}")
    else:
        st.session_state.ragflow_model_config['model_type'] = 'openai'
        Logger.info(f"[RAGFlow INIT] Configured for OpenAI model: {model_name}")
    
    # Ensure OpenAI API key is set in environment (for fallback)
    os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "")
    
    Logger.info(f"[RAGFlow INIT] Model configuration stored: {st.session_state.ragflow_model_config}")
    
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


def get_available_ragflow_models():
    """
    Get available models from RAGFlow server.
    
    Returns:
        list: List of available model dictionaries from RAGFlow
    """
    try:
        from ..ragflow_client import create_client
        client = create_client()
        response = client.get_available_models()
        
        if response.get('code') == 0:
            return response.get('data', [])
        else:
            Logger.error(f"Failed to get RAGFlow models: {response.get('message')}")
            return []
    except Exception as e:
        Logger.error(f"Error fetching RAGFlow models: {str(e)}")
        return []


def get_ragflow_model_for_assistant():
    """
    Get the selected model name for RAGFlow chat assistant creation.
    
    Returns:
        str: Selected model name from RAGFlow available models
    """
    # Get the selected model from session state
    selected_model = st.session_state.get('selected_ragflow_model')
    
    if selected_model:
        return selected_model
    
    # If no model selected, get the first available model
    available_models = get_available_ragflow_models()
    if available_models:
        first_model = available_models[0].get('name', available_models[0].get('id'))
        Logger.info(f"No model selected, using first available: {first_model}")
        return first_model
    
    # If no models available, raise an error
    raise ValueError("No models available in RAGFlow. Please configure models in your RAGFlow instance.")


def validate_ragflow_environment():
    """
    Validate that RAGFlow environment variables are properly set.
    
    Returns:
        bool: True if environment is valid, False otherwise
    """
    required_vars = ['RAGFLOW_API_KEY', 'RAGFLOW_BASE_URL']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        Logger.error(f"Missing required RAGFlow environment variables: {missing_vars}")
        return False
    
    Logger.info("RAGFlow environment variables validated successfully")
    return True


def initialize_ragflow_session():
    """Initialize RAGFlow-specific session state variables."""
    
    # Initialize RAGFlow-specific session state
    if 'ragflow_initialized' not in st.session_state:
        st.session_state.ragflow_initialized = False
    
    if 'ragflow_dataset_id' not in st.session_state:
        st.session_state.ragflow_dataset_id = None
    
    if 'ragflow_chat_id' not in st.session_state:
        st.session_state.ragflow_chat_id = None
    
    if 'ragflow_document_mapping' not in st.session_state:
        st.session_state.ragflow_document_mapping = {}
    
    # Initialize other required session state variables
    if 'processed_files' not in st.session_state:
        st.session_state.processed_files = set()
    
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = {}
    
    if 'file_document_id' not in st.session_state:
        st.session_state.file_document_id = {}
    
    Logger.info("RAGFlow session state initialized")