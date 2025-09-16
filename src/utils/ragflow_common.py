"""
RAGFlow-compatible common utility functions for the Chat with Docs application.
"""

import os
import time
import uuid
import ast
import re
import streamlit as st

from ..utils.logger import Logger
from ..utils.prompts import PromptTemplates

from ..ragflow_client import create_client

from ..core.ragflow_chat_engine import RAGFlowChatEngine
from ..core.state_manager import StateManager

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
        list: List of chat assistants
        
    Raises:
        Exception: If unable to fetch assistants
    """
    client = create_client()
    return client.get_chat_assistants()


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
        
        # Get selected assistant
        assistant_id = st.session_state.get('selected_ragflow_assistant')
        if not assistant_id:
            return []
        
        client = create_client()
        
        # Get assistant details to find associated datasets
        assistants_list = client.get_chat_assistants()
        
        # Find the selected assistant
        selected_assistant = None
        for assistant in assistants_list:
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
        
        # Get selected assistant
        assistant_id = st.session_state.get('selected_ragflow_assistant')
        if not assistant_id:
            return {}
        
        client = create_client()
        
        # Get assistant details
        # Get assistant details
        assistants_list = client.get_chat_assistants()
        
        # Find the selected assistant
        selected_assistant = None
        for assistant in assistants_list:
            if assistant.get("id") == assistant_id:
                selected_assistant = assistant
                break
        
        if not selected_assistant:
            return {}
        
        # Get datasets from the assistant (according to RAGFlow API docs)
        datasets = selected_assistant.get("datasets", [])
        dataset_names = {}
        
        # The datasets array already contains the dataset info including names
        for dataset in datasets:
            dataset_id = dataset.get("id")
            dataset_name = dataset.get("name", f"Dataset {dataset_id}")
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


def generate_ragflow_query_suggestions(ragflow_doc: dict) -> None:
    """
    Generate query suggestions for a RAGFlow document using the same approach as LlamaIndex version.
    
    Args:
        ragflow_doc: RAGFlow document dictionary containing id, dataset_id, etc.
    """
    try:
        
        doc_id = ragflow_doc.get('id')
        dataset_id = ragflow_doc.get('dataset_id')
        
        if not doc_id or not dataset_id:
            Logger.warning("Missing document ID or dataset ID for query suggestion generation")
            return
        
        # Check if suggestions already exist for this document
        if doc_id in st.session_state.get('document_query_suggestions', {}):
            Logger.info(f"Query suggestions already exist for document {doc_id}")
            return
        
        Logger.info(f"Generating query suggestions for RAGFlow document {doc_id}...")
        
        client = create_client()
        
        # Get document chunks using SDK
        try:
            # Find the dataset and document
            datasets = client.ragflow.list_datasets()
            target_doc = None
            for dataset in datasets:
                if dataset.id == dataset_id:
                    documents = dataset.list_documents()
                    for doc in documents:
                        if doc.id == doc_id:
                            target_doc = doc
                            break
                    break
            
            if not target_doc:
                Logger.error(f"Document {doc_id} not found in dataset {dataset_id}")
                _mark_query_generation_failure(doc_id)
                return
            
            # Get chunks using SDK
            chunk_objects = target_doc.list_chunks()
            if not chunk_objects:
                Logger.warning(f"No chunks found for document {doc_id}")
                _mark_query_generation_failure(doc_id)
                return
            
            # Extract content from chunks (same as LlamaIndex approach)
            sample_chunks = chunk_objects[:min(5, len(chunk_objects))]  # Use first 5 chunks
            document_content = "\n\n".join([
                chunk.content for chunk in sample_chunks if chunk.content
            ])
            
            # Limit content length (same as LlamaIndex: 5000 chars)
            max_chars = 5000
            if len(document_content) > max_chars:
                document_content = document_content[:max_chars] + "..."
            
            if not document_content.strip():
                Logger.warning(f"No text content found in document chunks for {doc_id}")
                _mark_query_generation_failure(doc_id)
                return
            
            # Debug: Log the content being used
            Logger.info(f"Using document content for suggestions (length: {len(document_content)}): {document_content[:200]}...")
            
            # Use the same approach as summary generation - ask about the document by name
            doc_name = ragflow_doc.get('name', 'this document')
            
            # Create a question that asks the assistant to generate questions about the specific document
            # Use the UI language - translation will be handled in the main query processing
            suggestion_prompt = PromptTemplates.get_query_suggestion_prompt()
            suggestion_query = suggestion_prompt.format(doc_name=doc_name)
            
            # Debug: Log the query being used
            Logger.info(f"Query suggestion query: {suggestion_query}")
            
            # Use RAGFlowChatEngine.process_query but don't store for annotations
            try:
                # Debug: Log the session key that will be used for suggestions
                suggestion_session_key = f'ragflow_session_{doc_name}'
                Logger.info(f"Query suggestion using session key: {suggestion_session_key}")
                Logger.info(f"Current session state keys: {list(st.session_state.keys())}")
                if suggestion_session_key in st.session_state:
                    Logger.info(f"Session {suggestion_session_key} exists with ID: {st.session_state[suggestion_session_key]}")
                else:
                    Logger.info(f"Session {suggestion_session_key} does not exist yet")
                
                # Use store_for_annotations=False to prevent PDF annotations from query suggestions
                response = RAGFlowChatEngine.process_query(suggestion_query, doc_name, store_for_annotations=False)
                
                if response and response.get('answer'):
                    response_text = response['answer'].strip()
                    Logger.info(f"Raw suggestion response: {response_text}")
                    Logger.info(f"ALL Response: {response_text}")
                    
                else:
                    Logger.error("No answer received from RAGFlowChatEngine")
                    _mark_query_generation_failure(doc_id)
                    return
                    
            except Exception as e:
                Logger.error(f"Error using RAGFlowChatEngine for suggestions: {str(e)}")
                _mark_query_generation_failure(doc_id)
                return
            
        except Exception as e:
            Logger.error(f"Error in chunk-based suggestion generation: {str(e)}")
            _mark_query_generation_failure(doc_id)
            return
        
        # Parse the response using the exact same logic as the original
        suggestions = _parse_query_suggestions(response_text)
        
        # Store the suggestions using StateManager (same as original)
        StateManager.store_query_suggestions(doc_id, suggestions)
        
        Logger.info(f"Generated {len(suggestions)} query suggestions for RAGFlow document {doc_id}")
        
    except Exception as e:
        Logger.error(f"Error generating query suggestions for RAGFlow document: {str(e)}")
        if doc_id:
            _mark_query_generation_failure(doc_id)


def _parse_query_suggestions(response_text: str) -> list:
    """
    Parse query suggestions from LLM response with improved parsing for RAGFlow responses.
    
    Args:
        response_text: Raw response text from LLM
        
    Returns:
        List of 3 query suggestions
    """
    suggestions = []
    
    # Debug: Log what we're trying to parse
    Logger.info(f"Parsing suggestions from response: {response_text}")
    
    try:
        # Try to parse as Python list (same as original)
        suggestions = ast.literal_eval(response_text)
        if not isinstance(suggestions, list):
            raise ValueError("Response is not a list")
        Logger.info(f"Successfully parsed as list: {suggestions}")
    except Exception as parse_error:
        Logger.warning(f"Could not parse suggestions as list: {parse_error}")
        
        # Enhanced parsing for RAGFlow responses        
        # First, try to extract lines that look like questions
        lines = response_text.strip().split('\n')
        Logger.info(f"Splitting into lines: {lines}")
        
        for line in lines:
            line = line.strip()
            # Remove numbering, bullets, or dashes
            line = re.sub(r'^[\d\.\-\*\•\s]+', '', line).strip()
            # Remove quotes if present
            line = line.strip('"\'')
            
            if line and ('?' in line or len(line) > 10):  # Must have question mark or be substantial
                suggestions.append(line)
                Logger.info(f"Added suggestion: {line}")
                if len(suggestions) >= 3:
                    break
        
        # If still no good suggestions, try the original regex approach
        if len(suggestions) < 3:
            Logger.info("Not enough suggestions from lines, trying regex...")
            # Look for text in quotes
            quote_matches = re.findall(r'"([^"]*)"', response_text)
            if quote_matches:
                for match in quote_matches:
                    if match not in suggestions:
                        suggestions.append(match)
                        Logger.info(f"Added quoted suggestion: {match}")
                        if len(suggestions) >= 3:
                            break
            
            # If still not enough, try to extract questions by question marks
            if len(suggestions) < 3:
                Logger.info("Still not enough, trying question mark extraction...")
                question_matches = re.findall(r'[^.!?]*\?', response_text)
                for match in question_matches:
                    clean_match = match.strip()
                    if clean_match and clean_match not in suggestions:
                        suggestions.append(clean_match)
                        Logger.info(f"Added question mark suggestion: {clean_match}")
                        if len(suggestions) >= 3:
                            break
    
    # Clean up suggestions
    cleaned_suggestions = []
    for suggestion in suggestions:
        # Remove any remaining numbering or formatting
        clean = re.sub(r'^[\d\.\-\*\•\s]+', '', suggestion).strip()
        clean = clean.strip('"\'')
        
        # Remove RAGFlow citations like [ID:0], [ID:1], [ID:2, ID:3], etc.
        clean = re.sub(r'\s*\[ID:[0-9,\s]+\]', '', clean)
        
        if clean and len(clean) > 5:  # Must be substantial
            cleaned_suggestions.append(clean)
    
    suggestions = cleaned_suggestions
    Logger.info(f"Cleaned suggestions: {suggestions}")
    
    # Ensure we have exactly 3 questions (same as original)
    if len(suggestions) > 3:
        suggestions = suggestions[:3]
    elif len(suggestions) < 3:
        Logger.warning(f"Only got {len(suggestions)} suggestions, adding defaults")
        # Add default questions if we don't have enough (same as original)
        default_questions = [
            "What is the main topic of this document?",
            "What are the key findings in this document?",
            "Summarize this document briefly."
        ]
        
        # Fill in with default questions as needed
        suggestions = suggestions + default_questions[:(3 - len(suggestions))]
    
    Logger.info(f"Final suggestions: {suggestions}")
    return suggestions


def _mark_query_generation_failure(doc_id: str) -> None:
    """
    Mark document as having failed query generation.
    
    Args:
        doc_id: Document ID
    """
    # Mark this document as having failed query generation
    if 'query_suggestion_failures' not in st.session_state:
        st.session_state.query_suggestion_failures = set()
    st.session_state.query_suggestion_failures.add(doc_id)
    
    Logger.info(f"Marked query generation failure for document {doc_id}")


def retry_query_suggestions(doc_id: str, ragflow_doc: dict) -> None:
    """
    Retry generating query suggestions for a failed document.
    
    Args:
        doc_id: Document ID
        ragflow_doc: RAGFlow document dictionary
    """
    # Remove from failures set
    if 'query_suggestion_failures' in st.session_state:
        st.session_state.query_suggestion_failures.discard(doc_id)
    
    # Clear existing suggestions
    if doc_id in st.session_state.get('document_query_suggestions', {}):
        del st.session_state.document_query_suggestions[doc_id]
    
    # Retry generation
    Logger.info(f"Retrying query suggestion generation for document {doc_id}")
    generate_ragflow_query_suggestions(ragflow_doc)


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
    
    # Initialize query suggestions (same as StateManager)
    if 'document_query_suggestions' not in st.session_state:
        st.session_state.document_query_suggestions = {}
    
    # Initialize query suggestion failures
    if 'query_suggestion_failures' not in st.session_state:
        st.session_state.query_suggestion_failures = set()
    
    # Initialize other required session state variables
    if 'processed_files' not in st.session_state:
        st.session_state.processed_files = set()
    
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = {}
    
    if 'file_document_id' not in st.session_state:
        st.session_state.file_document_id = {}
    
    Logger.info("RAGFlow session state initialized")