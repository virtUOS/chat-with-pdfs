"""
UI layouts for the Chat with Docs application.
"""

import os
import streamlit as st
import time
from streamlit_pdf_viewer import pdf_viewer
from streamlit_js_eval import streamlit_js_eval
from streamlit_dimensions import st_dimensions

from ..utils.logger import Logger
from ..utils.source import format_source_for_display
from ..core.document_manager import DocumentManager
from .components import (
    display_document_info, display_document_images, render_advanced_settings,
)
from ..config import MODELS, OLLAMA_MODELS, OLLAMA_SUFFIX, OPENAI_SUFFIX, CUSTOM_MODELS, CUSTOM_SUFFIX
from .handlers import handle_query_submission, handle_settings_change

def render_sidebar() -> None:
    """Render the sidebar with file upload and settings."""
    with st.sidebar:
        # Check if there are any documents uploaded
        has_documents = bool(st.session_state.pdf_data)
        
        if not has_documents:
            # Only show file uploader when no documents are uploaded
            st.header("Document Upload")
            
            # Define callback for file uploader
            def on_file_upload():
                # Try all possible file uploader keys to find the files
                uploaded_files = None
                current_key = f"file_uploader_{st.session_state.interaction_id}"
                
                # Check current session key first
                if current_key in st.session_state and st.session_state[current_key]:
                    uploaded_files = st.session_state[current_key]
                
                # If we found uploaded files, process them
                if uploaded_files:
    
                    # Reset error display dictionary
                    st.session_state["display_errors"] = {}
                    
                    # Initialize or update file queue status
                    if 'file_processing_status' not in st.session_state:
                        st.session_state.file_processing_status = {}
                    
                    # Ensure we have a list of files even if only one file was uploaded
                    if not isinstance(uploaded_files, list):
                        uploaded_files = [uploaded_files]
                    
                    # Track if we had a current file before processing
                    had_current_file = 'current_file' in st.session_state and st.session_state.current_file
                    
                    # Add a progress indicator for multiple file uploads
                    if len(uploaded_files) > 1:
                        st.session_state.multi_upload_progress = {
                            'total': len(uploaded_files),
                            'processed': 0,
                            'started_at': time.time()
                        }
                    
                    # Process each uploaded file
                    for i, uploaded_file in enumerate(uploaded_files):
    
                        with st.spinner(f"Uploading and processing file {uploaded_file.name}..."):
                            # Update processing status
                            st.session_state.file_processing_status[uploaded_file.name] = {
                                'status': 'processing',
                                'started_at': time.time(),
                                'index': i,
                                'total': len(uploaded_files)
                            }
                            
                            # Set as current only if:
                            # - It's the only file being uploaded and we didn't have a current file
                            # - It's the last file in a multi-file upload and we didn't have a current file
                            set_as_current = (not had_current_file and
                                            (len(uploaded_files) == 1 or i == len(uploaded_files) - 1))
                            
                            # Process the file with multi-upload information
                            DocumentManager.process_document(
                                uploaded_file,
                                set_as_current=set_as_current,
                                multi_upload=(len(uploaded_files) > 1)
                            )
                            
                            # Update status after processing
                            if uploaded_file.name in st.session_state.file_processing_status:
                                st.session_state.file_processing_status[uploaded_file.name]['status'] = 'completed'
                                st.session_state.file_processing_status[uploaded_file.name]['finished_at'] = time.time()
                            
                            # Update multi-upload progress if applicable
                            if len(uploaded_files) > 1 and 'multi_upload_progress' in st.session_state:
                                st.session_state.multi_upload_progress['processed'] += 1
                    
                    # Store the files we just processed to a more persistent session state key
                    st.session_state.last_processed_files_data = uploaded_files
            
            # Generate a unique key for the file uploader that changes with each session
            # but keeps the uploaded files until they are processed
            session_key = f"file_uploader_{st.session_state.interaction_id}"
            
            # Display the file uploader with the session-specific key
            st.file_uploader(
                "Upload PDF documents",
                type="pdf",
                key=session_key,
                accept_multiple_files=True,
                on_change=on_file_upload
            )
        else:
            # Create a scrollable container for the document list with dynamic height
            # This code adds padding to between UI widgets so don't put it in between widgets to avoid 
            # too much blank space that looks weird in the UI
            sidebar_screen_height = streamlit_js_eval(js_expressions='screen.height', key='sidebar_height')
            sidebar_max_height = int(sidebar_screen_height * 0.4) if sidebar_screen_height else 400

            # Show document list and management section when documents are available
            st.header("Your Documents")
            
            # Display document count and add a "Delete All" button
            total_docs = len(st.session_state.pdf_data)

            container_height = min(sidebar_max_height, 80 * total_docs)  # 80px per document, max dynamic height
            doc_list_container = st.container(height=container_height)
            
            st.caption(f"{total_docs} document{'s' if total_docs > 1 else ''} available")
            
            # Put all documents in the scrollable container
            with doc_list_container:
                # Create a more visual document list with timestamps
                for doc_name in st.session_state.pdf_data.keys():
                    
                    # Create columns for document name, timestamp, and delete button
                    col1, col3 = st.columns([3, 1])
                    
                    # Highlight the current document
                    is_current = doc_name == st.session_state.get('current_file', '')
                    
                    # Document selection button styled as a link
                    button_label = f"📄 {doc_name}"
                    if is_current:
                        button_label = f"📌 {doc_name}"
                    
                    if col1.button(button_label, key=f"doc_btn_{doc_name}", use_container_width=True,
                                  help=f"Switch to {doc_name}"):
                        st.session_state.current_file = doc_name
                        st.rerun()
                    
                    # Delete button for each document
                    if col3.button("🗑️", key=f"del_doc_{doc_name}", help=f"Remove {doc_name}"):
                        del st.session_state.pdf_data[doc_name]
                        if doc_name in st.session_state.pdf_binary_data:
                            del st.session_state.pdf_binary_data[doc_name]
                        if doc_name in st.session_state.query_engine:
                            del st.session_state.query_engine[doc_name]
                        if doc_name in st.session_state.chat_history:
                            del st.session_state.chat_history[doc_name]
                            
                        # Clean up document-specific responses
                        if doc_name in st.session_state.document_responses:
                            del st.session_state.document_responses[doc_name]
                            
                        # Also remove from processed_files set
                        if doc_name in st.session_state.processed_files:
                            st.session_state.processed_files.remove(doc_name)
                            
                        # Set current file to another document if available
                        if st.session_state.pdf_data:
                            st.session_state.current_file = list(st.session_state.pdf_data.keys())[0]
                        else:
                            st.session_state.current_file = None
                        st.rerun()
                    
                    # Add a divider between documents
                    st.divider()

            # Add "Delete All" button
            if st.button("🗑️ Clear All Files", help="Delete all documents"):
                # Clear all document data
                st.session_state.pdf_data = {}
                st.session_state.pdf_binary_data = {}
                st.session_state.query_engine = {}
                st.session_state.chat_history = {}
                st.session_state.document_responses = {}
                st.session_state.processed_files = set()
                st.session_state.current_file = None
                st.rerun()
        
        st.header("Settings")
        # Model selection

        # Use model display map and display names from session state (initialized in StateManager)
        model_display_map = st.session_state['model_display_map']
        display_names = st.session_state['model_display_names']

        # Determine current display name
        current_model = st.session_state.get('model_name', list(MODELS.keys())[0])
        current_display_name = None
        for disp_name, real_name in model_display_map.items():
            if real_name == current_model:
                current_display_name = disp_name
                break
        if current_display_name is None:
            current_display_name = display_names[0]

        st.selectbox(
            "Select Model",
            display_names,
            index=display_names.index(current_display_name),
            key='selected_display_name',
            on_change=handle_settings_change
        )


        # Add advanced settings section
        render_advanced_settings()
        
        # Clear chat button - only show if there's chat history for the current document
        current_file = st.session_state.get('current_file')
        has_chat_history = (current_file and
                           current_file in st.session_state.get('chat_history', {}) and
                           len(st.session_state.chat_history[current_file]) > 0)
        
        if has_chat_history:
            if st.button("Clear Chat"):
                # Reset chat history for current file
                st.session_state.chat_history[current_file] = []
                st.rerun()


