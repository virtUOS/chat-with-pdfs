"""
Event handlers for the Chat with Docs application UI.
"""

import streamlit as st
import time
from typing import Dict, Any, List, Optional, Union

from ..utils.logger import Logger
from ..core.document_manager import DocumentManager
from ..core.chat_engine import ChatEngine
from ..core.state_manager import StateManager


def handle_file_upload(uploaded_files) -> None:
    """Handle file upload event.
    
    Args:
        uploaded_files: File or list of files from the file uploader
    """
    # Reset error display dictionary
    st.session_state["display_errors"] = {}
    
    # Initialize or update file queue status
    if 'file_processing_status' not in st.session_state:
        st.session_state.file_processing_status = {}
    
    # Ensure we have a list of files even if only one file was uploaded
    if not isinstance(uploaded_files, list):
        uploaded_files = [uploaded_files]
    
    # Track if we had a current file before processing
    had_current_file = 'current_file' in st.session_state and st.session_state.current_file
    
    # Add a progress indicator for multiple file uploads
    if len(uploaded_files) > 1:
        st.session_state.multi_upload_progress = {
            'total': len(uploaded_files),
            'processed': 0,
            'started_at': time.time()
        }
    
    # Process each uploaded file
    for i, uploaded_file in enumerate(uploaded_files):
        # Update processing status
        st.session_state.file_processing_status[uploaded_file.name] = {
            'status': 'processing',
            'started_at': time.time(),
            'index': i,
            'total': len(uploaded_files)
        }
        
        # Set as current only if:
        # - It's the only file being uploaded and we didn't have a current file
        # - It's the last file in a multi-file upload and we didn't have a current file
        set_as_current = (not had_current_file and
                         (len(uploaded_files) == 1 or i == len(uploaded_files) - 1))
        
        # Process the file with multi-upload information
        DocumentManager.process_document(
            uploaded_file,
            set_as_current=set_as_current,
            multi_upload=(len(uploaded_files) > 1)
        )
        
        # Update progress for multi-upload
        if len(uploaded_files) > 1 and 'multi_upload_progress' in st.session_state:
            st.session_state.multi_upload_progress['processed'] += 1
    
    # Increment interaction ID to force UI refresh
    st.session_state.interaction_id = st.session_state.get('interaction_id', 0) + 1
    
    # Force a full page rerun to reflect changes
    st.rerun()


def handle_query_submission(query_text: str, current_file: str, chat_container) -> None:
    """Handle query submission event.
    
    Args:
        query_text: The query text to process
        current_file: The current file to query against
    """
    if not query_text.strip() or not current_file:
        return
    
    # Add the current file to the chat history if it doesn't exist yet
    if current_file not in st.session_state.chat_history:
        st.session_state.chat_history[current_file] = []
    
    # Add user message to the chat history
    st.session_state.chat_history[current_file].append({
        "role": "user",
        "content": query_text
    })

    with chat_container:
        with st.chat_message('user'):
            st.markdown(query_text)
    
        with st.spinner('Thinking...'):
            try:
                # Process the query using the chat engine
                response = ChatEngine.process_query(query_text, current_file)
                
                # Extract information from the response
                answer = response.get('answer', "Sorry, I couldn't process your query.")
                sources = response.get('sources', [])
                images = response.get('images', [])
                citation_mapping = response.get('citation_mapping', {})  # Get the citation mapping
                
                # Extract citation numbers from the response
                from ..utils.source import extract_citation_indices
                citations = extract_citation_indices(answer)
                
                # Create citation page mapping
                citation_pages = {}
                if citations:
                    for i, source in enumerate(sources):
                        citation_num = i + 1
                        # Extract page number from the source
                        page_num = None
                        if hasattr(source, 'node'):
                            page_num = source.node.metadata.get('page', 0)
                        elif hasattr(source, 'metadata'):
                            page_num = source.metadata.get('page', 0)
                        
                        # Store page number if available
                        if page_num is not None:
                            try:
                                page_num = int(page_num)
                                if page_num > 0:
                                    citation_pages[str(citation_num)] = page_num
                            except (ValueError, TypeError):
                                pass
                
                # Add assistant message to the chat history
                st.session_state.chat_history[current_file].append({
                    "role": "assistant",
                    "content": answer,
                    "sources": sources,
                    "images": images,
                    "citations": citations,
                    "citation_pages": citation_pages,
                    "citation_mapping": citation_mapping,  # Use the one already extracted
                    "document": current_file,
                    "response_id": len(st.session_state.chat_history[current_file]) - 1
                })
                
                # Clear the query input for next question
                st.session_state.query_text = ""
                
            except Exception as e:
                # Log the error
                Logger.error(f"Error processing query: {str(e)}")
                
                # Add error message to chat history
                st.session_state.chat_history[current_file].append({
                    "role": "assistant",
                    "content": f"Error processing your query: {str(e)}",
                    "document": current_file
                })


def handle_settings_change(model_name=None) -> None:
    """Handle settings changes.
    
    Args:
        model_name: New model name (if changed)
        auto_expand_sources: New auto-expand sources setting (if changed)
    """
    # Update model if changed
    if model_name is not None and model_name != st.session_state.get('model_name'):
        st.session_state.model_name = model_name
        # Re-initialize LLM settings
        from ..utils.common import initialize_llm_settings
        initialize_llm_settings()
        # Re-create query engines for all loaded files using the new model
        from ..core.chat_engine import ChatEngine
        vector_indices = st.session_state.get('vector_index', {})
        keyword_indices = st.session_state.get('keyword_index', {})
        file_document_ids = st.session_state.get('file_document_id', {})
        if 'query_engine' not in st.session_state:
            st.session_state['query_engine'] = {}
        for file_name in vector_indices:
            vector_index = vector_indices.get(file_name)
            keyword_index = keyword_indices.get(file_name)
            doc_id = file_document_ids.get(file_name)
            if vector_index is not None and keyword_index is not None and doc_id is not None:
                try:
                    query_engine = ChatEngine.create_query_engine(vector_index, keyword_index, doc_id)
                    st.session_state['query_engine'][file_name] = query_engine
                    Logger.info(f"Re-created query engine for file: {file_name} with new model: {model_name}")
                except Exception as e:
                    Logger.error(f"Failed to re-create query engine for file {file_name}: {e}")
        Logger.info(f"Model changed to: {model_name} and all query engines re-created with new model.")
