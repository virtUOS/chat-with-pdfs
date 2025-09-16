"""
Query suggestions component for document interaction.

Handles the display of query suggestion pills and retry functionality
for failed suggestion generation.
"""

import streamlit as st
from typing import Dict, Any

from ...utils.logger import Logger
from ...utils.i18n import I18n
from ...utils.ragflow_common import retry_query_suggestions
from ..layout_state_manager import LayoutStateManager


def render_query_suggestions(current_ragflow_doc: Dict[str, Any], chat_container=None) -> None:
    """
    Render query suggestion pills or retry button for the current document.
    
    Args:
        current_ragflow_doc: Current RAGFlow document information
        chat_container: Streamlit container for chat display (optional)
    """
    current_doc_id = current_ragflow_doc.get('id', '')
    
    if not current_doc_id:
        return
    
    # Check if query generation failed for this document
    if LayoutStateManager.is_query_suggestion_failed(current_doc_id):
        _render_retry_suggestions(current_doc_id, current_ragflow_doc)
    elif LayoutStateManager.has_query_suggestions(current_doc_id):
        _render_suggestion_pills(current_doc_id, chat_container)


def _render_retry_suggestions(current_doc_id: str, current_ragflow_doc: Dict[str, Any]) -> None:
    """
    Render retry button for failed query suggestions.
    
    Args:
        current_doc_id: Document ID
        current_ragflow_doc: Document information
    """
    # Show failure message and retry button
    col1, col2 = st.columns([3, 1])
    with col1:
        st.warning("⚠️ Query suggestions failed to generate properly")
    with col2:
        if st.button("🔄 Retry", key=f"retry_suggestions_{current_doc_id}", 
                    help="Try generating suggestions again"):
            retry_query_suggestions(current_doc_id, current_ragflow_doc)
            st.rerun()


def _render_suggestion_pills(current_doc_id: str, chat_container=None) -> None:
    """
    Render query suggestion pills for a document.
    
    Args:
        current_doc_id: Document ID to get suggestions for
        chat_container: Streamlit container for chat display (optional)
    """
    suggestions = LayoutStateManager.get_query_suggestions(current_doc_id)
    
    if not suggestions:
        return
    
    # Display suggestions as pills
    try:
        # Use the help parameter to show the full suggestion text on hover
        help_text = I18n.t('available_suggestions') + ":\n" + "\n".join([f"• {suggestion}" for suggestion in suggestions])
        
        selected_suggestion = st.pills(
            label=I18n.t('query_suggestions'),
            options=suggestions,
            selection_mode="single",
            help=help_text
        )
        
        # If a suggestion is selected
        if selected_suggestion:
            _handle_suggestion_selection(selected_suggestion, current_doc_id, chat_container)
    
    except Exception as e:
        Logger.error(f"Error rendering suggestion pills: {e}")
        st.error(f"Error displaying suggestions: {str(e)}")


def _handle_suggestion_selection(selected_suggestion: str, current_doc_id: str, chat_container=None) -> None:
    """
    Handle selection of a query suggestion.
    
    Args:
        selected_suggestion: The selected suggestion text
        current_doc_id: Document ID
        chat_container: Streamlit container for chat display (optional)
    """
    # Use the selected suggestion as the prompt
    prompt = selected_suggestion
    
    # Remove the selected suggestion from the list
    suggestions = LayoutStateManager.get_query_suggestions(current_doc_id)
    if selected_suggestion in suggestions:
        suggestions.remove(selected_suggestion)
        
        # Update the session state with the modified list
        if 'document_query_suggestions' not in st.session_state:
            st.session_state.document_query_suggestions = {}
        st.session_state.document_query_suggestions[current_doc_id] = suggestions
    
    # If we have a chat container, process immediately
    if chat_container is not None:
        # Import here to avoid circular imports
        from ..handlers import handle_query_submission
        
        current_file = LayoutStateManager.get_current_file()
        if current_file:
            handle_query_submission(prompt, current_file, chat_container)
    else:
        # Store the suggestion as the next prompt to be processed by the chat input
        st.session_state.suggested_prompt = prompt
    
    # Trigger a rerun to update the interface
    st.rerun()