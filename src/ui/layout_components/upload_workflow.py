"""
Upload workflow component following the transcription app pattern.
Handles the complete upload process without infinite loops.
"""

import time
import streamlit as st
from typing import List, Any, Optional

from ...core.upload_manager import get_upload_manager
from ...utils.logger import Logger


def render_upload_workflow() -> None:
    """Render the upload workflow (like transcription workflow)."""
    upload_manager = get_upload_manager()
    
    # Initialize session state for upload workflow
    if 'upload_workflow_initialized' not in st.session_state:
        st.session_state.upload_workflow_initialized = True
        st.session_state.upload_files = None
        st.session_state.upload_operation_id = None
        st.session_state.upload_status = None
        st.session_state.upload_result = None
        st.session_state.upload_error = None
        st.session_state.upload_processing = False
    
    # File uploader section
    st.header("📤 Upload Documents")
    st.markdown("Upload your documents to create a new knowledge base and chat assistant.")
    
    # Show upload form only if not currently processing
    if not st.session_state.upload_processing:
        uploaded_files = st.file_uploader(
            "Choose files to upload",
            type=['pdf', 'txt', 'docx', 'md'],
            accept_multiple_files=True,
            help="Supported formats: PDF, TXT, DOCX, MD. Maximum size: 50MB per file.",
            key='upload_files_input'
        )
        
        if uploaded_files:
            # Store files in session state
            st.session_state.upload_files = uploaded_files
            
            # Show file preview
            st.subheader("📁 Selected Files")
            
            total_size = sum(file.size for file in uploaded_files)
            total_size_mb = total_size / (1024 * 1024)
            
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**{len(uploaded_files)} files selected**")
            with col2:
                st.write(f"**Total: {total_size_mb:.1f} MB**")
            
            # Validate files
            valid_files, errors = upload_manager.validate_files(uploaded_files)
            
            # Show validation errors
            if errors:
                st.error("❌ **Validation Errors:**")
                for error in errors:
                    st.error(error)
            
            # Show valid files and dataset selection
            if valid_files:
                st.success(f"✅ **{len(valid_files)} files ready for upload**")
                
                # Dataset selection
                st.subheader("🗂️ Dataset Selection")
                
                dataset_option = st.radio(
                    "Choose how to organize your documents:",
                    ["Create New Dataset", "Add to Existing Dataset"],
                    help="Datasets group related documents together. Each dataset gets its own chat assistant."
                )
                
                dataset_id = None
                dataset_name = None
                dataset_description = ""
                
                if dataset_option == "Create New Dataset":
                    dataset_name = st.text_input(
                        "Dataset Name *",
                        placeholder="e.g., Research Papers, Company Documents, etc.",
                        help="Choose a descriptive name for your document collection"
                    )
                    
                    dataset_description = st.text_area(
                        "Description (optional)",
                        placeholder="Describe what these documents contain...",
                        height=80
                    )
                
                else:
                    # Existing dataset selection
                    user_datasets = upload_manager.get_user_datasets()
                    
                    if user_datasets:
                        dataset_options = []
                        dataset_ids = []
                        
                        for dataset in user_datasets:
                            name = dataset.get('name', 'Unnamed Dataset')
                            dataset_options.append(name)
                            dataset_ids.append(dataset.get('id'))
                        
                        selected_dataset_idx = st.selectbox(
                            "Select Dataset",
                            range(len(dataset_options)),
                            format_func=lambda x: dataset_options[x],
                            help="Choose an existing dataset to add your documents to"
                        )
                        
                        if selected_dataset_idx is not None:
                            dataset_id = dataset_ids[selected_dataset_idx]
                            dataset_name = dataset_options[selected_dataset_idx]
                            
                            st.info(f"📚 Adding to: **{dataset_name}**")
                    
                    else:
                        st.warning("No existing datasets found. Please create a new dataset.")
                        return
                
                # Upload button (like transcribe button)
                can_upload = (
                    valid_files and 
                    (dataset_option == "Add to Existing Dataset" and dataset_id) or
                    (dataset_option == "Create New Dataset" and dataset_name and dataset_name.strip())
                )
                
                if can_upload:
                    if st.button("📤 Start Upload", type="primary", use_container_width=True):
                        # Start upload operation (like transcription start)
                        st.session_state.upload_processing = True
                        
                        operation_id = upload_manager.start_upload_operation(
                            files=valid_files,
                            dataset_option="new" if dataset_option == "Create New Dataset" else "existing",
                            dataset_id=dataset_id,
                            dataset_name=dataset_name,
                            dataset_description=dataset_description
                        )
                        
                        st.session_state.upload_operation_id = operation_id
                        st.session_state.upload_status = "PENDING"
                        
                        Logger.info(f"Started upload operation {operation_id}")
                        st.rerun()  # Only rerun when starting upload
                
                elif dataset_option == "Create New Dataset" and not (dataset_name and dataset_name.strip()):
                    st.warning("⚠️ Please enter a dataset name to continue.")
    
    else:
        # Show current upload info (like transcription info)
        if st.session_state.upload_files:
            st.write(f"**Uploading:** {len(st.session_state.upload_files)} files")
            if st.button("🗑️ Cancel Upload"):
                _reset_upload_state()
                st.rerun()


