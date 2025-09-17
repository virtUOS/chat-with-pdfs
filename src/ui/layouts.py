"""
UI layouts for the Chat with Docs application.
"""

import streamlit as st
from streamlit_js_eval import streamlit_js_eval
from streamlit_dimensions import st_dimensions

from ..utils.i18n import I18n
from .layout_state_manager import LayoutStateManager
from .layout_components.assistant_selector import render_assistant_selector
from .layout_components.document_list import render_document_list
from .layout_components.settings_panel import render_settings_panel
from .layout_components.pdf_viewer import render_pdf_viewer
from .layout_components.chat_interface import render_chat_interface
from .layout_components.tab_container import render_content_tabs

def render_sidebar() -> None:
    """Render the sidebar with chat assistant selection and knowledge base documents."""
    with st.sidebar:
        # Chat Assistant selection
        assistant_selected = render_assistant_selector()
        
        # Show documents if an assistant was selected
        if assistant_selected:
            render_document_list()
        
        # Settings section
        render_settings_panel()
                

def render_main_content() -> None:
    """Render the main content area with chat interface and document viewer."""
    # Check if we have a selected assistant and current file
    selected_assistant = st.session_state.get('selected_ragflow_assistant')
    current_file = st.session_state.get('current_file')
    
    if not selected_assistant:
        st.info(I18n.t('select_assistant_to_start'))
        return
    
    if not current_file:
        st.info(I18n.t('select_document_to_start'))
        return
    
    # Get current RAGFlow document info
    current_ragflow_doc = st.session_state.get('current_ragflow_doc', {})
    
    # Display document information
    st.subheader(I18n.t('chatting_with', filename=current_file))
    
    # Split the display into two columns - one for PDF and one for content tabs
    pdf_column, content_column = st.columns([50, 50], gap="medium")
    
    # Display PDF in the left column
    with pdf_column:
        render_pdf_viewer(current_file, current_ragflow_doc)
    
    # Get screen dimensions for responsive containers
    screen_height = streamlit_js_eval(js_expressions='screen.height', key='screen_height')
    main_container_dimensions = st_dimensions(key="main")
    
    # Calculate container heights using state manager
    height_column_container = LayoutStateManager.get_chat_container_height(screen_height if main_container_dimensions else None)
    images_container_height = LayoutStateManager.get_images_container_height(screen_height if main_container_dimensions else None)
    
    # Tabbed content in the right column
    with content_column:
        # Define chat tab content as a lambda function
        def chat_tab_content():
            render_chat_interface(current_file, current_ragflow_doc, height_column_container)
        
        # Render content tabs
        render_content_tabs(current_ragflow_doc, images_container_height, chat_tab_content)


