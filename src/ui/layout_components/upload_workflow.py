"""
Upload workflow component following the transcription app pattern.
Handles the complete upload process without infinite loops.
"""

import time
import streamlit as st

from ...core.upload_manager import get_upload_manager
from ...utils.logger import Logger
from ...utils.i18n import I18n
from ...config import MAX_FILE_SIZE_MB


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
        st.session_state.upload_widget_key = 0  # For resetting file uploader
    
    # File uploader section
    st.header(f"📤 {I18n.t('upload_documents')}")
    st.markdown(I18n.t('upload_documents_description'))
    
    # Show upload form only if not currently processing
    if not st.session_state.upload_processing:
        uploaded_files = st.file_uploader(
            I18n.t('choose_files_to_upload'),
            type=['pdf'],
            accept_multiple_files=True,
            help=I18n.t('supported_formats_help', max_size=MAX_FILE_SIZE_MB),
            key=f'upload_files_input_{st.session_state.upload_widget_key}'
        )
        
        if uploaded_files:
            # Store files in session state
            st.session_state.upload_files = uploaded_files
            
            # Show file preview
            st.subheader(f"📁 {I18n.t('selected_files')}")
            
            total_size = sum(file.size for file in uploaded_files)
            total_size_mb = total_size / (1024 * 1024)
            
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**{len(uploaded_files)} {I18n.t('files_selected')}**")
            with col2:
                st.write(f"**{I18n.t('total')}: {total_size_mb:.1f} MB**")
            
            # Validate files
            valid_files, errors = upload_manager.validate_files(uploaded_files)
            
            # Show validation errors
            if errors:
                st.error(f"❌ **{I18n.t('validation_errors')}:**")
                for error in errors:
                    st.error(error)
            
            # Show valid files and dataset selection
            if valid_files:
                st.success(f"✅ **{len(valid_files)} {I18n.t('files_ready_for_upload')}**")
                
                # Dataset selection
                st.subheader(f"🗂️ {I18n.t('dataset_selection')}")
                
                dataset_option = st.radio(
                    I18n.t('choose_organization_method'),
                    [I18n.t('create_new_dataset'), I18n.t('add_to_existing_dataset')],
                    help=I18n.t('dataset_organization_help')
                )
                
                dataset_id = None
                dataset_name = None
                dataset_description = ""
                
                if dataset_option == I18n.t('create_new_dataset'):
                    dataset_name = st.text_input(
                        I18n.t('dataset_name_required'),
                        placeholder=I18n.t('dataset_name_placeholder'),
                        help=I18n.t('dataset_name_help')
                    )
                    
                    dataset_description = st.text_area(
                        I18n.t('description_optional'),
                        placeholder=I18n.t('description_placeholder'),
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
                            I18n.t('select_dataset'),
                            range(len(dataset_options)),
                            format_func=lambda x: dataset_options[x],
                            help=I18n.t('select_existing_dataset_help')
                        )
                        
                        if selected_dataset_idx is not None:
                            dataset_id = dataset_ids[selected_dataset_idx]
                            dataset_name = dataset_options[selected_dataset_idx]
                            
                            st.info(f"📚 {I18n.t('adding_to_dataset', dataset_name=dataset_name)}")
                    
                    else:
                        st.warning(I18n.t('no_existing_datasets'))
                        return
                
                # Upload button (like transcribe button)
                can_upload = (
                    valid_files and
                    (dataset_option == I18n.t('add_to_existing_dataset') and dataset_id) or
                    (dataset_option == I18n.t('create_new_dataset') and dataset_name and dataset_name.strip())
                )
                
                if can_upload:
                    if st.button(f"📤 {I18n.t('start_upload')}", type="primary", use_container_width=True):
                        # Start upload operation (like transcription start)
                        st.session_state.upload_processing = True
                        
                        operation_id = upload_manager.start_upload_operation(
                            files=valid_files,
                            dataset_option="new" if dataset_option == I18n.t('create_new_dataset') else "existing",
                            dataset_id=dataset_id,
                            dataset_name=dataset_name,
                            dataset_description=dataset_description
                        )
                        
                        st.session_state.upload_operation_id = operation_id
                        st.session_state.upload_status = "PENDING"
                        st.session_state.upload_start_time = time.time()  # Set start time for this operation
                        
                        Logger.info(f"Started upload operation {operation_id}")
                        st.rerun()  # Only rerun when starting upload
                
                elif dataset_option == I18n.t('create_new_dataset') and not (dataset_name and dataset_name.strip()):
                    st.warning(f"⚠️ {I18n.t('enter_dataset_name_warning')}")
    
    elif st.session_state.upload_processing:
        # Show current upload info only when actively processing
        if st.session_state.upload_files:
            st.write(f"**{I18n.t('uploading_files', count=len(st.session_state.upload_files))}**")
            if st.button(f"🗑️ {I18n.t('cancel_upload')}"):
                _reset_upload_state()
                st.rerun()


