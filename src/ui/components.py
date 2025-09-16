"""
Reusable UI components for the Chat with Docs application.
"""

import os
import re
import streamlit as st
import ast
import fitz  # PyMuPDF
from datetime import datetime

from ..utils.logger import Logger
from ..utils.i18n import I18n
from ..utils.prompts import PromptTemplates
from ..core.state_manager import StateManager
from ..core.ragflow_chat_engine import RAGFlowChatEngine
from ..core.ragflow_document_manager import RAGFlowDocumentManager
from ..ragflow_client import create_client

def display_ragflow_document_info(ragflow_doc: dict) -> None:
    """Display metadata information for the current RAGFlow document."""
    if not ragflow_doc:
        st.warning(I18n.t('no_document_info_available'))
        return
    
    # Get additional document details from RAGFlow API
    doc_details = _get_ragflow_document_details(ragflow_doc)
    
    # Create two columns for better layout
    col1, col2 = st.columns(2)
    
    with col1:
        # Document name with icon
        doc_name = ragflow_doc.get('name', I18n.t('unknown_document'))
        st.markdown(f"**📋 {I18n.t('document_name')}**")
        st.markdown(f"   {doc_name}")
        st.markdown("")
        
        # File size if available
        size = ragflow_doc.get('size', 0)
        if size > 0:
            # Convert bytes to human readable format
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size / (1024 * 1024):.1f} MB"
            st.markdown(f"**📊 {I18n.t('file_size')}**")
            st.markdown(f"   {size_str}")
            st.markdown("")
        
        # Document type
        doc_type = ragflow_doc.get('type', I18n.t('unknown')).upper()
        st.markdown(f"**📎 {I18n.t('document_type')}**")
        st.markdown(f"   {doc_type}")
        st.markdown("")
    
    with col2:
        # Dataset information - only show ID, not the redundant name
        dataset_id = ragflow_doc.get('dataset_id', I18n.t('unknown'))
        st.markdown(f"**🗂️ {I18n.t('dataset_id')}**")
        st.markdown(f"   `{dataset_id}`")
        st.markdown("")
        
        # Chunk count - get from detailed info if available
        chunk_count = doc_details.get('chunk_num', ragflow_doc.get('chunk_num', 0))
        if chunk_count > 0:
            st.markdown(f"**🧩 {I18n.t('text_chunks')}**")
            st.markdown(f"   {chunk_count} {I18n.t('chunks')}")
            st.markdown("")
        
        # Page count - try multiple sources
        page_count = doc_details.get('page_count')
        
        # If not available from chunks, try to get from cached PDF
        if not page_count:
            page_count = _get_page_count_from_cached_pdf(ragflow_doc)
        
        if page_count:
            st.markdown(f"**📖 {I18n.t('pages')}**")
            st.markdown(f"   {page_count} {I18n.t('pages_count')}")
            st.markdown("")
    
    # Creation and update dates in a single row
    created_date = ragflow_doc.get('create_date')
    update_date = ragflow_doc.get('update_date')
    
    if created_date or update_date:
        st.markdown(f"**📅 {I18n.t('timestamps')}**")
        date_col1, date_col2 = st.columns(2)
        
        if created_date:
            # Format the date nicely
            try:
                # Parse the date and format it nicely
                dt = datetime.strptime(created_date, "%a, %d %b %Y %H:%M:%S %Z")
                formatted_date = dt.strftime("%B %d, %Y at %H:%M")
                date_col1.caption(f"{I18n.t('created')}: {formatted_date}")
            except:
                date_col1.caption(f"{I18n.t('created')}: {created_date}")
        
        if update_date:
            try:
                dt = datetime.strptime(update_date, "%a, %d %b %Y %H:%M:%S %Z")
                formatted_date = dt.strftime("%B %d, %Y at %H:%M")
                date_col2.caption(f"{I18n.t('updated')}: {formatted_date}")
            except:
                date_col2.caption(f"{I18n.t('updated')}: {update_date}")
    
    # Document summary section
    st.markdown("---")
    st.markdown(f"**📝 {I18n.t('document_summary')}**")
    
    # Try to get or generate a summary
    summary_data = _get_or_generate_document_summary(ragflow_doc)
    if summary_data:
        # Display the summary text
        if isinstance(summary_data, dict):
            summary_text = summary_data.get('text', '')
        else:
            # Legacy string format
            summary_text = summary_data
        
        st.markdown(summary_text)
    else:
        # Show a button to generate summary
        if st.button(I18n.t('generate_summary'), key=f"generate_summary_{ragflow_doc.get('id')}"):
            with st.spinner(I18n.t('generating_summary')):
                summary_response = _generate_document_summary_with_assistant(ragflow_doc)
                if summary_response:
                    # Store the summary for future use
                    if 'ragflow_document_summaries' not in st.session_state:
                        st.session_state.ragflow_document_summaries = {}
                    st.session_state.ragflow_document_summaries[ragflow_doc.get('id')] = summary_response
                    st.rerun()
                else:
                    st.error(I18n.t('failed_generate_summary'))


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


