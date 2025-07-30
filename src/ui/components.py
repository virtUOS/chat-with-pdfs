"""
Reusable UI components for the Chat with Docs application.
"""

import os
import streamlit as st
import ast
import fitz  # PyMuPDF
from datetime import datetime

from ..utils.logger import Logger
from ..utils.i18n import I18n
from ..utils.source import extract_citation_indices, format_source_for_display, get_source_page_numbers_for_display, format_page_numbers_for_display, get_source_annotation_snippets
from ..core.state_manager import StateManager
from ..core.ragflow_chat_engine import RAGFlowChatEngine
from ..core.ragflow_document_manager import RAGFlowDocumentManager
from ..ragflow_client import create_client

def display_ragflow_document_info(ragflow_doc: dict) -> None:
    """Display metadata information for the current RAGFlow document."""
    if not ragflow_doc:
        st.warning("No document information available")
        return
    
    # Get additional document details from RAGFlow API
    doc_details = _get_ragflow_document_details(ragflow_doc)
    
    # Create two columns for better layout
    col1, col2 = st.columns(2)
    
    with col1:
        # Document name with icon
        doc_name = ragflow_doc.get('name', 'Unknown Document')
        st.markdown(f"**📋 Document Name**")
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
            st.markdown(f"**📊 File Size**")
            st.markdown(f"   {size_str}")
            st.markdown("")
        
        # Document type
        doc_type = ragflow_doc.get('type', 'Unknown').upper()
        st.markdown(f"**📎 Document Type**")
        st.markdown(f"   {doc_type}")
        st.markdown("")
    
    with col2:
        # Dataset information - only show ID, not the redundant name
        dataset_id = ragflow_doc.get('dataset_id', 'Unknown')
        st.markdown(f"**🗂️ Dataset ID**")
        st.markdown(f"   `{dataset_id}`")
        st.markdown("")
        
        # Chunk count - get from detailed info if available
        chunk_count = doc_details.get('chunk_num', ragflow_doc.get('chunk_num', 0))
        if chunk_count > 0:
            st.markdown(f"**🧩 Text Chunks**")
            st.markdown(f"   {chunk_count} chunks")
            st.markdown("")
        
        # Page count - try multiple sources
        page_count = doc_details.get('page_count')
        
        # If not available from chunks, try to get from cached PDF
        if not page_count:
            page_count = _get_page_count_from_cached_pdf(ragflow_doc)
        
        if page_count:
            st.markdown(f"**📖 Pages**")
            st.markdown(f"   {page_count} pages")
            st.markdown("")
    
    # Creation and update dates in a single row
    created_date = ragflow_doc.get('create_date')
    update_date = ragflow_doc.get('update_date')
    
    if created_date or update_date:
        st.markdown("**📅 Timestamps**")
        date_col1, date_col2 = st.columns(2)
        
        if created_date:
            # Format the date nicely
            try:
                # Parse the date and format it nicely
                dt = datetime.strptime(created_date, "%a, %d %b %Y %H:%M:%S %Z")
                formatted_date = dt.strftime("%B %d, %Y at %H:%M")
                date_col1.caption(f"Created: {formatted_date}")
            except:
                date_col1.caption(f"Created: {created_date}")
        
        if update_date:
            try:
                dt = datetime.strptime(update_date, "%a, %d %b %Y %H:%M:%S %Z")
                formatted_date = dt.strftime("%B %d, %Y at %H:%M")
                date_col2.caption(f"Updated: {formatted_date}")
            except:
                date_col2.caption(f"Updated: {update_date}")
    
    # Document summary section
    st.markdown("---")
    st.markdown("**📝 Document Summary**")
    
    # Try to get or generate a summary
    summary_data = _get_or_generate_document_summary(ragflow_doc)
    if summary_data:
        # Display the summary text
        if isinstance(summary_data, dict):
            summary_text = summary_data.get('text', '')
            sources = summary_data.get('sources', [])
            citation_mapping = summary_data.get('citation_mapping', {})
        else:
            # Legacy string format
            summary_text = summary_data
            sources = []
            citation_mapping = {}
        
        st.markdown(summary_text)
        
        # Display sources if available (like in chat)
        if sources and citation_mapping:
            # Extract citation numbers from the summary
            citations = extract_citation_indices(summary_text)
            
            if citations:
                with st.expander("📚 Show Sources"):
                    displayed_sources = set()
                    
                    for citation_num in sorted(citations):
                        # Get the original source index from the mapping
                        if str(citation_num) in citation_mapping:
                            original_source_index = citation_mapping[str(citation_num)]
                            
                            if original_source_index in displayed_sources:
                                continue  # Skip if already displayed this source
                            
                            if original_source_index < len(sources):
                                # Get the source using the original index
                                source = sources[original_source_index]
                                
                                # Extract all page numbers that this source spans
                                try:
                                    page_numbers = get_source_page_numbers_for_display(source)
                                    page_display = format_page_numbers_for_display(page_numbers)
                                except Exception:
                                    page_display = 'Error'
                                
                                # Get document name and similarity for nice display
                                if isinstance(source, dict):
                                    doc_name = source.get('metadata', {}).get('document_name', 'Unknown Document')
                                    similarity = source.get('metadata', {}).get('similarity', 0.0)
                                else:
                                    doc_name = 'Unknown Document'
                                    similarity = 0.0
                                
                                # Display in a nice format like the test script
                                st.markdown(f"**{citation_num}. {doc_name}** (similarity: {similarity:.3f})")
                                if page_display not in ['N/A', 'Error']:
                                    st.caption(f"📄 {page_display}")
                                
                                # Check if we have multiple annotation snippets
                                annotation_snippets = get_source_annotation_snippets(source)
                                
                                if annotation_snippets and len(annotation_snippets) > 1:
                                    # Display individual snippets for each annotation
                                    st.markdown("**Multiple text segments:**")
                                    for i, snippet in enumerate(annotation_snippets):
                                        st.markdown(f"**Segment {i+1}** (Page {snippet['page']}):")
                                        st.markdown(f"   _{snippet['text']}_")
                                        if i < len(annotation_snippets) - 1:
                                            st.markdown("")  # Add spacing between snippets
                                else:
                                    # Display single source text as before
                                    source_text = format_source_for_display(source)
                                    st.markdown(f"   {source_text}")
                                
                                st.markdown("---")  # Add separator between sources
                                displayed_sources.add(original_source_index)
    else:
        # Show a button to generate summary
        if st.button("🤖 Generate Summary", key=f"generate_summary_{ragflow_doc.get('id')}"):
            with st.spinner("Generating document summary..."):
                summary_response = _generate_document_summary_with_assistant(ragflow_doc)
                if summary_response:
                    # Store the summary for future use
                    if 'ragflow_document_summaries' not in st.session_state:
                        st.session_state.ragflow_document_summaries = {}
                    st.session_state.ragflow_document_summaries[ragflow_doc.get('id')] = summary_response
                    st.rerun()
                else:
                    st.error("Failed to generate summary")


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
        st.info("No document selected")
        return
    
    doc_name = ragflow_doc.get('name', '')
    pdf_cache_key = f"ragflow_pdf_{doc_name}"
    
    # Check if we have cached PDF data
    if pdf_cache_key not in st.session_state:
        st.info("📄 PDF not loaded yet. Please wait for the PDF to load in the viewer.")
        return
    
    pdf_data = st.session_state[pdf_cache_key]
    
    # Get the document ID from the ragflow document mapping
    ragflow_doc_id = ragflow_doc.get('id')
    if not ragflow_doc_id:
        st.info("Document ID not available")
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
                with st.spinner("Processing document images..."):
                    RAGFlowDocumentManager._process_ragflow_document_images(pdf_data, doc_name, temp_doc_id)
                
                # Use the temporary doc_id
                doc_id = temp_doc_id
                Logger.info(f"Successfully processed images on-demand for RAGFlow document: {doc_id}")
            
        except Exception as e:
            Logger.error(f"Failed to process images on-demand: {e}")
            st.error(f"Could not process document images: {str(e)}")
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
            st.subheader(f"Images from {doc_name}")
            st.caption(f"Found {len(images)} images")
            
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
                    st.markdown(f"*{len(page_images)} image(s) on this page*")
                    
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
                                    caption = f"Image {img_index + 1}"
                                
                                st.image(img_info['image_data'], caption=caption, width=300)
                                
                            except Exception as e:
                                Logger.error(f"Error displaying image {i} on page {page_num}: {e}")
                                st.warning(f"Error displaying image {i+1}")
                    
                    # Add separator between pages
                    if page_num != max(images_by_page.keys()):
                        st.markdown("---")
        else:
            st.info("No images found in this document")
            
    except Exception as e:
        Logger.error(f"Error extracting images: {e}")
        st.error(f"Error extracting images: {str(e)}")


