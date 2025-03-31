"""
Chat with Docs - Main Application

This application allows users to upload PDF documents and chat with them using LLM technology.
Documents are processed with LlamaIndex and responses are generated using the specified model.
"""

import os
import streamlit as st
import time
import ast  # For safely evaluating strings
from streamlit_pdf_viewer import pdf_viewer
from streamlit_js_eval import streamlit_js_eval
from streamlit_dimensions import st_dimensions

# Import local modules
from src.config import MODELS, DEFAULT_MODEL
from src.utils import initialize_session_state, initialize_llm_settings, create_empty_directories
from src.document import save_uploaded_file, process_pdf
from src.chat_engine import create_query_engine, process_query
from src.source import extract_citation_indices, format_source_for_display


def display_document_info(file_name):
    """Display metadata information for the current document."""
    if file_name not in st.session_state.pdf_data:
        st.warning("Document information not available")
        return
    
    # Get document ID
    doc_id = st.session_state.file_document_id.get(file_name)
    if not doc_id:
        st.warning("Document ID not found")
        return
    
    # Find metadata from the vector index
    vector_index = st.session_state.pdf_data[file_name].get('vector_index')
    if not vector_index or not vector_index.docstore:
        st.warning("Document data not found")
        return
    
    # Get a representative node to extract metadata
    try:
        # Try to get documents using the docstore API
        # First attempt: use get_all() method if available
        if hasattr(vector_index.docstore, 'get_all'):
            # Get all documents and take the first one
            all_documents = vector_index.docstore.get_all()
            if all_documents:
                # Get the first document
                first_node_id = list(all_documents.keys())[0]
                first_node = all_documents[first_node_id]
                metadata = first_node.metadata
            else:
                raise ValueError("No documents found in docstore")
        # Second attempt: for newer versions with get_document_by_id or similar method
        elif hasattr(vector_index.docstore, 'docs'):
            # Access the docs dictionary directly
            if vector_index.docstore.docs:
                first_node_id = list(vector_index.docstore.docs.keys())[0]
                first_node = vector_index.docstore.docs[first_node_id]
                metadata = first_node.metadata
            else:
                raise ValueError("No documents found in docstore.docs")
        # Third attempt: get document IDs and fetch first document
        elif hasattr(vector_index.docstore, 'get_document_ids'):
            doc_ids = vector_index.docstore.get_document_ids()
            if doc_ids:
                first_node_id = doc_ids[0]
                first_node = vector_index.docstore.get_document(first_node_id)
                metadata = first_node.metadata
            else:
                raise ValueError("No document IDs found")
        else:
            # Fallback method - try to get documents from the index
            if hasattr(vector_index, 'ref_docs'):
                # Some versions store reference documents directly
                ref_docs = vector_index.ref_docs
                if ref_docs:
                    first_node = list(ref_docs.values())[0]
                    metadata = first_node.metadata
                else:
                    raise ValueError("No reference documents found")
            else:
                raise ValueError("Could not find documents in the index")
    except Exception as e:
        st.warning(f"Could not retrieve document metadata: {str(e)}")
        return
    
    # Display formatted metadata
    st.subheader("Document Information")
    
    # Title
    if metadata.get('title') and metadata['title'] not in ['None', 'null']:
        st.markdown(f"**Title:** {metadata['title']}")
    
    # Author
    if metadata.get('author') and metadata['author'] not in ['None', 'null']:
        st.markdown(f"**Author:** {metadata['author']}")
    
    # Keywords
    if metadata.get('keywords') and metadata['keywords'] not in ['None', 'null']:
        st.markdown(f"**Keywords:** {metadata['keywords']}")
    
    # Display summary if available
    if doc_id and doc_id in st.session_state.get('document_summaries', {}):
        st.markdown("### Summary")
        summary = st.session_state['document_summaries'][doc_id]
        st.markdown(f"{summary}")
        st.markdown("---")
    
    # Page count - get from the PDF path if available
    pdf_path = st.session_state.pdf_data[file_name].get('path')
    if pdf_path and os.path.exists(pdf_path):
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(pdf_path)
            st.markdown(f"**Page count:** {len(doc)}")
            doc.close()
        except Exception as e:
            st.warning(f"Could not determine page count: {str(e)}")
    
    # Table of Contents
    if metadata.get('toc_items') and metadata['toc_items'] not in ['None', 'null', '[]']:
        st.markdown("**Table of Contents:**")
        try:
            # Safely evaluate the toc_items string to get the actual data
            toc_items = ast.literal_eval(metadata['toc_items'])
            if isinstance(toc_items, list) and toc_items:
                for item in toc_items:
                    if isinstance(item, dict) and 'title' in item and 'page' in item:
                        st.markdown(f"- {item['title']} (Page {item['page']})")
        except Exception as e:
            # Fallback to displaying the raw string
            st.markdown(metadata['toc_items'])


