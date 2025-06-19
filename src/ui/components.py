"""
Reusable UI components for the Chat with Docs application.
"""

import os
import streamlit as st
import ast
import fitz  # PyMuPDF

from ..utils.logger import Logger
from ..utils.i18n import I18n

def display_document_info(file_name: str) -> None:
    """Display metadata information for the current document."""
    if file_name not in st.session_state.pdf_data:
        st.warning(I18n.t('document_info_not_available'))
        return
    
    # Get document ID
    doc_id = st.session_state.file_document_id.get(file_name)
    if not doc_id:
        st.warning(I18n.t('document_id_not_found'))
        return
    
    # Find metadata from the vector index
    vector_index = st.session_state.pdf_data[file_name].get('vector_index')
    if not vector_index or not vector_index.docstore:
        st.warning(I18n.t('document_data_not_found'))
        return
    
    # Get a representative node to extract metadata
    try:
        metadata = _extract_document_metadata(vector_index)
        if not metadata:
            raise ValueError("Could not extract metadata")
    except Exception as e:
        st.warning(I18n.t('could_not_retrieve_metadata', error=str(e)))
        return
    
    # Display formatted metadata
    st.subheader(I18n.t('document_information'))
    
    # Title
    if metadata.get('title') and metadata['title'] not in ['None', 'null']:
        st.markdown(f"**{I18n.t('title')}:** {metadata['title']}")
    
    # Author
    if metadata.get('author') and metadata['author'] not in ['None', 'null']:
        st.markdown(f"**{I18n.t('author')}:** {metadata['author']}")
    
    # Keywords
    if metadata.get('keywords') and metadata['keywords'] not in ['None', 'null']:
        st.markdown(f"**{I18n.t('keywords')}:** {metadata['keywords']}")
    
    # Display summary if available (but not for scanned documents)
    # Check if document is likely scanned
    is_likely_scanned = False
    if (
        'ocr_analysis' in st.session_state and
        doc_id in st.session_state.ocr_analysis
    ):
        is_likely_scanned = st.session_state.ocr_analysis[doc_id]['is_likely_scanned']
    
    if (
        not is_likely_scanned and  # Only show summary for non-scanned documents
        doc_id and
        doc_id in st.session_state.get('document_summaries', {}) and
        st.session_state['document_summaries'][doc_id].strip()  # Only show if summary is not empty
    ):
        st.markdown(f"### {I18n.t('summary')}")
        summary = st.session_state['document_summaries'][doc_id]
        st.markdown(f"{summary}")
        st.markdown("---")
    
    # Page count - get from the PDF path if available
    pdf_path = st.session_state.pdf_data[file_name].get('path')
    if pdf_path and os.path.exists(pdf_path):
        try:
            doc = fitz.open(pdf_path)
            st.markdown(f"**{I18n.t('page_count')}:** {len(doc)}")
            doc.close()
        except Exception as e:
            Logger.warning(f"Could not determine page count: {str(e)}")
    
    # Table of Contents
    if metadata.get('toc_items') and metadata['toc_items'] not in ['None', 'null', '[]']:
        st.markdown(f"**{I18n.t('table_of_contents')}:**")
        try:
            # Safely evaluate the toc_items string
            toc_items = ast.literal_eval(metadata['toc_items'])
            if isinstance(toc_items, list) and toc_items:
                for item in toc_items:
                    if isinstance(item, dict) and 'title' in item and 'page' in item:
                        st.markdown(f"- {item['title']} (Page {item['page']})")
        except Exception as e:
            # Fallback to displaying the raw string
            st.markdown(metadata['toc_items'])