def render_upload_status() -> None:
    """Render upload status (like transcription status display)."""
    upload_manager = get_upload_manager()
    
    # Check if we have an active upload operation
    if (st.session_state.upload_processing and 
        st.session_state.upload_operation_id and 
        st.session_state.upload_status not in ["SUCCESS", "FAILURE"]):
        
        st.info(f"🔄 {I18n.t('upload_in_progress')}")
        
        operation_id = st.session_state.upload_operation_id
        
        # Get start time for this operation (set when upload started)
        start_time = st.session_state.get('upload_start_time', time.time())
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
                    st.warning(f"⚠️ {I18n.t('upload_completed_with_issues')}")
                    st.success(f"✅ {len(successful_files)} {I18n.t('files_processed_successfully')}")
                    st.error(f"❌ {len(failed_files)} {I18n.t('files_failed')}")
                    for failed_file in failed_files:
                        st.error(f"  • {failed_file.get('name', 'Unknown')}: {failed_file.get('error', 'Unknown error')}")
                    st.info(f"🤖 {I18n.t('assistant_created_with_documents', count=len(successful_files))}")
                elif failed_files:
                    # All failed
                    st.error(f"❌ {I18n.t('upload_failed_all_files', count=len(failed_files))}")
                    for failed_file in failed_files:
                        st.error(f"  • {failed_file.get('name', 'Unknown')}: {failed_file.get('error', 'Unknown error')}")
                else:
                    # All success
                    st.success(f"✅ {I18n.t('upload_completed_success')}")
                    st.info(f"🤖 {I18n.t('assistant_created_ready', assistant_name=operation.get('assistant_name'))}")
                
                # Trigger assistant list refresh
                if 'ragflow_assistants_cache' in st.session_state:
                    del st.session_state.ragflow_assistants_cache
                if 'available_ragflow_assistants' in st.session_state:
                    del st.session_state.available_ragflow_assistants
                
                Logger.info(f"Upload operation {operation_id} completed")
                
                # Reset upload state so users can upload more documents
                _reset_upload_state()
                time.sleep(2)
                st.rerun()
                
            elif status == "failed":
                st.session_state.upload_status = "FAILURE"
                st.session_state.upload_error = operation.get('error_message', 'Unknown error')
                st.error(f"❌ Upload operation failed: {st.session_state.upload_error}")
                
                # Reset upload state so users can try again
                time.sleep(3)
                _reset_upload_state()
                st.rerun()
                
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
                                st.session_state.upload_error = I18n.t('all_documents_failed')
                                st.error(f"❌ {I18n.t('all_documents_failed')}")
                                
                                # Reset upload state so users can try again
                                time.sleep(3)
                                _reset_upload_state()
                                st.rerun()
                
                # Process one step of the operation
                upload_manager.process_upload_operation(operation_id)
                
                status_placeholder.info(
                    f"📋 {I18n.t('upload_status_message', status=str(status).title(), stage=str(stage).title(), progress=progress, minutes=int(minutes), seconds=int(seconds))}"
                )
                time.sleep(5)
                st.rerun()


def _reset_upload_state():
    """Reset upload state (like reset transcription)."""
    st.session_state.upload_files = None
    st.session_state.upload_operation_id = None
    st.session_state.upload_status = None
    st.session_state.upload_result = None
    st.session_state.upload_error = None
    st.session_state.upload_processing = False
    st.session_state.upload_start_time = None
    
    # Increment widget key to force file uploader reset (Streamlit pattern)
    st.session_state.upload_widget_key += 1
    
    # Clear any active operations from session state
    if 'upload_operations' in st.session_state:
        st.session_state.upload_operations = {}


def render_upload_interface() -> None:
    """Main upload interface combining workflow and status."""
    render_upload_workflow()
    if st.session_state.get('upload_processing', False):
        render_upload_status()