"""
Tab container component for organizing content tabs.
"""

import streamlit as st

from ...utils.i18n import I18n
from ..components import display_ragflow_document_info, display_ragflow_document_images


def render_content_tabs(current_ragflow_doc: dict, images_container_height: int, chat_tab_content) -> None:
    """Render the content tabs (chat, info, images).
    
    Args:
        current_ragflow_doc: RAGFlow document dictionary
        images_container_height: Height for the images container
        chat_tab_content: Function to render chat tab content
    """
    # Create tabs
    chat_tab, info_tab, images_tab = st.tabs([I18n.t('chat'), I18n.t('document_info'), I18n.t('images')])

    # Chat tab - contains the chat interface
    with chat_tab:
        chat_tab_content()
    
    # Information tab
    with info_tab:
        if current_ragflow_doc:
            display_ragflow_document_info(current_ragflow_doc)
        else:
            st.info(I18n.t('no_document_selected'))
    
    # Images tab
    with images_tab:
        if current_ragflow_doc:
            display_ragflow_document_images(current_ragflow_doc, container_height=images_container_height)
        else:
            st.info(I18n.t('no_document_selected'))