# This function has been removed as it was redundant.
# Images are already extracted during document processing using pymupdf4llm
# and stored in session state via StateManager.store_document_unified_images()


def _extract_image_caption_from_text(page_text: str, img_index: int, page_num: int) -> str:
    """Extract caption for an image from page text using heuristics."""
    import re
    
    try:
        # Split text into lines
        lines = page_text.splitlines()
        
        # Look for common caption patterns (more comprehensive)
        caption_patterns = [
            r'^(Figure|Fig\.|Table|Diagram|Chart|Image|Photo)\s*\d+[:\.]?\s*(.+)',  # Figure 8: caption
            r'^(Figure|Fig\.|Table|Diagram|Chart|Image|Photo)\s*\d+\s+(.+)',       # Figure 8 caption
            r'^(Figure|Fig\.|Table|Diagram|Chart|Image|Photo)\s+\d+[:\.]?\s*(.+)', # Figure 8: caption
            r'^(Figure|Fig\.|Table|Diagram|Chart|Image|Photo)[:\.]?\s*(.+)',       # Figure: caption
        ]
        
        caption_lines = []
        max_caption_length = 300
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            # Check if line matches caption patterns
            for pattern in caption_patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    # Found a caption start - include the full match (e.g., "Figure 8: caption text")
                    if len(match.groups()) >= 2:
                        # Reconstruct the full caption with figure number
                        figure_part = match.group(1)  # "Figure", "Fig.", etc.
                        caption_text = match.group(2)  # The actual caption text
                        # Extract figure number from the original line
                        figure_match = re.search(r'(\d+)', line)
                        if figure_match:
                            figure_num = figure_match.group(1)
                            full_caption = f"{figure_part} {figure_num}: {caption_text}"
                        else:
                            full_caption = f"{figure_part}: {caption_text}"
                        caption_lines.append(full_caption)
                    else:
                        caption_lines.append(match.group(1))
                    
                    # Look for continuation lines
                    for j in range(i + 1, min(i + 5, len(lines))):  # Check next few lines
                        next_line = lines[j].strip()
                        if not next_line:
                            continue
                        # Stop if we hit another section or caption
                        if re.match(r'^(Figure|Fig\.|Table|Diagram|Chart|Image|Photo|#|##|\s*INTRODUCTION|ABSTRACT|REFERENCES)', next_line, re.IGNORECASE):
                            break
                        # Add continuation if it looks like part of caption
                        if len(next_line) < 200 and not re.match(r'^\d{1,4}$', next_line):
                            caption_lines.append(next_line)
                        else:
                            break
                    
                    # Join and clean up caption
                    caption = ' '.join(caption_lines).strip()
                    if len(caption) > max_caption_length:
                        caption = caption[:max_caption_length] + "..."
                    
                    if caption:
                        Logger.info(f"Extracted caption for image {img_index} on page {page_num}: '{caption[:100]}...'")
                        return caption
                    break
        
        # If no specific caption pattern found, look for text near common figure references
        for line in lines:
            line = line.strip()
            if re.search(r'\b(see\s+)?(figure|fig|image|diagram|chart)\b', line, re.IGNORECASE):
                # This might be a reference to a figure, use it as a simple caption
                if len(line) < 200:
                    Logger.info(f"Found figure reference for image {img_index} on page {page_num}: '{line[:100]}...'")
                    return line
        
        Logger.info(f"No caption found for image {img_index} on page {page_num}")
        return ""
        
    except Exception as e:
        Logger.warning(f"Error extracting caption for image {img_index} on page {page_num}: {e}")
        return ""


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
        # Use the chat engine to ask for a summary
        summary_query = f"Please provide a brief summary of the document '{ragflow_doc.get('name', 'this document')}'. Include the main topics, key points, and purpose of the document in 2-3 sentences."
        
        response = RAGFlowChatEngine.process_query(summary_query, ragflow_doc.get('name', ''))
        
        if response and response.get('answer'):
            # Return the full response with sources and citation mapping
            return {
                'text': response['answer'],
                'sources': response.get('sources', []),
                'citation_mapping': response.get('citation_mapping', {})
            }
        
    except Exception as e:
        Logger.error(f"Error generating document summary: {e}")
    
    return None