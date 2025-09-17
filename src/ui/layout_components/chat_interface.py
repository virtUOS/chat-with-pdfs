"""
Chat interface component for handling chat input and display.
"""

import streamlit as st

from ...utils.i18n import I18n
from ..layout_state_manager import LayoutStateManager
from ..handlers import handle_query_submission
from .message_renderer import render_chat_messages
from .query_suggestions import render_query_suggestions


def render_chat_interface(current_file: str, current_ragflow_doc: dict, height_column_container: int) -> None:
    """Render the complete chat interface including history, input, and suggestions.
    
    Args:
        current_file: Name of the current file
        current_ragflow_doc: RAGFlow document dictionary
        height_column_container: Height for the chat container
    """
    # Add clear chat button above the chat container
    has_chat_history = LayoutStateManager.has_chat_history(current_file) if current_file else False
    
    if has_chat_history and current_file:
        if st.button(I18n.t('clear_chat'), key="clear_chat_main", help=I18n.t('clear_chat_help')):
            # Reset chat history for current file
            LayoutStateManager.clear_chat_history(current_file)
            st.rerun()
    
    # Create a scrollable container for chat with reduced height to ensure input visibility
    chat_container = st.container(height=height_column_container)

    # Display chat history using message renderer
    render_chat_messages(current_file, chat_container)
                    
    # Display query suggestions as pills if available
    render_query_suggestions(current_ragflow_doc, chat_container)
                    
    # Chat input
    _handle_chat_input(current_file, chat_container)


def _handle_chat_input(current_file: str, chat_container) -> None:
    """Handle chat input and query submission.
    
    Args:
        current_file: Name of the current file
        chat_container: Streamlit container for chat messages
    """
    # Check if we have a suggested prompt from query suggestions
    suggested_prompt = st.session_state.get('suggested_prompt', '')
    if suggested_prompt and current_file:
        # Process the suggested prompt
        handle_query_submission(suggested_prompt, current_file, chat_container)
        # Clear the suggested prompt
        del st.session_state.suggested_prompt
        st.rerun()
    else:
        user_query = st.chat_input(I18n.t('type_question_here'))
        if user_query and current_file:
            handle_query_submission(user_query, current_file, chat_container)
            st.rerun()