def _get_page_count_from_cached_pdf(ragflow_doc: dict) -> int | None:
    """Get page count from cached PDF data using PyMuPDF."""
    try:
        doc_name = ragflow_doc.get('name', '')
        pdf_cache_key = f"ragflow_pdf_{doc_name}"
        
        # Check if we have cached PDF data
        if pdf_cache_key in st.session_state:
            pdf_data = st.session_state[pdf_cache_key]
            
            # Use PyMuPDF to count pages
            doc = fitz.open(stream=pdf_data, filetype="pdf")
            page_count = len(doc)
            doc.close()
            
            return page_count
        
    except Exception as e:
        Logger.warning(f"Could not get page count from cached PDF: {e}")
    
    return None


def display_ragflow_document_images(ragflow_doc: dict, container_height: int | None = None) -> None:
    """Display images extracted from RAGFlow document using PyMuPDF."""
    if not ragflow_doc:
        st.info(I18n.t('no_document_selected'))
        return
    
    doc_name = ragflow_doc.get('name', '')
    pdf_cache_key = f"ragflow_pdf_{doc_name}"
    
    # Check if we have cached PDF data
    if pdf_cache_key not in st.session_state:
        st.info(I18n.t('pdf_not_loaded_yet'))
        return
    
    pdf_data = st.session_state[pdf_cache_key]
    
    # Get the document ID from the ragflow document mapping
    ragflow_doc_id = ragflow_doc.get('id')
    if not ragflow_doc_id:
        st.info(I18n.t('document_id_not_available'))
        return
    
    # Debug logging to understand the session state
    Logger.info(f"Looking for RAGFlow document ID: {ragflow_doc_id}")
    Logger.info(f"Available ragflow_document_mapping: {st.session_state.get('ragflow_document_mapping', {})}")
    Logger.info(f"Available file_document_id: {st.session_state.get('file_document_id', {})}")
    
    # Find the corresponding document ID in our session state
    # Check if we have a mapping from ragflow doc ID to our internal doc ID
    doc_id = None
    ragflow_mapping = st.session_state.get('ragflow_document_mapping', {})
    
    # Look for the document ID by matching the ragflow document ID
    for file_name, mapped_ragflow_id in ragflow_mapping.items():
        Logger.info(f"Checking file_name: {file_name}, mapped_ragflow_id: {mapped_ragflow_id}")
        if mapped_ragflow_id == ragflow_doc_id:
            # Get the internal document ID for this file
            doc_id = st.session_state.get('file_document_id', {}).get(file_name)
            Logger.info(f"Found matching file: {file_name}, internal doc_id: {doc_id}")
            break
    
    if not doc_id:
        # Try alternative approach - maybe the document name matches directly
        Logger.info("Direct mapping failed, trying document name matching...")
        file_document_id_map = st.session_state.get('file_document_id', {})
        for file_name, internal_doc_id in file_document_id_map.items():
            if doc_name in file_name or file_name in doc_name:
                doc_id = internal_doc_id
                Logger.info(f"Found document by name matching: {file_name} -> {doc_id}")
                break
    
    if not doc_id:
        Logger.warning(f"Could not find document mapping for RAGFlow doc {ragflow_doc_id} ({doc_name})")
        Logger.info("RAGFlow document not processed locally - processing images on-demand...")
        
        # Process images on-demand for RAGFlow documents
        try:
            # Use the ragflow_doc_id as our internal doc_id for this session
            temp_doc_id = f"ragflow_{ragflow_doc_id}"
            
            # Check if we already processed this document in this session
            existing_images = StateManager.get_document_unified_images(temp_doc_id)
            if existing_images:
                Logger.info(f"Using already processed images for {temp_doc_id}")
                doc_id = temp_doc_id
            else:
                # Process images from the downloaded PDF data
                with st.spinner(I18n.t('processing_document_images')):
                    RAGFlowDocumentManager._process_ragflow_document_images(pdf_data, doc_name, temp_doc_id)
                
                # Use the temporary doc_id
                doc_id = temp_doc_id
                Logger.info(f"Successfully processed images on-demand for RAGFlow document: {doc_id}")
            
        except Exception as e:
            Logger.error(f"Failed to process images on-demand: {e}")
            st.error(I18n.t('could_not_process_document_images', error=str(e)))
            return
    
    # Get unified images directly from session state (already extracted by pymupdf4llm)
    unified_images = StateManager.get_document_unified_images(doc_id)
    
    # Debug log unified images
    Logger.info(f"Got {len(unified_images) if unified_images else 0} unified images for RAGFlow document {doc_name} (doc_id: {doc_id})")
    if unified_images:
        for i, img in enumerate(unified_images[:3]):  # Log first 3 images for debugging
            Logger.info(f"Image {i+1} info: path={img.get('file_path', 'None')}, page={img.get('page', 'None')}, caption='{img.get('caption', 'None')}'")
    
    # Use already-extracted images instead of re-extracting
    try:
        images = []
        if unified_images:
            for img_info in unified_images:
                img_path = img_info.get('file_path') or img_info.get('path')
                if img_path and os.path.exists(img_path):
                    try:
                        with open(img_path, 'rb') as f:
                            img_data = f.read()
                        images.append({
                            'image_data': img_data,
                            'page': img_info.get('page', 'Unknown'),
                            'index': img_info.get('index', 0),
                            'format': 'png',
                            'caption': img_info.get('caption', '')
                        })
                    except Exception as e:
                        Logger.warning(f"Could not read image file {img_path}: {e}")
        
        if images:
            st.subheader(I18n.t('images_from', filename=doc_name))
            st.caption(I18n.t('found_images', count=len(images)))
            
            # Sort images by page number first, then by index within page
            sorted_images = sorted(images, key=lambda x: (x.get('page', 0), x.get('index', 0)))
            
            # Use the provided dynamic height for the images container
            with st.container(height=container_height):
                # Group images by page for better organization
                images_by_page = {}
                for img_info in sorted_images:
                    page_num = img_info.get('page', 'Unknown')
                    if page_num not in images_by_page:
                        images_by_page[page_num] = []
                    images_by_page[page_num].append(img_info)
                
                # Display images organized by page
                for page_num in sorted(images_by_page.keys()):
                    page_images = images_by_page[page_num]
                    
                    # Page header
                    st.markdown(f"### 📄 Page {page_num}")
                    st.markdown(f"*{I18n.t('images_on_page', count=len(page_images))}*")
                    
                    # Create columns for images on this page (max 3 per row)
                    num_cols = min(3, len(page_images))
                    cols = st.columns(num_cols)
                    
                    for i, img_info in enumerate(page_images):
                        with cols[i % num_cols]:
                            try:
                                img_index = img_info.get('index', i)
                                extracted_caption = img_info.get('caption', '')
                                
                                # Use extracted caption if available, otherwise use default
                                if extracted_caption:
                                    # Keep the original caption intact (e.g., "Figure 8: Nearest neighbors...")
                                    caption = extracted_caption
                                else:
                                    # Fallback to generic caption if no caption was extracted
                                    caption = I18n.t('image_number', number=img_index + 1)
                                
                                st.image(img_info['image_data'], caption=caption, width=300)
                                
                            except Exception as e:
                                Logger.error(f"Error displaying image {i} on page {page_num}: {e}")
                                st.warning(I18n.t('error_displaying_image_number', number=i+1))
                    
                    # Add separator between pages
                    if page_num != max(images_by_page.keys()):
                        st.markdown("---")
        else:
            st.info(I18n.t('no_images_found_in_document'))

    except Exception as e:
        Logger.error(f"Error extracting images: {e}")
        st.error(I18n.t('error_extracting_images', error=str(e)))