def render_upload_status() -> None:
    """Render upload status (like transcription status display)."""
    upload_manager = get_upload_manager()
    
    # Check if we have an active upload operation
    if (st.session_state.upload_processing and 
        st.session_state.upload_operation_id and 
        st.session_state.upload_status not in ["SUCCESS", "FAILURE"]):
        
        st.info("🔄 Upload is in progress. Please wait...")
        
        operation_id = st.session_state.upload_operation_id
        
        # Store start time in session state to persist across renders
        if 'upload_start_time' not in st.session_state:
            st.session_state.upload_start_time = time.time()
        
        start_time = st.session_state.upload_start_time
        status_placeholder = st.empty()
        
        # Process the operation (like transcription status check)
        while True:
            # Check operation status
            operation = upload_manager.get_operation_status(operation_id)
            
            if not operation:
                st.session_state.upload_status = "FAILURE"
                st.session_state.upload_error = "Operation not found"
                break
            
            elapsed_time = time.time() - start_time
            minutes, seconds = divmod(elapsed_time, 60)
            
            status = operation.get('status')
            stage = operation.get('stage', 'unknown')
            progress = operation.get('progress', 0)
            
            if status == "completed":
                st.session_state.upload_status = "SUCCESS"
                st.session_state.upload_result = operation
                
                # Check if operation has any failures to report
                files = operation.get('files', [])
                failed_files = [f for f in files if f.get('status') == 'failed']
                successful_files = [f for f in files if f.get('status') != 'failed']
                
                if failed_files and successful_files:
                    # Partial success
                    st.warning(f"⚠️ Upload completed with some issues:")
                    st.success(f"✅ {len(successful_files)} files processed successfully")
                    st.error(f"❌ {len(failed_files)} files failed:")
                    for failed_file in failed_files:
                        st.error(f"  • {failed_file.get('name', 'Unknown')}: {failed_file.get('error', 'Unknown error')}")
                    st.info(f"🤖 Assistant created with {len(successful_files)} documents")
                elif failed_files:
                    # All failed
                    st.error(f"❌ Upload failed - all {len(failed_files)} files failed processing")
                    for failed_file in failed_files:
                        st.error(f"  • {failed_file.get('name', 'Unknown')}: {failed_file.get('error', 'Unknown error')}")
                else:
                    # All success
                    st.success("✅ Upload completed! All documents processed successfully.")
                    st.info(f"🤖 Assistant '{operation.get('assistant_name')}' created and ready to use!")
                
                # Trigger assistant list refresh
                if 'ragflow_assistants_cache' in st.session_state:
                    del st.session_state.ragflow_assistants_cache
                if 'available_ragflow_assistants' in st.session_state:
                    del st.session_state.available_ragflow_assistants
                
                Logger.info(f"Upload operation {operation_id} completed")
                time.sleep(2)
                st.rerun()
                
            elif status == "failed":
                st.session_state.upload_status = "FAILURE"
                st.session_state.upload_error = operation.get('error_message', 'Unknown error')
                st.error(f"❌ Upload operation failed: {st.session_state.upload_error}")
                break
                
            else:
                # Still processing - check individual document statuses
                dataset_id = operation.get('dataset_id')
                if dataset_id:
                    # Get detailed status of all documents
                    dataset_status = upload_manager.client.check_dataset_processing_status(dataset_id)
                    if dataset_status.get('code') == 0:
                        status_data = dataset_status.get('data', {})
                        processed_docs = status_data.get('processed_docs', 0)
                        failed_docs = status_data.get('failed_docs', 0)
                        processing_docs = status_data.get('processing_docs', 0)
                        total_docs = status_data.get('total_docs', 0)
                        
                        # Show detailed status
                        if failed_docs > 0:
                            st.warning(f"⚠️ Processing status: {processed_docs} completed, {failed_docs} failed, {processing_docs} still processing")
                        
                        # If all documents are done (either success or failure), complete the operation
                        if processing_docs == 0 and total_docs > 0:
                            if processed_docs > 0:
                                # Some succeeded - try to create assistant
                                Logger.info(f"Some documents processed successfully, attempting assistant creation")
                                upload_manager.process_upload_operation(operation_id)
                                st.rerun()
                            else:
                                # All failed
                                st.session_state.upload_status = "FAILURE"
                                st.session_state.upload_error = f"All {total_docs} documents failed to process"
                                st.error(f"❌ All documents failed to process")
                                break
                
                # Process one step of the operation
                upload_manager.process_upload_operation(operation_id)
                
                status_placeholder.info(
                    f"📋 Status: {str(status).title()} ({str(stage).title()}). "
                    f"Progress: {progress}%. "
                    f"Elapsed: {int(minutes)} min {int(seconds)} sec. "
                    f"Checking again in 5 seconds..."
                )
                time.sleep(5)
                st.rerun()
    
    # Reset processing flag when done
    st.session_state.upload_processing = False


def _reset_upload_state():
    """Reset upload state (like reset transcription)."""
    st.session_state.upload_files = None
    st.session_state.upload_operation_id = None
    st.session_state.upload_status = None
    st.session_state.upload_result = None
    st.session_state.upload_error = None
    st.session_state.upload_processing = False
    st.session_state.upload_start_time = None
    
    # Clear any active operations from session state
    if 'upload_operations' in st.session_state:
        st.session_state.upload_operations = {}


def render_upload_interface() -> None:
    """Main upload interface combining workflow and status."""
    render_upload_workflow()
    render_upload_status()