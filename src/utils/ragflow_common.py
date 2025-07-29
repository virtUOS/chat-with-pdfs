"""
RAGFlow-compatible common utility functions for the Chat with Docs application.
"""

import os
import time
import uuid
import streamlit as st

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
    """Initialize RAGFlow settings - no model configuration needed for chat assistants."""
    
    # RAGFlow uses pre-configured chat assistants with their own models
    # No model configuration needed here
    Logger.info("[RAGFlow INIT] Using pre-configured chat assistants - no model setup required")
    
    return None


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


def get_available_ragflow_assistants():
    """
    Get available chat assistants from RAGFlow server.
    
    Returns:
        list: List of available chat assistant dictionaries from RAGFlow
    """
    try:
        from ..ragflow_client import create_client
        client = create_client()
        response = client.get_chat_assistants()
        
        if response.get('code') == 0:
            return response.get('data', [])
        else:
            Logger.error(f"Failed to get RAGFlow assistants: {response.get('message')}")
            return []
    except Exception as e:
        Logger.error(f"Error fetching RAGFlow assistants: {str(e)}")
        return []


def get_selected_ragflow_assistant():
    """
    Get the selected chat assistant ID for RAGFlow.
    
    Returns:
        str: Selected assistant ID from session state or None
    """
    return st.session_state.get('selected_ragflow_assistant')


def set_selected_ragflow_assistant(assistant_id: str):
    """
    Set the selected chat assistant ID in session state.
    
    Args:
        assistant_id: The ID of the selected assistant
    """
    st.session_state.selected_ragflow_assistant = assistant_id
    # Also store the assistant ID for the chat engine to use
    st.session_state.ragflow_chat_id = assistant_id


def get_assistant_documents():
    """
    Get documents from the selected assistant's datasets.
    
    Returns:
        list: List of documents from all datasets associated with the selected assistant
    """
    try:
        from ..ragflow_client import create_client
        
        # Get selected assistant
        assistant_id = st.session_state.get('selected_ragflow_assistant')
        if not assistant_id:
            return []
        
        client = create_client()
        
        # Get assistant details to find associated datasets
        assistants_response = client.get_chat_assistants()
        if assistants_response.get('code') != 0:
            Logger.error(f"Failed to get assistants: {assistants_response.get('message')}")
            return []
        
        # Find the selected assistant
        selected_assistant = None
        for assistant in assistants_response.get('data', []):
            if assistant.get('id') == assistant_id:
                selected_assistant = assistant
                break
        
        if not selected_assistant:
            Logger.error(f"Selected assistant {assistant_id} not found")
            return []
        
        # Get datasets from the assistant (according to RAGFlow API docs)
        datasets = selected_assistant.get('datasets', [])
        if not datasets:
            Logger.info("Selected assistant has no datasets associated")
            return []
        
        # Get documents from all datasets
        all_documents = []
        for dataset in datasets:
            dataset_id = dataset.get('id')
            if not dataset_id:
                continue
            try:
                docs_response = client.get_documents(dataset_id)
                if docs_response.get('code') == 0:
                    docs_data = docs_response.get('data', {})
                    documents = docs_data.get('docs', []) if isinstance(docs_data, dict) else docs_data
                    
                    # Add dataset info to each document
                    for doc in documents:
                        doc['dataset_id'] = dataset_id
                        doc['dataset_name'] = f"Dataset {dataset_id}"  # Could be enhanced to get actual dataset name
                    
                    all_documents.extend(documents)
                else:
                    Logger.error(f"Failed to get documents from dataset {dataset_id}: {docs_response.get('message')}")
            except Exception as e:
                Logger.error(f"Error getting documents from dataset {dataset_id}: {str(e)}")
        
        Logger.info(f"Found {len(all_documents)} documents in assistant's datasets")
        return all_documents
        
    except Exception as e:
        Logger.error(f"Error getting assistant documents: {str(e)}")
        return []


def get_assistant_dataset_names():
    """
    Get dataset names for the selected assistant.
    
    Returns:
        dict: Mapping of dataset_id to dataset_name
    """
    try:
        from ..ragflow_client import create_client
        
        # Get selected assistant
        assistant_id = st.session_state.get('selected_ragflow_assistant')
        if not assistant_id:
            return {}
        
        client = create_client()
        
        # Get assistant details
        assistants_response = client.get_chat_assistants()
        if assistants_response.get('code') != 0:
            return {}
        
        # Find the selected assistant
        selected_assistant = None
        for assistant in assistants_response.get('data', []):
            if assistant.get('id') == assistant_id:
                selected_assistant = assistant
                break
        
        if not selected_assistant:
            return {}
        
        # Get datasets from the assistant (according to RAGFlow API docs)
        datasets = selected_assistant.get('datasets', [])
        dataset_names = {}
        
        # The datasets array already contains the dataset info including names
        for dataset in datasets:
            dataset_id = dataset.get('id')
            dataset_name = dataset.get('name', f'Dataset {dataset_id}')
            if dataset_id:
                dataset_names[dataset_id] = dataset_name
        
        return dataset_names
        
    except Exception as e:
        Logger.error(f"Error getting dataset names: {str(e)}")
        return {}


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