def _get_ragflow_document_details(ragflow_doc: dict) -> dict:
    """Get additional document details from RAGFlow API."""
    try:
        client = create_client()
        
        dataset_id = ragflow_doc.get('dataset_id')
        doc_id = ragflow_doc.get('id')
        
        if not dataset_id or not doc_id:
            return {}
        
        # Try to get document chunks to get accurate chunk count
        chunks_response = client._make_request('GET', f'/api/v1/datasets/{dataset_id}/documents/{doc_id}/chunks')
        if chunks_response.status_code == 200:
            chunks_data = chunks_response.json()
            if chunks_data.get('code') == 0:
                chunks = chunks_data.get('data', {}).get('chunks', [])
                return {
                    'chunk_num': len(chunks),
                    'page_count': _extract_page_count_from_chunks(chunks)
                }
    except Exception as e:
        Logger.warning(f"Could not get detailed document info: {e}")
    
    return {}


def _extract_page_count_from_chunks(chunks: list) -> int | None:
    """Extract page count from document chunks."""
    try:
        max_page = 0
        for chunk in chunks:
            # Look for page information in chunk metadata
            if isinstance(chunk, dict):
                # Check various possible locations for page info
                page_num = None
                if 'page' in chunk:
                    page_num = chunk['page']
                elif 'metadata' in chunk and isinstance(chunk['metadata'], dict):
                    page_num = chunk['metadata'].get('page')
                
                if page_num is not None:
                    try:
                        page_int = int(page_num)
                        max_page = max(max_page, page_int)
                    except (ValueError, TypeError):
                        pass
        
        return max_page if max_page > 0 else None
    except Exception as e:
        Logger.warning(f"Error extracting page count: {e}")
        return None


