"""
Centralized state management for the Chat with Docs application.
"""

import streamlit as st
from typing import Any, Dict, List, Set, Optional

# Import from config
from ..config import DEFAULT_MODEL

class StateManager:
    """Centralized manager for session state variables."""
    
    @staticmethod
    def initialize() -> None:
        """Initialize all session state variables."""
        # Document tracking
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
        
        # Document metadata and references
        if 'metadata_store' not in st.session_state:
            st.session_state['metadata_store'] = {}
        
        if 'file_document_id' not in st.session_state:
            st.session_state['file_document_id'] = {}
        
        if 'document_image_map' not in st.session_state:
            st.session_state['document_image_map'] = {}
        
        # Settings
        if 'model_name' not in st.session_state:
            st.session_state['model_name'] = DEFAULT_MODEL
        
        # File tracking
        if 'processed_files' not in st.session_state:
            st.session_state['processed_files'] = set()
        
        if 'pdf_binary_data' not in st.session_state:
            st.session_state['pdf_binary_data'] = {}
        
        # UI state
        if 'just_processed_file' not in st.session_state:
            st.session_state['just_processed_file'] = False
        
        if 'interaction_id' not in st.session_state:
            st.session_state['interaction_id'] = 0
        
        if 'uploader_id' not in st.session_state:
            st.session_state['uploader_id'] = 0
        
        # Document content
        if 'document_summaries' not in st.session_state:
            st.session_state['document_summaries'] = {}
        
        if 'document_responses' not in st.session_state:
            st.session_state['document_responses'] = {}
        
        if 'document_query_suggestions' not in st.session_state:
            st.session_state['document_query_suggestions'] = {}
        
        # Citation UI state
        if 'selected_annotation_index' not in st.session_state:
            st.session_state['selected_annotation_index'] = None
        
        if 'highlighted_citation' not in st.session_state:
            st.session_state['highlighted_citation'] = None
        
        if 'auto_expand_sources' not in st.session_state:
            st.session_state['auto_expand_sources'] = False
            
        # Query suggestion handling
        if 'selected_suggestion' not in st.session_state:
            st.session_state['selected_suggestion'] = None
            
        if 'selected_file' not in st.session_state:
            st.session_state['selected_file'] = None

        # Initialize error state
        if "display_errors" not in st.session_state:
            st.session_state["display_errors"] = {}
    
    # Accessor methods for common operations
    @staticmethod
    def get_current_file() -> Optional[str]:
        """Get the current file name."""
        return st.session_state.get('current_file')
    
    @staticmethod
    def set_current_file(file_name: str) -> None:
        """Set the current file name."""
        st.session_state['current_file'] = file_name
    
    @staticmethod
    def get_chat_history(file_name: str) -> List[Dict[str, Any]]:
        """Get chat history for a specific file."""
        return st.session_state.get('chat_history', {}).get(file_name, [])
    
    @staticmethod
    def add_chat_message(file_name: str, message: Dict[str, Any]) -> None:
        """Add a message to the chat history for a specific file."""
        if file_name not in st.session_state.get('chat_history', {}):
            st.session_state.chat_history[file_name] = []
        st.session_state.chat_history[file_name].append(message)
    
    @staticmethod
    def get_document_id(file_name: str) -> Optional[str]:
        """Get the document ID for a specific file."""
        return st.session_state.get('file_document_id', {}).get(file_name)
    
    @staticmethod
    def get_processed_files() -> Set[str]:
        """Get the set of processed file names."""
        return st.session_state.get('processed_files', set())
        
    @staticmethod
    def get_query_engine(file_name: str) -> Optional[Any]:
        """Get the query engine for a specific file."""
        return st.session_state.get('query_engine', {}).get(file_name)
    
    @staticmethod
    def store_query_engine(file_name: str, engine: Any) -> None:
        """Store a query engine for a specific file."""
        if 'query_engine' not in st.session_state:
            st.session_state['query_engine'] = {}
        st.session_state['query_engine'][file_name] = engine
    
    @staticmethod
    def store_pdf_data(file_name: str, pdf_data: Dict[str, Any]) -> None:
        """Store PDF data for a specific file."""
        if 'pdf_data' not in st.session_state:
            st.session_state['pdf_data'] = {}
        st.session_state['pdf_data'][file_name] = pdf_data
    
    @staticmethod
    def get_pdf_data(file_name: str) -> Optional[Dict[str, Any]]:
        """Get PDF data for a specific file."""
        return st.session_state.get('pdf_data', {}).get(file_name)
    
    @staticmethod
    def store_pdf_binary(file_name: str, binary_data: bytes) -> None:
        """Store binary PDF data for a specific file."""
        if 'pdf_binary_data' not in st.session_state:
            st.session_state['pdf_binary_data'] = {}
        st.session_state['pdf_binary_data'][file_name] = binary_data
    
    @staticmethod
    def store_document_image_map(doc_id: str, image_paths: List[str]) -> None:
        """Store image paths for a specific document."""
        if 'document_image_map' not in st.session_state:
            st.session_state['document_image_map'] = {}
        st.session_state['document_image_map'][doc_id] = image_paths
    
    @staticmethod
    def get_document_image_map(doc_id: str) -> List[str]:
        """Get image paths for a specific document."""
        return st.session_state.get('document_image_map', {}).get(doc_id, [])
    
    @staticmethod
    def store_document_summary(doc_id: str, summary: str) -> None:
        """Store summary for a specific document."""
        if 'document_summaries' not in st.session_state:
            st.session_state['document_summaries'] = {}
        st.session_state['document_summaries'][doc_id] = summary
    
    @staticmethod
    def get_document_summary(doc_id: str) -> Optional[str]:
        """Get summary for a specific document."""
        return st.session_state.get('document_summaries', {}).get(doc_id)
    
    @staticmethod
    def store_query_suggestions(doc_id: str, suggestions: List[str]) -> None:
        """Store query suggestions for a specific document."""
        if 'document_query_suggestions' not in st.session_state:
            st.session_state['document_query_suggestions'] = {}
        st.session_state['document_query_suggestions'][doc_id] = suggestions
    
    @staticmethod
    def get_query_suggestions(doc_id: str) -> List[str]:
        """Get query suggestions for a specific document."""
        return st.session_state.get('document_query_suggestions', {}).get(doc_id, [])