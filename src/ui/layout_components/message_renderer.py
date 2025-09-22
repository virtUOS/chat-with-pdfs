"""
Message renderer component for displaying chat messages.
"""

import os
import streamlit as st

from ...utils.logger import Logger
from ...utils.i18n import I18n
from ..layout_state_manager import LayoutStateManager
from .source_citations import render_source_citations


def render_chat_messages(current_file: str, chat_container) -> None:
    """Render all chat messages for the current file.
    
    Args:
        current_file: Name of the current file
        chat_container: Streamlit container for chat messages
    """
    with chat_container:
        chat_history = LayoutStateManager.get_chat_history(current_file) if current_file else []
        for msg_idx, msg in enumerate(chat_history):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

                # Display source citations for this message
                render_source_citations(msg, msg_idx)
                                        
                # Display images if present
                _render_message_images(msg)


def _render_message_images(msg: dict) -> None:
    """Render images within a chat message.
    
    Args:
        msg: Message dictionary containing potential images
    """
    if msg["role"] == "assistant" and msg.get("images") and len(msg["images"]) > 0:
        Logger.info(f"Displaying {len(msg['images'])} images in message")
        with st.expander(I18n.t('view_images'), expanded=False):
            # Create a grid layout for images (2 columns)
            cols = st.columns(2)
            for i, img_info in enumerate(msg["images"]):
                with cols[i % 2]:
                    try:
                        # Check if image exists
                        if os.path.exists(img_info['file_path']):
                            # Read the image file as binary data
                            with open(img_info['file_path'], 'rb') as f:
                                img_bytes = f.read()
                            page_num = img_info.get('page', 'unknown')
                            meta_caption = img_info.get('caption', '')
                            if meta_caption:
                                caption = I18n.t('image_from_page_with_caption', page=page_num, caption=meta_caption)
                            else:
                                caption = I18n.t('image_from_page', page=page_num)
                            st.image(img_bytes, caption=caption)
                        else:
                            Logger.warning(f"Image file not found: {img_info['file_path']}")
                            st.warning(f"Image file not found: {os.path.basename(img_info['file_path'])}")
                    except Exception as e:
                        Logger.error(f"Error displaying image {img_info['file_path']}: {e}")
                        st.warning(f"Error displaying image: {os.path.basename(img_info['file_path']) if 'file_path' in img_info else 'Unknown'}")