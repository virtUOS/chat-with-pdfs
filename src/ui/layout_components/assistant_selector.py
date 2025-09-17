"""
Assistant selector component for the sidebar.
"""

import streamlit as st

from ...utils.logger import Logger
from ...utils.i18n import I18n
from ...utils.ragflow_common import get_available_ragflow_assistants, set_selected_ragflow_assistant


def render_assistant_selector() -> bool:
    """Render the chat assistant selection interface.
    
    Returns:
        bool: True if an assistant was selected, False otherwise.
    """
    st.header(I18n.t('chat_assistant'))
    
    # Check if assistants list needs refresh (from upload operations)
    if st.session_state.get('assistants_list_needs_refresh', False):
        # Clear cache to force refresh
        if 'ragflow_assistants_cache' in st.session_state:
            del st.session_state.ragflow_assistants_cache
        if 'available_ragflow_assistants' in st.session_state:
            del st.session_state.available_ragflow_assistants
        st.session_state.assistants_list_needs_refresh = False
        Logger.info("Refreshed assistants list due to background operations")
    
    try:
        available_assistants = get_available_ragflow_assistants()
        if available_assistants:
            # Handle both string and dict types in the assistant list
            assistant_names = []
            assistant_ids = []
            
            for assistant in available_assistants:
                if isinstance(assistant, dict):
                    assistant_names.append(assistant.get('name', 'Unnamed Assistant'))
                    assistant_ids.append(assistant.get('id'))
                else:
                    # If it's a string or other type, convert appropriately
                    assistant_names.append(str(assistant))
                    assistant_ids.append(str(assistant))
            
            # Get current selection
            current_selection = st.session_state.get('selected_ragflow_assistant')
            current_index = 0
            if current_selection and current_selection in assistant_ids:
                current_index = assistant_ids.index(current_selection)
            
            selected_name = st.selectbox(
                I18n.t('select_chat_assistant'),
                assistant_names,
                index=current_index,
                key='ragflow_assistant_selector',
                help=I18n.t('chat_assistant_help')
            )
            
            # Store the actual assistant ID
            if selected_name:
                selected_index = assistant_names.index(selected_name)
                selected_assistant_id = assistant_ids[selected_index]
                set_selected_ragflow_assistant(selected_assistant_id)
                return True  # Indicates an assistant was selected
            
            return False
        else:
            st.warning(I18n.t('no_chat_assistants'))
            return False
            
    except Exception as e:
        error_str = str(e)
        Logger.error(f"Error fetching RAGFlow assistants: {error_str}")
        
        # Check if it's an authentication error
        if 'authentication' in error_str.lower() or 'api key' in error_str.lower() or 'invalid' in error_str.lower():
            st.error(I18n.t('api_authentication_failed'))
        else:
            st.error(I18n.t('error_loading_assistants', error=error_str))
        
        st.info(I18n.t('check_ragflow_connection'))
        return False