def display_document_images(file_name: str, container_height: int | None = None) -> None:
    """Display all images extracted from the document with captions.

    Args:
        file_name (str): The document file name.
        container_height (int, optional): Height for the scrollable container. If None, no scroll container is used.
    """
    if file_name not in st.session_state.pdf_data:
        st.warning(I18n.t('document_images_not_available'))
        return
    
    # Get document ID
    doc_id = st.session_state.file_document_id.get(file_name)
    if not doc_id:
        st.warning(I18n.t('document_id_not_found'))
        return
    
    # Get unified images directly from session state
    from ..core.state_manager import StateManager
    unified_images = StateManager.get_document_unified_images(doc_id)
    
    # Debug log unified images
    Logger.info(f"Got {len(unified_images) if unified_images else 0} unified images for document {doc_id}")
    if unified_images:
        for i, img in enumerate(unified_images[:3]):  # Log first 3 images for debugging
            Logger.info(f"Image {i+1} info: path={img.get('file_path', 'None')}, page={img.get('page', 'None')}, caption='{img.get('caption', 'None')}'")
    
    if unified_images:
        # Display images with rich metadata
        st.subheader(I18n.t('images_from', filename=file_name))
        st.caption(I18n.t('found_images', count=len(unified_images)))

        # Use the provided dynamic height for the images container
        with st.container(height=container_height):
            # Create a grid layout for images (3 columns)
            cols = st.columns(3)

            # Display images in a grid with captions
            displayed_count = 0
            for i, img_info in enumerate(unified_images):
                # Try both 'file_path' and 'path' for backward compatibility
                img_path = img_info.get('file_path') or img_info.get('path')
                if not img_path:
                    Logger.warning(f"Image {i+1} has no path: {img_info}")
                    continue

                # Debug logging
                Logger.info(f"Displaying image: path={img_path}, caption='{img_info.get('caption', 'None')}'")

                # Check if image exists
                if os.path.exists(img_path):
                    try:
                        # Read the image file as binary data
                        with open(img_path, 'rb') as f:
                            img_bytes = f.read()

                        # Get page number and caption
                        page_num = img_info.get('page', 'Unknown')
                        caption = img_info.get('caption', '')

                        # Display image with caption
                        with cols[displayed_count % 3]:
                            if caption:
                                display_caption = I18n.t('image_from_page_with_caption', page=page_num, caption=caption)
                            else:
                                display_caption = I18n.t('page', page=page_num)
                            st.image(img_bytes, caption=display_caption)
                            st.caption(I18n.t('image_count', current=displayed_count+1, total=len(unified_images)))

                        displayed_count += 1
                    except Exception as e:
                        with cols[displayed_count % 3]:
                            Logger.error(f"Error displaying image {img_path}: {e}")
                            st.warning(I18n.t('error_displaying_image', filename=os.path.basename(img_path)))
                        displayed_count += 1
                else:
                    with cols[displayed_count % 3]:
                        Logger.warning(f"Image file not found: {img_path}")
                        st.warning(I18n.t('image_file_not_found', filename=os.path.basename(img_path)))
                    displayed_count += 1

            # If we displayed some images, return early
            if displayed_count > 0:
                return
    
    # Fallback to the old method using document_image_map
    Logger.info("Using fallback method for displaying images")
    image_paths = st.session_state.get('document_image_map', {}).get(doc_id, [])
    
    if not image_paths:
        st.info(I18n.t('no_images_found'))
        return
    
    st.subheader(I18n.t('images_from', filename=file_name))
    st.caption(I18n.t('found_images', count=len(image_paths)))
    
    # Create a grid layout for images (3 columns)
    cols = st.columns(3)
    
    # Display images in a grid
    for i, img_path in enumerate(image_paths):
        # Check if image exists
        if os.path.exists(img_path):
            # Extract page number from filename (format: filename-page-index.jpg)
            page_num = "Unknown"
            try:
                # Pattern is usually: filename-page-index.jpg
                parts = os.path.basename(img_path).split('-')
                if len(parts) >= 2:
                    page_part = parts[-2]
                    page_num = int(page_part)  # No need to add 1, metadata now has correct page numbers
            except Exception as e:
                Logger.warning(f"Could not extract page number from {img_path}: {e}")
            
            try:
                # Read the image file as binary data
                with open(img_path, 'rb') as f:
                    img_bytes = f.read()
                
                # Display image in the appropriate column using binary data
                with cols[i % 3]:
                    st.image(img_bytes, caption=I18n.t('page', page=page_num))
                    st.caption(I18n.t('image_count', current=i+1, total=len(image_paths)))
            except Exception as e:
                with cols[i % 3]:
                    Logger.error(f"Error displaying image {img_path}: {e}")
                    st.warning(I18n.t('error_displaying_image', filename=os.path.basename(img_path)))
        else:
            with cols[i % 3]:
                Logger.warning(f"Image file not found: {img_path}")
                st.warning(I18n.t('image_file_not_found', filename=os.path.basename(img_path)))


def _extract_document_metadata(vector_index):
    """Helper function to extract metadata from a vector index.
    
    Args:
        vector_index: The vector index containing document metadata
        
    Returns:
        dict: Document metadata or None if not found
    """
    # Extract based on docstore API structure
    try:
        # Try to get documents using the docstore API
        # First attempt: use get_all() method if available
        if hasattr(vector_index.docstore, 'get_all'):
            all_documents = vector_index.docstore.get_all()
            if all_documents:
                first_node_id = list(all_documents.keys())[0]
                first_node = all_documents[first_node_id]
                return first_node.metadata
            
        # Second attempt: for newer versions with docs dictionary
        elif hasattr(vector_index.docstore, 'docs'):
            if vector_index.docstore.docs:
                first_node_id = list(vector_index.docstore.docs.keys())[0]
                first_node = vector_index.docstore.docs[first_node_id]
                return first_node.metadata
            
        # Third attempt: get document IDs and fetch first document
        elif hasattr(vector_index.docstore, 'get_document_ids'):
            doc_ids = vector_index.docstore.get_document_ids()
            if doc_ids:
                first_node_id = doc_ids[0]
                first_node = vector_index.docstore.get_document(first_node_id)
                return first_node.metadata
            
        # Fallback method - try to get documents from the index
        elif hasattr(vector_index, 'ref_docs'):
            ref_docs = vector_index.ref_docs
            if ref_docs:
                first_node = list(ref_docs.values())[0]
                return first_node.metadata
    except Exception as e:
        Logger.error(f"Error extracting metadata: {str(e)}")
    
    return None