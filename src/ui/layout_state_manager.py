"""
Centralized state management for layout components.

This module provides a unified interface for accessing and modifying
Streamlit session state used throughout the layout components.
"""

import streamlit as st
from typing import Optional, Dict, List, Any


class LayoutStateManager:
    """Centralized state management for layout components."""
    
    # Assistant and Document State
    @staticmethod
    def get_current_file() -> Optional[str]:
        """Get the currently selected file name."""
        return st.session_state.get('current_file')
    
    @staticmethod
    def set_current_file(file_name: str) -> None:
        """Set the currently selected file name."""
        st.session_state.current_file = file_name
    
    @staticmethod
    def get_selected_assistant() -> Optional[str]:
        """Get the currently selected RAGFlow assistant ID."""
        return st.session_state.get('selected_ragflow_assistant')
    
    @staticmethod
    def get_current_ragflow_doc() -> Dict[str, Any]:
        """Get the current RAGFlow document info."""
        return st.session_state.get('current_ragflow_doc', {})
    
    @staticmethod
    def set_current_ragflow_doc(doc: Dict[str, Any]) -> None:
        """Set the current RAGFlow document info."""
        st.session_state.current_ragflow_doc = doc
    
    # Chat State
    @staticmethod
    def get_chat_history(file_name: str) -> List[Dict[str, Any]]:
        """Get chat history for a specific file."""
        return st.session_state.get('chat_history', {}).get(file_name, [])
    
    @staticmethod
    def clear_chat_history(file_name: str) -> None:
        """Clear chat history for a specific file."""
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = {}
        st.session_state.chat_history[file_name] = []
    
    @staticmethod
    def has_chat_history(file_name: str) -> bool:
        """Check if a file has any chat history."""
        return (file_name and
                file_name in st.session_state.get('chat_history', {}) and
                len(st.session_state.chat_history[file_name]) > 0)
    
    # PDF State
    @staticmethod
    def get_pdf_data(file_name: str) -> Optional[bytes]:
        """Get cached PDF data for a file."""
        cache_key = f"ragflow_pdf_{file_name}"
        return st.session_state.get(cache_key)
    
    @staticmethod
    def set_pdf_data(file_name: str, pdf_data: bytes) -> None:
        """Cache PDF data for a file."""
        cache_key = f"ragflow_pdf_{file_name}"
        st.session_state[cache_key] = pdf_data
    
    @staticmethod
    def has_pdf_data(file_name: str) -> bool:
        """Check if PDF data is cached for a file."""
        cache_key = f"ragflow_pdf_{file_name}"
        return cache_key in st.session_state
    
    # Document Responses and Sources
    @staticmethod
    def get_document_responses(file_name: str) -> Dict[str, Any]:
        """Get document-specific responses."""
        return st.session_state.get('document_responses', {}).get(file_name, {})
    
    @staticmethod
    def has_document_response_with_sources(file_name: str) -> bool:
        """Check if a file has a response with sources and answer."""
        response = LayoutStateManager.get_document_responses(file_name)
        return (response and 
                'sources' in response and 
                'answer' in response)
    
    # Query Suggestions
    @staticmethod
    def get_query_suggestions(doc_id: str) -> List[str]:
        """Get query suggestions for a document."""
        suggestions = st.session_state.get('document_query_suggestions', {}).get(doc_id, [])
        return suggestions if suggestions else []
    
    @staticmethod
    def has_query_suggestions(doc_id: str) -> bool:
        """Check if query suggestions exist for a document."""
        return (doc_id and
                'document_query_suggestions' in st.session_state and
                doc_id in st.session_state.get('document_query_suggestions', {}) and
                st.session_state['document_query_suggestions'][doc_id])
    
    @staticmethod
    def is_query_suggestion_failed(doc_id: str) -> bool:
        """Check if query suggestion generation failed for a document."""
        return doc_id in st.session_state.get('query_suggestion_failures', set())
    
    # Annotation State
    @staticmethod
    def get_annotation_mode() -> str:
        """Get the current annotation mode."""
        return st.session_state.get('annotation_mode', 'smart')
    
    @staticmethod
    def get_citation_to_annotation_mapping() -> Dict[int, List[int]]:
        """Get the citation to annotation position mapping."""
        return st.session_state.get('citation_to_annotation_mapping', {})
    
    @staticmethod
    def set_citation_to_annotation_mapping(mapping: Dict[int, List[int]]) -> None:
        """Set the citation to annotation position mapping."""
        st.session_state['citation_to_annotation_mapping'] = mapping
    
    @staticmethod
    def get_scroll_to_annotation() -> Optional[int]:
        """Get the annotation position to scroll to."""
        return st.session_state.get('scroll_to_annotation')
    
    @staticmethod
    def set_scroll_to_annotation(position: int) -> None:
        """Set the annotation position to scroll to."""
        st.session_state.scroll_to_annotation = position
    
    # Document Mapping
    @staticmethod
    def get_ragflow_document_mapping() -> Dict[str, str]:
        """Get the RAGFlow document ID to name mapping."""
        return st.session_state.get('ragflow_document_mapping', {})
    
    @staticmethod
    def set_ragflow_document_mapping(doc_id: str, doc_name: str) -> None:
        """Set RAGFlow document ID to name mapping."""
        if 'ragflow_document_mapping' not in st.session_state:
            st.session_state.ragflow_document_mapping = {}
        st.session_state.ragflow_document_mapping[doc_id] = doc_name
    
    # UI State Helpers
    @staticmethod
    def get_chat_container_height(screen_height: Optional[int]) -> int:
        """Calculate optimal chat container height."""
        return int(screen_height * 0.35) if screen_height else 300
    
    @staticmethod
    def get_pdf_height(screen_height: Optional[int]) -> int:
        """Calculate optimal PDF viewer height."""
        return int(screen_height * 0.8) if screen_height else 900
    
    @staticmethod
    def get_images_container_height(screen_height: Optional[int]) -> int:
        """Calculate optimal images container height."""
        return int(screen_height * 0.4) if screen_height else 500
    
    @staticmethod
    def get_sidebar_max_height(screen_height: Optional[int]) -> int:
        """Calculate optimal sidebar document list height."""
        return int(screen_height * 0.4) if screen_height else 400