def _get_or_generate_document_summary(ragflow_doc: dict) -> dict | str | None:
    """Get existing summary or return None to trigger generation."""
    doc_id = ragflow_doc.get('id')
    if not doc_id:
        return None
    
    # Check if we have a cached summary
    summaries = st.session_state.get('ragflow_document_summaries', {})
    return summaries.get(doc_id)


def _generate_document_summary_with_assistant(ragflow_doc: dict) -> dict | None:
    """Generate a document summary using the RAGFlow assistant."""
    try:
        # Get language-appropriate summary query from prompts
        doc_name = ragflow_doc.get('name', 'this document')
        summary_query = PromptTemplates.get_summary_query_prompt().format(doc_name=doc_name)
        
        # Use store_for_annotations=False to prevent PDF annotations from summary generation
        response = RAGFlowChatEngine.process_query(summary_query, ragflow_doc.get('name', ''), store_for_annotations=False)
        
        if response and response.get('answer'):
            # Remove citations from summary text (same as query suggestions)
            summary_text = response['answer']
            summary_text = re.sub(r'\s*\[ID:\d+\]', '', summary_text)
            
            # Return the cleaned summary without sources (no annotations needed)
            return {
                'text': summary_text,
                'sources': [],  # Don't include sources to prevent annotations
                'citation_mapping': {}  # Don't include citation mapping
            }
        
    except Exception as e:
        Logger.error(f"Error generating document summary: {e}")
    
    return None