def display_document_images(file_name):
    """Display all images extracted from the document."""
    if file_name not in st.session_state.pdf_data:
        st.warning("Document images not available")
        return
    
    # Get document ID
    doc_id = st.session_state.file_document_id.get(file_name)
    if not doc_id:
        st.warning("Document ID not found")
        return
    
    # Get image paths for this document
    image_paths = st.session_state.get('document_image_map', {}).get(doc_id, [])
    
    if not image_paths:
        st.info("No images found in this document")
        return
    
    st.subheader(f"Images from {file_name}")
    st.caption(f"Found {len(image_paths)} images")
    
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
                page_part = img_path.split('-')[-2]
                page_num = int(page_part) + 1  # Convert to 1-based page number
            except Exception:
                pass
            
            # Display image in the appropriate column
            with cols[i % 3]:
                st.image(img_path, caption=f"Page {page_num}")
                st.caption(f"Image {i+1} of {len(image_paths)}")
        else:
            with cols[i % 3]:
                st.warning(f"Image file not found: {os.path.basename(img_path)}")


def process_uploaded_file(uploaded_file, set_as_current=True, multi_upload=False):
    """Process an uploaded file and store it in session state.
    
    Args:
        uploaded_file: The file to process
        set_as_current: If True, set this file as the current file
        multi_upload: Whether this is part of a multi-file upload
    """
    if not uploaded_file:
        return
        
    # Initialize file queue tracking if not exists
    if 'file_queue' not in st.session_state:
        st.session_state.file_queue = []
    
    # Record this file upload interaction
    st.session_state.last_uploaded_file_name = uploaded_file.name
    st.session_state.last_upload_timestamp = str(int(time.time()))
    
    file_name = uploaded_file.name
    
    # Check if this file is already processed
    if uploaded_file.name not in st.session_state.processed_files:
        with st.spinner(f"Processing {file_name}..."):
            try:
                # Save uploaded file to temp location
                pdf_path = save_uploaded_file(uploaded_file)
                
                # Process the PDF
                vector_index, keyword_index, doc_id = process_pdf(pdf_path, uploaded_file.name)
                # Create query engine
                query_engine = create_query_engine(
                    vector_index,
                    keyword_index,
                    doc_id,
                    citation_mode=st.session_state.citation_mode
                )
                
                # Store data for reuse
                st.session_state.pdf_data[file_name] = {
                    'path': pdf_path,
                    'vector_index': vector_index,
                    'keyword_index': keyword_index,
                    'doc_id': doc_id,
                    'invalid': False
                }
                
                # Store binary data for reliable access
                with open(pdf_path, 'rb') as pdf_file:
                    st.session_state.pdf_binary_data[file_name] = pdf_file.read()
                
                # Store query engine
                st.session_state.query_engine[file_name] = query_engine
                
                # Initialize chat history for this file
                if file_name not in st.session_state.chat_history:
                    st.session_state.chat_history[file_name] = []
                
                # Store the name of the processed file for display on the next page load
                if "last_processed_files" not in st.session_state:
                    st.session_state["last_processed_files"] = []
                st.session_state["last_processed_files"].append(file_name)
                
                # Only set as current file if requested (or if it's the first file)
                if set_as_current or not st.session_state.get('current_file'):
                    st.session_state.current_file = file_name
                
                # Add file name to processed files set
                st.session_state.processed_files.add(uploaded_file.name)
                
                # Store the complete state before rerunning
                st.session_state.file_processed = True
                
                # Track processing time for this file
                if file_name in st.session_state.get('file_processing_status', {}):
                    st.session_state.file_processing_status[file_name]['processing_time'] = (
                        time.time() - st.session_state.file_processing_status[file_name].get('started_at', time.time())
                    )
                    st.session_state.file_processing_status[file_name]['status'] = 'completed'
                
                # For multi-uploads, store in a session var to show status after all files are processed
                if multi_upload:
                    if 'multi_upload_results' not in st.session_state:
                        st.session_state.multi_upload_results = {'success': [], 'failed': []}
                    st.session_state.multi_upload_results['success'].append(file_name)
                
                return True
            except Exception as e:
                # Use a different approach for error handling
                error_msg = str(e)
                st.session_state["display_errors"][file_name] = error_msg
                
                # Update processing status to show failure
                if file_name in st.session_state.get('file_processing_status', {}):
                    st.session_state.file_processing_status[file_name]['status'] = 'failed'
                    st.session_state.file_processing_status[file_name]['error'] = error_msg
                
                # For multi-uploads, track failures separately
                if multi_upload:
                    if 'multi_upload_results' not in st.session_state:
                        st.session_state.multi_upload_results = {'success': [], 'failed': []}
                    st.session_state.multi_upload_results['failed'].append({
                        'name': file_name,
                        'error': error_msg
                    })
                
                # Clean up the file if processing failed
                if 'pdf_path' in locals() and os.path.exists(pdf_path):
                    os.remove(pdf_path)
                return False
    else:
        # If file was already processed, only set as current if requested
        if set_as_current:
            st.session_state.current_file = file_name
        return True