def render_main_content() -> None:
    """Render the main content area with chat interface and document viewer."""
    # Check if we have a current file
    current_file = st.session_state.get('current_file')
    
    if not current_file:
        if not st.session_state.pdf_data:
            # No documents uploaded yet
            st.info("👈 Please upload a PDF document to start chatting")
        else:
            # Documents uploaded but none selected
            st.info("👈 Select a PDF document to start chatting")
        return
    
    # Display document information with total number of documents
    total_docs = len(st.session_state.pdf_data)
    doc_position = list(st.session_state.pdf_data.keys()).index(current_file) + 1
    st.subheader(f"You're now chatting with: {current_file} ({doc_position}/{total_docs})")
    
    # Split the display into two columns - one for PDF and one for content tabs
    pdf_column, content_column = st.columns([50, 50], gap="medium")
    
    # Display PDF in the left column
    with pdf_column:
        if current_file and current_file in st.session_state.pdf_binary_data:
            # Get annotations for this document's chat history
            annotations = []
            
            # Check if we have a document-specific response with sources and answer
            if (current_file in st.session_state.get('document_responses', {}) and
                st.session_state.document_responses[current_file] and
                'sources' in st.session_state.document_responses[current_file] and
                'answer' in st.session_state.document_responses[current_file]):
                
                # Import the function to create annotations from sources
                from ..utils.source import create_annotations_from_sources
                
                # Create annotations based on the document-specific response
                doc_response = st.session_state.document_responses[current_file]
                citation_mapping = doc_response.get('citation_mapping', {})

                annotations = create_annotations_from_sources(
                    doc_response['answer'],
                    doc_response['sources'],
                    citation_mapping
                )
                Logger.info(f"Created {len(annotations)} annotations for document {current_file}")
            
            # Create PDF viewer component with responsive height
            screen_height = streamlit_js_eval(js_expressions='screen.height', key='pdf_screen_height')
            pdf_height = int(screen_height * 0.8) if screen_height else 900  # Increased height
            
            # Define a simple annotation click handler
            def annotation_click_handler(annotation):
                """Handle clicks on source annotations in the PDF viewer."""
                page = annotation.get('page', 'unknown')
                Logger.info(f"Annotation clicked on page {page}")
                # No further action required
            
            pdf_data = st.session_state.pdf_binary_data[current_file]
            pdf_viewer(
                pdf_data,
                height=pdf_height,
                annotations=annotations,
                annotation_outline_size=5,  # Make outlines more visible
                on_annotation_click=annotation_click_handler
            )
        else:
            st.error("PDF data not available. Please try re-uploading the document.")
    
    # Create a scrollable container for the chat with dynamic height
    screen_height = streamlit_js_eval(js_expressions='screen.height', key='screen_height')
    main_container_dimensions = st_dimensions(key="main")
    height_column_container = int(screen_height * 0.5) if main_container_dimensions else 400
    
    # Tabbed content in the right column
    with content_column:
        # Create tabs
        chat_tab, info_tab, images_tab = st.tabs(["Chat", "Document Info", "Images"])

        # Calculate images container height (0.6 * screen_height)
        images_container_height = int(screen_height * 0.6) if main_container_dimensions else 500

        # Chat tab - contains the chat interface
        with chat_tab:
            # Create a scrollable container for chat
            chat_container = st.container(height=height_column_container)

            # Display chat history
            with chat_container:
                if current_file in st.session_state.chat_history:
                    for msg in st.session_state.chat_history[current_file]:
                        with st.chat_message(msg["role"]):
                            st.markdown(msg["content"])

                            # Get citation numbers for this message
                            citation_numbers = msg.get("citations", [])
                            
                            # We only want to display the sources for the citations present in the answer.
                            if citation_numbers:
                                # Display sources if this is an assistant message with sources
                                if msg["role"] == "assistant" and msg.get("sources"):
                                    with st.expander("📂 Show Sources"):
                                        # Only display sources that are actually cited in the response
                                        displayed_sources = set()
                                        
                                        # Only proceed if we have a citation mapping
                                        if "citation_mapping" in msg:
                                            for citation_num in sorted(citation_numbers):
                                                # Get the original source index from the mapping
                                                if str(citation_num) in msg["citation_mapping"]:
                                                    original_source_index = msg["citation_mapping"][str(citation_num)]
                                                    
                                                    if original_source_index in displayed_sources:
                                                        continue  # Skip if already displayed this source
                                                    
                                                    if original_source_index < len(msg["sources"]):
                                                        # Get the source using the original index
                                                        source = msg["sources"][original_source_index]
                                                        
                                                        # DEBUG: Log full source text before formatting
                                                        try:
                                                            full_text = getattr(source, 'text', '')
                                                            Logger.info(f"Full source text (len={len(full_text)}): {full_text[:500].replace('\n', ' ')}")
                                                        except Exception as e:
                                                            Logger.warning(f"Error logging full source text: {e}")
                                                        
                                                        # Extract page number for prominent label
                                                        try:
                                                            if hasattr(source, 'node'):
                                                                page_num = source.node.metadata.get('page', 'N/A')
                                                            elif hasattr(source, 'metadata') and hasattr(source, 'text'):
                                                                page_num = source.metadata.get('page', 'N/A')
                                                            else:
                                                                page_num = 'Unknown'
                                                        except Exception:
                                                            page_num = 'Error'
                                                        
                                                        # Get raw source text
                                                        source_text = format_source_for_display(source)
                                                        
                                                        # Display prominent citation label
                                                        st.markdown(f"##### **Source [{citation_num}] (Page {page_num}):**")
                                                        # Display raw source content as plain text/code block
                                                        st.code(source_text)
                                                        displayed_sources.add(original_source_index)
                                                else:
                                                    Logger.warning(f"Citation number {citation_num} not found in mapping")
                                        else:
                                            st.warning("⚠️ Citation mapping not available. Source information may be incomplete.")
                                        # Add separator between sources
                                        if len(displayed_sources) < len(citation_numbers):
                                            st.divider()
                                                
                                # Display images if present
                                if msg["role"] == "assistant" and msg.get("images") and len(msg["images"]) > 0:
                                    Logger.info(f"Displaying {len(msg['images'])} images in message")
                                    with st.expander("🖼️ View Images", expanded=False):
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
                                                            caption = f"Image from page {page_num}: {meta_caption}"
                                                        else:
                                                            caption = f"Image from page {page_num}"
                                                        st.image(img_bytes, caption=caption)
                                                    else:
                                                        Logger.warning(f"Image file not found: {img_info['file_path']}")
                                                        st.warning(f"Image file not found: {os.path.basename(img_info['file_path'])}")
                                                except Exception as e:
                                                    Logger.error(f"Error displaying image {img_info['file_path']}: {e}")
                                                    st.warning(f"Error displaying image: {os.path.basename(img_info['file_path']) if 'file_path' in img_info else 'Unknown'}")
            
            # Display query suggestions as pills if available
            current_doc_id = st.session_state.pdf_data[current_file].get('doc_id', '')
            if (
                'document_query_suggestions' in st.session_state and
                current_doc_id in st.session_state.get('document_query_suggestions', {}) and
                st.session_state['document_query_suggestions'][current_doc_id]
            ):
                # Get suggestions for this document
                suggestions = st.session_state['document_query_suggestions'][current_doc_id]
                
                if suggestions:
                    # Display suggestions as pills
                    try:
                        # Use the help parameter to show the full suggestion text on hover
                        help_text = "Available suggestions:\n" + "\n".join([f"• {suggestion}" for suggestion in suggestions])
                        
                        selected_suggestion = st.pills(
                            label="Query suggestions:",
                            options=suggestions,
                            selection_mode="single",
                            help=help_text
                        )
                        
                        # If a suggestion is selected
                        if selected_suggestion:
                            # Use the selected suggestion as the prompt
                            prompt = selected_suggestion
                            
                            # Remove the selected suggestion from the list
                            suggestions.remove(selected_suggestion)
                            st.session_state['document_query_suggestions'][current_doc_id] = suggestions
                            
                            # Process the suggestion
                            # Call the query submission handler
                            handle_query_submission(prompt, current_file, chat_container)
                            st.rerun()
                    except Exception as e:
                        Logger.error(f"Error displaying suggestions: {e}")
                        
            # Chat input
            user_query = st.chat_input("Type your question here...")
            if user_query:
                handle_query_submission(user_query, current_file, chat_container)
                st.rerun()
        
        # Information tab
        with info_tab:
            display_document_info(current_file)
        
        # Images tab
        with images_tab:
            display_document_images(current_file, container_height=images_container_height)

