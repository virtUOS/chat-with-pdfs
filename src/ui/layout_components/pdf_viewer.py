"""
PDF viewer component for displaying documents with annotations.
"""

import streamlit as st
from streamlit_pdf_viewer import pdf_viewer
from streamlit_js_eval import streamlit_js_eval

from ...utils.logger import Logger
from ...utils.i18n import I18n
from ...ragflow_client import create_client
from ..layout_state_manager import LayoutStateManager
from .pdf_utils import calculate_pdf_height, extract_page_dimensions_immediately
from .annotation_handler import create_annotation_click_handler, create_annotations_for_document


def render_pdf_viewer(current_file: str, current_ragflow_doc: dict) -> None:
    """Render the PDF viewer with annotations and responsive height.
    
    Args:
        current_file: Name of the current file
        current_ragflow_doc: RAGFlow document dictionary
    """
    # Try to get PDF data from RAGFlow
    pdf_data = None
    
    # Check if we have cached PDF data
    pdf_cache_key = f"ragflow_pdf_{current_file}"
    if pdf_cache_key in st.session_state:
        pdf_data = st.session_state[pdf_cache_key]
    elif current_ragflow_doc:
        # Download PDF from RAGFlow using SDK
        pdf_data = _download_pdf_from_ragflow(current_file, current_ragflow_doc, pdf_cache_key)
    
    if pdf_data:
        _render_pdf_with_annotations(pdf_data, current_file)
    else:
        st.info(I18n.t('pdf_loading'))


def _download_pdf_from_ragflow(current_file: str, current_ragflow_doc: dict, pdf_cache_key: str) -> bytes | None:
    """Download PDF from RAGFlow and cache it.
    
    Args:
        current_file: Name of the current file
        current_ragflow_doc: RAGFlow document dictionary
        pdf_cache_key: Cache key for storing PDF data
        
    Returns:
        PDF data as bytes or None if failed
    """
    try:
        with st.spinner(I18n.t('loading_pdf_from_ragflow')):
            client = create_client()
            
            dataset_id = current_ragflow_doc.get('dataset_id')
            doc_id = current_ragflow_doc.get('id')
            
            if dataset_id and doc_id:
                # Use RAGFlow SDK to get the document object and download content
                datasets = client.ragflow.list_datasets()
                target_dataset = None
                for dataset in datasets:
                    if dataset.id == dataset_id:
                        target_dataset = dataset
                        break
                
                if target_dataset:
                    documents = target_dataset.list_documents()
                    target_doc = None
                    for doc in documents:
                        if doc.id == doc_id:
                            target_doc = doc
                            break
                    
                    if target_doc:
                        # Download the document content using SDK
                        pdf_data = target_doc.download()
                        
                        # Validate that we actually got PDF data
                        if pdf_data and isinstance(pdf_data, bytes) and pdf_data.startswith(b'%PDF'):
                            # Cache the PDF data
                            st.session_state[pdf_cache_key] = pdf_data
                            Logger.info(f"Successfully downloaded PDF for {current_file} using SDK (size: {len(pdf_data)} bytes)")
                            
                            # Extract page dimensions immediately for annotations
                            extract_page_dimensions_immediately(pdf_data, current_ragflow_doc)
                            return pdf_data
                        else:
                            Logger.error(f"Downloaded data is not a valid PDF (type: {type(pdf_data)}, starts with: {pdf_data[:20] if pdf_data else 'None'})")
                            st.error("Downloaded file is not a valid PDF document")
                    else:
                        st.error(f"Document {doc_id} not found in dataset")
                else:
                    st.error(f"Dataset {dataset_id} not found")
            else:
                st.error(I18n.t('document_dataset_id_not_available'))
                
    except Exception as e:
        Logger.error(f"Error downloading PDF using SDK: {str(e)}")
        st.error(I18n.t('error_downloading_pdf', error=str(e)))
    
    return None


def _render_pdf_with_annotations(pdf_data: bytes, current_file: str) -> None:
    """Render the PDF viewer with annotations.
    
    Args:
        pdf_data: PDF data as bytes
        current_file: Name of the current file
    """
    # Get annotations for this document's chat history
    annotations = create_annotations_for_document(current_file)
    
    # Create PDF viewer component with responsive height
    screen_height = streamlit_js_eval(js_expressions='screen.height', key='pdf_screen_height')
    pdf_height = calculate_pdf_height(screen_height)

    # Create annotation click handler
    annotation_click_handler = create_annotation_click_handler()
    
    # Get scroll to annotation from session state
    scroll_to_annotation = LayoutStateManager.get_scroll_to_annotation()
    
    pdf_viewer(
        pdf_data,
        height=pdf_height,
        width="100%",  # Use dynamic width based on container
        annotations=annotations,
        annotation_outline_size=5,  # Make outlines more visible
        on_annotation_click=annotation_click_handler,
        scroll_to_annotation=scroll_to_annotation
    )
    
    # Debug logging
    if scroll_to_annotation is not None:
        Logger.info(f"PDF viewer rendered with scroll_to_annotation={scroll_to_annotation}")