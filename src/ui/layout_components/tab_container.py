"""
Tab container component for organizing content tabs.
"""

import streamlit as st

from ...utils.i18n import I18n
from ..components import display_ragflow_document_info, display_ragflow_document_images
from .upload_workflow import render_upload_interface


def render_content_tabs(current_ragflow_doc: dict, images_container_height: int, chat_tab_content) -> None:
    """Render the content tabs (chat, info, images, upload).
    
    Args:
        current_ragflow_doc: RAGFlow document dictionary
        images_container_height: Height for the images container
        chat_tab_content: Function to render chat tab content
    """
    # Create tabs - add upload tab
    if current_ragflow_doc:
        # When document is selected, show all tabs with chat as primary
        chat_tab, info_tab, images_tab, upload_tab = st.tabs([
            I18n.t('chat'),
            I18n.t('document_info'),
            I18n.t('images'),
            "📤 Upload Documents"
        ])
    else:
        # When no document selected, make upload tab more prominent
        upload_tab, chat_tab, info_tab, images_tab = st.tabs([
            "📤 Upload Documents",
            I18n.t('chat'),
            I18n.t('document_info'),
            I18n.t('images')
        ])

    # Chat tab - contains the chat interface
    with chat_tab:
        if current_ragflow_doc:
            chat_tab_content()
        else:
            st.info("Select a document from the sidebar to start chatting, or upload new documents using the Upload tab.")
    
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
    
    # Upload tab - new functionality
    with upload_tab:
        render_upload_interface()