def annotation_click_handler(annotation):
    """Handle clicks on source annotations in the PDF viewer."""
    # Log the click but don't take any action
    page = annotation.get('page', 'unknown')
    print(f"Annotation clicked on page {page}: {annotation}")
    # No further action required

def verify_stored_files():
    """Verify that all stored PDF files still exist and can be loaded."""
    if 'pdf_data' not in st.session_state or not st.session_state.pdf_data:
        return
        
    invalid_files = []
    
    # Check each file in the pdf_data
    for file_name, file_data in st.session_state.pdf_data.items():
        pdf_path = file_data.get('path')
        if not pdf_path or not os.path.exists(pdf_path):
            # If we have binary data for this file, we can still display it
            if file_name not in st.session_state.get('pdf_binary_data', {}):
                invalid_files.append(file_name)
    
    # Mark invalid files in the session state
    for file_name in invalid_files:
        if file_name in st.session_state.pdf_data:
            # Don't delete yet, we'll just mark files as invalid and let the user decide
            st.session_state.pdf_data[file_name]['invalid'] = True

def main():
    """Main application function."""
    # Set page configuration
    st.set_page_config(
        page_title="Chat with your PDF",
        page_icon="📚",
        layout="wide"
    )
    
    # Initialize session state and create directories
    initialize_session_state()
    create_empty_directories()
    # Migrate existing chat history to include page information (v2)
    if 'chat_history_migrated_v2' not in st.session_state:
        print("Migrating chat history to add citation page information (v2)")
        for file_name, messages in st.session_state.get('chat_history', {}).items():
            for i, msg in enumerate(messages):
                if msg["role"] == "assistant":
                    # Extract citation numbers if needed
                    if "citations" not in msg:
                        all_citation_numbers = extract_citation_indices(msg["content"])
                        msg["citations"] = sorted(list(set(all_citation_numbers)))
                    
                    # Add response_id if needed
                    if "response_id" not in msg:
                        msg["response_id"] = i
                    
                    # Add empty citation_pages dictionary if not present
                    if "citation_pages" not in msg:
                        msg["citation_pages"] = {}
                        
                    # Make sure document field is present for multi-document support
                    if "document" not in msg:
                        msg["document"] = file_name
        
        st.session_state.chat_history_migrated_v2 = True
    
    # Migration v3: Add document ID and improve citation page information
    if 'chat_history_migrated_v3' not in st.session_state:
        print("Migrating chat history to improve citation page information (v3)")
        for file_name, messages in st.session_state.get('chat_history', {}).items():
            for msg in messages:
                if msg["role"] == "assistant":
                    # Add document reference
                    if "document" not in msg:
                        msg["document"] = file_name
                    
                    # Ensure citation_pages is a dictionary
                    if "citation_pages" not in msg or not isinstance(msg["citation_pages"], dict):
                        msg["citation_pages"] = {}
                    
                    # Try to populate page information from document responses if available
                    if (file_name in st.session_state.get('document_responses', {}) and
                        'sources' in st.session_state.document_responses[file_name]):
                        
                        # Only process if we have citations but no page info
                        if msg.get("citations") and not msg["citation_pages"]:
                            print(f"Adding missing page info for message in {file_name}")
                            sources = st.session_state.document_responses[file_name]['sources']
                            
                            for citation_num in msg["citations"]:
                                idx = citation_num - 1  # Convert to 0-based index
                                if idx < len(sources):
                                    source = sources[idx]
                                    # Extract page number based on source type
                                    page_num = 0
                                    if hasattr(source, 'node'):
                                        page_num = source.node.metadata.get('page', 0)
                                    elif hasattr(source, 'metadata') and hasattr(source, 'text'):
                                        page_num = source.metadata.get('page', 0)
                                    
                                    # Convert to int if possible
                                    try:
                                        page_num = int(page_num)
                                        if page_num > 0:
                                            msg["citation_pages"][str(citation_num)] = page_num
                                    except (ValueError, TypeError):
                                        pass
        
        st.session_state.chat_history_migrated_v3 = True
        st.session_state.chat_history_migrated_v2 = True
    
    # Verify that all stored PDF files still exist
    verify_stored_files()
    
    # Initialize error state
    if "display_errors" not in st.session_state:
        st.session_state["display_errors"] = {}
    
    # Initialize LLM settings
    model_name = initialize_llm_settings()
    
    # Store PDF binary data in session state if not already there
    if 'pdf_binary_data' not in st.session_state:
        st.session_state.pdf_binary_data = {}
    
    # Application header and description
    st.title("Chat with your PDF")
    
    # Sidebar for document upload and settings
    with st.sidebar:
        st.header("Document Upload")
        
        # Define callback for file uploader
        def on_file_upload():
            # Try all possible file uploader keys to find the files
            uploaded_files = None
            current_key = f"file_uploader_{st.session_state.interaction_id}"
            
            # Check current session key first
            if current_key in st.session_state and st.session_state[current_key]:
                uploaded_files = st.session_state[current_key]
            
            # If no files found with current key, check previous keys
            if not uploaded_files:
                for key in st.session_state:
                    if key.startswith("file_uploader_") and st.session_state[key]:
                        uploaded_files = st.session_state[key]
                        break
            
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
                    process_uploaded_file(
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
        
        # Improved document navigation in the sidebar
        if st.session_state.pdf_data:
            st.header("Your Documents")
            
            # Display document count
            total_docs = len(st.session_state.pdf_data)
            st.caption(f"{total_docs} document{'s' if total_docs > 1 else ''} available")
            
            # Create a scrollable container for the document list with dynamic height
            sidebar_screen_height = streamlit_js_eval(js_expressions='screen.height', key='sidebar_height')
            sidebar_max_height = int(sidebar_screen_height * 0.4) if sidebar_screen_height else 400
            container_height = min(sidebar_max_height, 80 * total_docs)  # 80px per document, max dynamic height
            doc_list_container = st.container(height=container_height)
            
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
        
        st.header("Settings")
        # Model selection
        selected_model = st.selectbox(
            "Select Model",
            options=list(MODELS.keys()),
            index=list(MODELS.keys()).index(model_name)
        )
        
        if selected_model != st.session_state.model_name:
            st.session_state.model_name = selected_model
            # Reinitialize settings with new model
            model_name = initialize_llm_settings()
        
        # Citation mode toggle
        citation_mode = st.toggle(
            "Strict citation mode",
            value=st.session_state.get('citation_mode', True),
            help="When enabled, responses must include citations to source documents in [#] format."
        )
        
        if citation_mode != st.session_state.get('citation_mode', True):
            st.session_state.citation_mode = citation_mode
            # Clear any previous query engines to ensure they use the updated citation mode
            st.session_state.query_engine = {}
        
        # Clear chat button
        if st.button("Clear Chat"):
            # Reset chat history for current file
            if 'current_file' in st.session_state and st.session_state.current_file:
                current_file = st.session_state.current_file
                # Clear chat history
                if current_file in st.session_state.chat_history:
                    st.session_state.chat_history[current_file] = []
                # Clear document-specific response
                if current_file in st.session_state.document_responses:
                    del st.session_state.document_responses[current_file]
            # Clear global response if it exists (legacy support)
            if 'response' in st.session_state:
                st.session_state.response = None
    # Store a unique interaction ID for this session run
    if "interaction_id" not in st.session_state:
        st.session_state.interaction_id = 0
    else:
        st.session_state.interaction_id += 1
    
    # File upload is handled by the on_file_upload callback
    # This keeps the file in the uploader widget even after page reruns
    
    # Show multi-file upload progress if applicable
    if 'multi_upload_progress' in st.session_state:
        progress = st.session_state.multi_upload_progress
        total = progress['total']
        processed = progress['processed']
        elapsed_time = time.time() - progress['started_at']
        
        if processed < total:
            # Show a progress bar for multi-file uploads
            progress_percentage = processed / total
            
            # Show status message
            st.info(f"Processing multiple files: {processed}/{total} completed ({progress_percentage:.0%}) - {elapsed_time:.1f}s elapsed")
        else:
            # All files processed, show detailed results
            if 'multi_upload_results' in st.session_state:
                results = st.session_state.multi_upload_results
                success_count = len(results.get('success', []))
                failed_count = len(results.get('failed', []))
                
                # Display an appropriate message based on results
                if failed_count == 0:
                    st.success(f"Successfully processed all {total} files in {elapsed_time:.1f}s")
                else:
                    st.warning(f"Processed {total} files in {elapsed_time:.1f}s. Success: {success_count}, Failed: {failed_count}")
                    
                    # If there were failures, show details in an expander
                    if failed_count > 0:
                        with st.expander(f"Show {failed_count} failed file details"):
                            for failure in results['failed']:
                                st.error(f"❌ {failure['name']}: {failure['error']}")
                
                # Clean up the results after showing them
                del st.session_state.multi_upload_results
            else:
                # Fallback if results not available
                st.success(f"Finished processing {total} files in {elapsed_time:.1f}s")
            
            # Keep the multi-upload progress for one render only
            del st.session_state.multi_upload_progress
    
    # Display success message if file was recently processed successfully (single file case)
    elif "last_processed_file" in st.session_state:
        file_name = st.session_state["last_processed_file"]
        st.success(f"Successfully processed {file_name}")
        # Keep the message only for one render
        del st.session_state["last_processed_file"]
    
    # Only show processing errors for the current session
    if st.session_state.get("display_errors") and len(st.session_state["display_errors"]) > 0:
        # Only show the most recent error
        recent_error = list(st.session_state["display_errors"].items())[-1]
        file_name, error_msg = recent_error
        st.error(f"Error processing {file_name}: {error_msg}")
        # Clear errors after showing them once
        st.session_state["display_errors"] = {}
    
    # Display document and chat interface if a document is loaded
    if 'current_file' in st.session_state and st.session_state.current_file and st.session_state.current_file in st.session_state.pdf_data:
        current_file = st.session_state.current_file
        
        # Display document information with total number of documents
        total_docs = len(st.session_state.pdf_data)
        doc_position = list(st.session_state.pdf_data.keys()).index(current_file) + 1
        st.subheader(f"You're now chatting with: {current_file} ({doc_position}/{total_docs})")
        
        # Split the display into two columns - one for PDF and one for content tabs
        pdf_column, content_column = st.columns([50, 50], gap="medium")
        
        # Display PDF in the left column
        with pdf_column:
            if 'pdf_data' in st.session_state and current_file in st.session_state.pdf_data:
                # Get the PDF binary data for the viewer
                pdf_path = st.session_state.pdf_data[current_file]['path']
                
                # Check if we have the binary data in session state
                if current_file in st.session_state.pdf_binary_data:
                    try:
                        # Use the stored binary data
                        pdf_binary = st.session_state.pdf_binary_data[current_file]
                        
                        # Create annotations if we have a response with sources for this specific document
                        annotations = []
                        # Check if we have a document-specific response
                        if (current_file in st.session_state.document_responses and
                            st.session_state.document_responses[current_file] and
                            'sources' in st.session_state.document_responses[current_file]):
                            
                            # Import the function to create annotations from sources
                            from src.source import create_annotations_from_sources
                            
                            # Create annotations based on the document-specific response
                            doc_response = st.session_state.document_responses[current_file]
                            annotations = create_annotations_from_sources(
                                doc_response['answer'],
                                doc_response['sources']
                            )
                        
                        # Display the PDF with the viewer using dynamic height
                        screen_height = streamlit_js_eval(js_expressions='screen.height', key='pdf_screen_height')
                        pdf_height = int(screen_height * 0.7) if screen_height else 800
                        pdf_viewer(
                            input=pdf_binary,
                            annotations=annotations,
                            annotation_outline_size=5,  # Make outlines more visible
                            height=pdf_height,
                            on_annotation_click=annotation_click_handler
                            # All automatic scrolling parameters removed
                        )
                    except Exception as e:
                        st.error(f"Error displaying PDF: {str(e)}")
                # Check if the file exists on disk
                elif os.path.exists(pdf_path):
                    try:
                        # Load the PDF binary data and store it for future use
                        with open(pdf_path, 'rb') as file:
                            pdf_binary = file.read()
                            st.session_state.pdf_binary_data[current_file] = pdf_binary
                        
                        # Create annotations if we have a response with sources for this specific document
                        annotations = []
                        # Check if we have a document-specific response
                        if (current_file in st.session_state.document_responses and
                            st.session_state.document_responses[current_file] and
                            'sources' in st.session_state.document_responses[current_file]):
                            
                            # Import the function to create annotations from sources
                            from src.source import create_annotations_from_sources
                            
                            # Create annotations based on the document-specific response
                            doc_response = st.session_state.document_responses[current_file]
                            annotations = create_annotations_from_sources(
                                doc_response['answer'],
                                doc_response['sources']
                            )
                        
                        # Display the PDF with the viewer using dynamic height
                        screen_height = streamlit_js_eval(js_expressions='screen.height', key='pdf_screen_height2')
                        pdf_height = int(screen_height * 0.7) if screen_height else 800
                        pdf_viewer(
                            input=pdf_binary,
                            annotations=annotations,
                            annotation_outline_size=5,  # Make outlines more visible
                            height=pdf_height,
                            on_annotation_click=annotation_click_handler
                            # All automatic scrolling parameters removed
                        )
                    except Exception as e:
                        st.error(f"Error loading PDF: {str(e)}")
                # File not found - show error message
                else:
                    st.error(f"Could not find PDF file at {pdf_path}. The file may have been moved or deleted.")

        # Create a scrollable container for the chat history with dynamic height
        screen_height = streamlit_js_eval(js_expressions='screen.height', key='screen_height')
        main_container_dimensions = st_dimensions(key="main")
        height_column_container = int(screen_height * 0.5) if main_container_dimensions else 400
        
        # Tabbed content in the right column
        with content_column:
            # Create tabs
            chat_tab, info_tab, images_tab = st.tabs(["Chat", "Document Info", "Images"])
            
            # Chat tab - contains the existing chat interface
            with chat_tab:

                chat_container = st.container(height=height_column_container)
                
                # Display chat history
                with chat_container:
                    if current_file in st.session_state.chat_history:
                        for msg_idx, msg in enumerate(st.session_state.chat_history[current_file]):
                            with st.chat_message(msg["role"]):
                                st.markdown(msg["content"])
                                
                                # Display sources if this is an assistant message
                                if msg["role"] == "assistant":
                                    # Check if this message is for the current document before showing citation buttons
                                    is_for_current_document = msg.get("document", current_file) == current_file
                                    
                                    # Display citation buttons for all messages (including the latest one)
                                    if msg.get("citations") and is_for_current_document:
                                        citation_numbers = msg.get("citations", [])
                                        # Citation buttons and jumping functionality removed
                                        # We keep the citation_numbers for displaying source information
                                    
                                    if msg.get("sources"):
                                        # Add a heading for Sources before the expander
                                        with st.expander("Show Sources"):
                                            # Get citation numbers for this message
                                            citation_numbers = msg.get("citations", [])
                                            
                                            if citation_numbers:
                                                # Only display sources that are actually cited in the response
                                                displayed_sources = set()
                                                
                                                for citation_num in sorted(citation_numbers):
                                                    source_index = citation_num - 1  # Convert 1-based citation to 0-based index
                                                    
                                                    if source_index in displayed_sources:
                                                        continue  # Skip if already displayed this source
                                                    
                                                    if source_index < len(msg["sources"]):
                                                        source_text = msg["sources"][source_index]
                                                        st.write(source_text)
                                                        displayed_sources.add(source_index)
                                                        
                                                        # Add separator between sources
                                                        if len(displayed_sources) < len(citation_numbers):
                                                            st.markdown("---")
                                            else:
                                                # Fallback: If no citations found, show all sources
                                                for i, source_text in enumerate(msg["sources"]):
                                                    st.write(source_text)
                                                    if i < len(msg["sources"]) - 1:
                                                        st.markdown("---")
                                
                                    # Display images if available
                                    if msg.get("images"):
                                        with st.expander("📊 **Related Images:**"):

                                            images_list = msg.get("images", [])
                                            
                                            for i, img_info in enumerate(images_list):
                                                try:
                                                    print("Image info", img_info)
                                                    # Extract path and caption
                                                    if isinstance(img_info, dict) and 'path' in img_info:
                                                        img_path = img_info['path']
                                                        img_caption = img_info.get('caption', f"Document Image {i+1}")
                                                        
                                                        # Try different path options in order of likelihood
                                                        image_displayed = False

                                                        try:
                                                            st.image(img_path, caption=img_caption)
                                                            image_displayed = True
                                                        except Exception as e:
                                                            image_displayed = False
                                                        
                                                        # Show warning if image couldn't be displayed
                                                        if not image_displayed:
                                                            st.warning(f"Could not display image {i+1}")
                                                except Exception as e:
                                                    st.warning(f"Error displaying image: {str(e)}")

                # Display query suggestions as pills if available
                current_doc_id = st.session_state.pdf_data[current_file]['doc_id']
                if (
                    'document_query_suggestions' in st.session_state and
                    current_doc_id in st.session_state['document_query_suggestions'] and
                    st.session_state['document_query_suggestions'][current_doc_id]
                ):
                    # Get suggestions for this document
                    suggestions = st.session_state['document_query_suggestions'][current_doc_id]
                    
                    if suggestions:
                        # Display suggestions as pills
                        selected_suggestion = st.pills(
                            label="",
                            options=suggestions,
                            selection_mode="single"
                        )
                        
                        # If a suggestion is selected
                        if selected_suggestion:
                            # Use the selected suggestion as the prompt
                            prompt = selected_suggestion
                            
                            # Remove the selected suggestion from the list
                            suggestions.remove(selected_suggestion)
                            st.session_state['document_query_suggestions'][current_doc_id] = suggestions
                            
                            # Add to chat history and process like a normal query
                            if current_file not in st.session_state.chat_history:
                                st.session_state.chat_history[current_file] = []
                            
                            # Add user message to chat history
                            st.session_state.chat_history[current_file].append({
                                "role": "user",
                                "content": prompt
                            })
                            
                            # Show thinking message in the chat container
                            with chat_container:
                                with st.chat_message("user"):
                                    st.markdown(prompt)
                                with st.status("Thinking...", expanded=True) as status:
                                    with st.chat_message("assistant"):
                                        try:
                                            # Process the query with the current settings
                                            response_data = process_query(
                                                prompt=prompt,
                                                file_name=current_file,
                                                citation_mode=st.session_state.citation_mode
                                            )
                                            # Mark as complete
                                            status.update(label="Done!", state="complete", expanded=False)
                                            
                                            # Store response for later use
                                            st.session_state.document_responses[current_file] = response_data
                                            st.session_state.current_response_file = current_file
                                            st.session_state.response = response_data
                                            
                                            # Extract citation numbers from the response
                                            all_citation_numbers = extract_citation_indices(response_data['answer'])
                                            unique_citation_numbers = set(all_citation_numbers)
                                            
                                            # Store citation numbers for persistence
                                            st.session_state.current_response_citations = sorted(list(unique_citation_numbers))
                                            st.session_state.current_response_id = len(st.session_state.chat_history.get(current_file, []))
                                            
                                            # Extract and store page numbers for each citation
                                            citation_page_map = {}
                                            for idx in sorted(list(unique_citation_numbers)):
                                                if idx <= len(response_data['sources']):
                                                    source = response_data['sources'][idx-1]
                                                    # Extract page number based on source type
                                                    page_num = 0
                                                    if hasattr(source, 'node'):
                                                        page_num = source.node.metadata.get('page', 0)
                                                    elif hasattr(source, 'metadata') and hasattr(source, 'text'):
                                                        page_num = source.metadata.get('page', 0)
                                                    
                                                    # Convert to int if possible
                                                    try:
                                                        page_num = int(page_num)
                                                    except (ValueError, TypeError):
                                                        page_num = 0
                                                    
                                                    citation_page_map[str(idx)] = page_num
                                            
                                            # Store page map in session state
                                            st.session_state.current_citation_pages = citation_page_map
                                            
                                            # Prepare source information
                                            sources = []
                                            images = []
                                            
                                            # Format source information if available
                                            if 'sources' in response_data and response_data['sources']:
                                                # Extract citation numbers from the response
                                                all_citation_numbers = extract_citation_indices(response_data['answer'])
                                                unique_citation_numbers = sorted(list(set(all_citation_numbers)))
                                                
                                                # Only format sources that are actually cited in the response
                                                for citation_num in unique_citation_numbers:
                                                    source_index = citation_num - 1  # Convert 1-based citation to 0-based index
                                                    if source_index < len(response_data['sources']):
                                                        source = response_data['sources'][source_index]
                                                        markdown, source_text = format_source_for_display(source, citation_num)
                                                        sources.append(markdown)
                                            
                                            # Handle images if available
                                            if 'images' in response_data and response_data['images']:
                                                images = response_data['images']
                                            
                                            # Create chat message with processed data
                                            chat_message = {
                                                "role": "assistant",
                                                "content": response_data['answer'],
                                                "sources": sources,
                                                "images": [{
                                                    "path": img['path'],
                                                    "caption": img.get('caption', "Document Image")
                                                } for img in images],
                                                "citations": st.session_state.current_response_citations,
                                                "citation_pages": st.session_state.current_citation_pages,
                                                "response_id": st.session_state.current_response_id,
                                                "document": current_file
                                            }
                                            
                                            # Add to chat history
                                            st.session_state.chat_history[current_file].append(chat_message)
                                            
                                        except Exception as e:
                                            print(f"Error processing suggestion: {str(e)}")
                                            # Add error message to chat
                                            st.session_state.chat_history[current_file].append({
                                                "role": "assistant",
                                                "content": f"I encountered an error while processing your query: {str(e)}"
                                            })
                            
                            # Force a page rerun to update the UI
                            st.rerun()
                
                # Query input (within the chat tab)
                prompt = st.chat_input("Ask a question about your document...")
                if prompt:
                    # Add user message to chat history
                    if current_file not in st.session_state.chat_history:
                        st.session_state.chat_history[current_file] = []
                    
                    st.session_state.chat_history[current_file].append({
                        "role": "user",
                        "content": prompt
                    })
                    
                    # Display user message in the container
                    with chat_container:
                        with st.chat_message("user"):
                            st.markdown(prompt)
                    
                        # Process query
                        with st.spinner("Thinking..."):
                            try:
                                response_data = process_query(
                                    prompt=prompt, 
                                    file_name=current_file, 
                                    citation_mode=st.session_state.citation_mode
                                )
                                # Store response for later use - document specific
                                st.session_state.document_responses[current_file] = response_data
                                st.session_state.current_response_file = current_file
                                st.session_state.response = response_data
                                
                                # Display assistant response in the container
                                with chat_container:
                                    with st.chat_message("assistant"):
                                        st.markdown(response_data['answer'])
                                        
                                        # Extract citation numbers from the response
                                        all_citation_numbers = extract_citation_indices(response_data['answer'])
                                        # Use a set to remove duplicates
                                        unique_citation_numbers = set(all_citation_numbers)
                                        
                                        # Store citation numbers in session state for persistence
                                        st.session_state.current_response_citations = sorted(list(unique_citation_numbers))
                                        st.session_state.current_response_id = len(st.session_state.chat_history.get(current_file, []))
                                        
                                        # Extract and store page numbers for each citation
                                        citation_page_map = {}
                                        for idx in sorted(list(unique_citation_numbers)):
                                            if idx <= len(response_data['sources']):
                                                source = response_data['sources'][idx-1]
                                                # Extract page number based on source type
                                                page_num = 0
                                                if hasattr(source, 'node'):
                                                    page_num = source.node.metadata.get('page', 0)
                                                elif hasattr(source, 'metadata') and hasattr(source, 'text'):
                                                    page_num = source.metadata.get('page', 0)
                                                
                                                # Convert to int if possible
                                                try:
                                                    page_num = int(page_num)
                                                except (ValueError, TypeError):
                                                    page_num = 0
                                                
                                                citation_page_map[str(idx)] = page_num  # Use string keys for JSON compatibility
                                        
                                        # Store page map in session state
                                        st.session_state.current_citation_pages = citation_page_map
                                        
                                        # Log citation info for debugging
                                        print(f"Storing {len(unique_citation_numbers)} unique citations in session state")
                                        print(f"Original citations: {all_citation_numbers}")
                                        print(f"Unique citations: {unique_citation_numbers}")
                                        print(f"Citation page map: {citation_page_map}")
                                        
                                        # No citation buttons needed here - they will be rendered as part of the chat history
                                        # after the rerun and persistent session state data
                                        
                                        # Prepare source information for storage
                                        sources = []
                                        images = []
                                        
                                        # Format and display source information if available
                                        if 'sources' in response_data and response_data['sources']:
                                            # Use the citation numbers we already extracted and stored in session state
                                            citation_numbers = st.session_state.current_response_citations
                                            
                                            if citation_numbers:
                                                # Display only the sources that are actually cited in the response
                                                displayed_sources = set()
                                                
                                                # Create the source information expander (no auto-expansion)
                                                with st.expander("Source Information", expanded=False):
                                                    
                                                    for citation_num in sorted(citation_numbers):
                                                        source_index = citation_num - 1  # Convert 1-based citation to 0-based index
                                        
                                                        try:
                                                            if source_index in displayed_sources:
                                                                continue  # Skip if already displayed this source
                                                            
                                                            if source_index < len(response_data['sources']):
                                                                source = response_data['sources'][source_index]
                                                                
                                                                # Display source header (no navigation column/button)
                                                                st.markdown(f"### Source [{citation_num}]")
                                                                
                                                                # Format the source for display
                                                                markdown, source_text = format_source_for_display(source, citation_num)
                                                                
                                                                # Display the markdown directly without splitting
                                                                # This works with our simplified format that only bolds the source and page
                                                                st.write(markdown)
                                                                
                                                                # Add to tracking set and sources list for history
                                                                displayed_sources.add(source_index)
                                                                sources.append(markdown)
                                                                
                                                                # Add horizontal rule between sources
                                                                if citation_num != sorted(citation_numbers)[-1]:
                                                                    st.markdown("---")
                                                        except IndexError:
                                                            st.warning(f"Citation [{citation_num}] does not match any available source.")
                                                
                                                if 'images' in response_data and response_data['images']:
                                                    images = response_data['images']
                                                    print("Images", images)
                                                    with st.expander("📊 **Related Images:**"):
                                                        for img in images:
                                                            st.image(img['path'], caption=img['caption'])


                                            else:
                                                with st.expander("Source Information"):
                                                    st.info("No source citations were found in this response.")
                                
                                # Create chat message with processed images and citation information
                                chat_message = {
                                    "role": "assistant",
                                    "content": response_data['answer'],
                                    "sources": sources,
                                    "images": [{
                                        "path": img['path'],
                                        "caption": img.get('caption', "Document Image")
                                    } for img in images],
                                    # Add citation information for hybrid navigation
                                    "citations": st.session_state.current_response_citations,
                                    "citation_pages": st.session_state.current_citation_pages,
                                    "response_id": st.session_state.current_response_id,
                                    "document": current_file  # Store document name for multi-document support
                                }
                                
                                # Add to chat history
                                st.session_state.chat_history[current_file].append(chat_message)
                                
                                # Force page rerun to refresh PDF viewer with annotations
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error processing your query: {str(e)}")
                                st.session_state.chat_history[current_file].append({
                                    "role": "assistant",
                                    "content": f"I encountered an error while processing your query: {str(e)}"
                                })
            
            # Document Info tab - displays document metadata
            with info_tab:
                display_document_info(current_file)
                
            # Images tab - displays all document images
            with images_tab:
                display_document_images(current_file)
    else:
        # Check if we have documents but none is selected
        if st.session_state.pdf_data:
            # Auto-select the first document if none is selected
            if not st.session_state.get('current_file') or st.session_state.current_file not in st.session_state.pdf_data:
                first_doc = list(st.session_state.pdf_data.keys())[0]
                st.session_state.current_file = first_doc
                st.rerun()
            else:
                st.info("👈 Select a document from the sidebar to view it here")
        else:
            # No documents loaded yet
            st.info("👈 Please upload a PDF document to start chatting")


if __name__ == "__main__":
    main()
