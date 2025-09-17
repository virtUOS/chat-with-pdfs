"""
Document uploader component for user file uploads.
"""

import time
import streamlit as st
from typing import List, Any, Optional

from ...core.upload_manager import get_upload_manager
from ...utils.logger import Logger
from ...utils.i18n import I18n


def render_document_uploader() -> None:
    """Render the document upload interface."""
    upload_manager = get_upload_manager()
    
    st.header("📤 Upload Documents")
    st.markdown("Upload your documents to create a new knowledge base and chat assistant.")
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Choose files to upload",
        type=['pdf', 'txt', 'docx', 'md'],
        accept_multiple_files=True,
        help="Supported formats: PDF, TXT, DOCX, MD. Maximum size: 50MB per file."
    )
    
    if uploaded_files:
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
        
        # Show valid files
        if valid_files:
            st.success(f"✅ **{len(valid_files)} files ready for upload**")
            
            with st.expander("📋 File Details", expanded=False):
                for file in valid_files:
                    file_size_mb = file.size / (1024 * 1024)
                    st.write(f"• **{file.name}** ({file_size_mb:.1f} MB)")
        
        # Dataset selection section
        if valid_files:
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
                # New dataset form
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    dataset_name = st.text_input(
                        "Dataset Name *",
                        placeholder="e.g., Research Papers, Company Documents, etc.",
                        help="Choose a descriptive name for your document collection"
                    )
                
                with col2:
                    # Auto-generate name button
                    if st.button("🎯 Auto-generate", help="Generate name based on uploaded files"):
                        # Simple auto-generation logic
                        file_types = set()
                        for file in valid_files:
                            if 'research' in file.name.lower() or 'paper' in file.name.lower():
                                file_types.add('Research')
                            elif 'report' in file.name.lower():
                                file_types.add('Reports')
                            elif 'manual' in file.name.lower() or 'guide' in file.name.lower():
                                file_types.add('Documentation')
                            else:
                                file_types.add('Documents')
                        
                        suggested_name = f"{' & '.join(file_types)} - {len(valid_files)} files"
                        st.session_state.suggested_dataset_name = suggested_name
                        st.rerun()
                
                # Use suggested name if available
                if 'suggested_dataset_name' in st.session_state and not dataset_name:
                    dataset_name = st.session_state.suggested_dataset_name
                    del st.session_state.suggested_dataset_name
                
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
                        doc_count = len(upload_manager.client.get_documents(dataset.get('id', '')).get('data', {}).get('docs', []))
                        dataset_options.append(f"{name} ({doc_count} documents)")
                        dataset_ids.append(dataset.get('id'))
                    
                    selected_dataset_idx = st.selectbox(
                        "Select Dataset",
                        range(len(dataset_options)),
                        format_func=lambda x: dataset_options[x],
                        help="Choose an existing dataset to add your documents to"
                    )
                    
                    if selected_dataset_idx is not None:
                        dataset_id = dataset_ids[selected_dataset_idx]
                        selected_dataset = user_datasets[selected_dataset_idx]
                        dataset_name = selected_dataset.get('name')
                        
                        # Show dataset info
                        st.info(f"📚 Adding to: **{dataset_name}**")
                        if selected_dataset.get('description'):
                            st.caption(selected_dataset.get('description'))
                
                else:
                    st.warning("No existing datasets found. Please create a new dataset.")
                    dataset_option = "Create New Dataset"
            
            # Upload button
            can_upload = (
                valid_files and 
                (dataset_option == "Add to Existing Dataset" and dataset_id) or
                (dataset_option == "Create New Dataset" and dataset_name and dataset_name.strip())
            )
            
            if can_upload:
                st.subheader("🚀 Ready to Upload")
                
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    if st.button("📤 Start Upload", type="primary", use_container_width=True):
                        # Start upload operation
                        operation_id = upload_manager.start_upload_operation(
                            files=valid_files,
                            dataset_option="new" if dataset_option == "Create New Dataset" else "existing",
                            dataset_id=dataset_id,
                            dataset_name=dataset_name,
                            dataset_description=dataset_description
                        )
                        
                        st.success(f"✅ Upload started! Operation ID: {operation_id}")
                        st.info("🔄 Your documents are being processed. You can continue using the app - you'll be notified when your assistant is ready!")
                        
                        # Clear the uploaded files
                        st.session_state.clear_upload_files = True
                        st.rerun()
                
                with col2:
                    st.caption("🔄 Processing time:")
                    st.caption("~2-5 min per document")
                
                with col3:
                    st.caption("📋 What happens:")
                    st.caption("Upload → Parse → Create Assistant")
            
            elif dataset_option == "Create New Dataset" and not (dataset_name and dataset_name.strip()):
                st.warning("⚠️ Please enter a dataset name to continue.")
            
            elif dataset_option == "Add to Existing Dataset" and not dataset_id:
                st.warning("⚠️ Please select a dataset to continue.")
    
    # Clear files if requested
    if st.session_state.get('clear_upload_files', False):
        st.session_state.clear_upload_files = False
        # This would clear the file uploader on next render


def render_upload_status_panel() -> None:
    """Render the upload status panel showing active operations."""
    upload_manager = get_upload_manager()
    
    # Get operations without processing them automatically
    active_operations = upload_manager.get_active_operations()
    recent_operations = upload_manager.get_recent_operations(limit=5)
    
    if active_operations or recent_operations:
        st.subheader("📊 Upload Status")
        
        # Show active operations with processing logic (like transcription app)
        if active_operations:
            st.markdown("**🔄 Active Uploads:**")
            
            # Process operations like transcription app handles status checking
            for operation in active_operations:
                operation_id = operation['id']
                
                with st.container():
                    _render_operation_status(operation, is_active=True)
                    st.divider()
                
                # Handle processing for this operation (like transcription while loop)
                if operation.get('status') not in ['completed', 'failed']:
                    start_time = time.time()
                    placeholder = st.empty()
                    
                    # Process this operation step
                    completed = upload_manager.process_upload_operation(operation_id)
                    updated_operation = upload_manager.get_operation_status(operation_id)
                    
                    if updated_operation:
                        if updated_operation.get('status') == 'completed':
                            st.success("✅ Upload completed! Assistant created successfully.")
                            # Trigger assistant list refresh
                            if 'ragflow_assistants_cache' in st.session_state:
                                del st.session_state.ragflow_assistants_cache
                            if 'available_ragflow_assistants' in st.session_state:
                                del st.session_state.available_ragflow_assistants
                            time.sleep(1)
                            st.rerun()
                        elif updated_operation.get('status') == 'failed':
                            st.error(f"❌ Upload failed: {updated_operation.get('error_message', 'Unknown error')}")
                            time.sleep(1)
                            st.rerun()
                        else:
                            # Still processing - show status and check again in 5 seconds
                            status = updated_operation.get('status', 'processing')
                            stage = updated_operation.get('stage', 'unknown')
                            progress = updated_operation.get('progress', 0)
                            
                            elapsed_time = time.time() - start_time
                            minutes, seconds = divmod(elapsed_time, 60)
                            
                            placeholder.info(
                                f"📋 Status: {status.title()} ({stage.title()}). "
                                f"Progress: {progress}%. "
                                f"Elapsed: {int(minutes)} min {int(seconds)} sec. "
                                f"Checking again in 5 seconds..."
                            )
                            time.sleep(5)
                            st.rerun()
        
        # Show recent completed operations
        completed_recent = [op for op in recent_operations if op.get('status') in ['completed', 'failed']]
        if completed_recent:
            with st.expander(f"📋 Recent Operations ({len(completed_recent)})", expanded=False):
                for operation in completed_recent[:3]:  # Show last 3
                    _render_operation_status(operation, is_active=False)
                    st.divider()


def _render_operation_status(operation: dict, is_active: bool = True) -> None:
    """Render status for a single upload operation."""
    status = operation.get('status', 'unknown')
    stage = operation.get('stage', 'unknown')
    progress = operation.get('progress', 0)
    dataset_name = operation.get('dataset_name', 'Unknown Dataset')
    files_count = len(operation.get('files', []))
    
    # Status icon and color
    if status == 'completed':
        status_icon = "✅"
        status_color = "green"
    elif status == 'failed':
        status_icon = "❌"
        status_color = "red"
    elif status == 'processing':
        status_icon = "🔄"
        status_color = "blue"
    else:
        status_icon = "⏳"
        status_color = "orange"
    
    # Main status line
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        st.markdown(f"{status_icon} **{dataset_name}** ({files_count} files)")
        if operation.get('assistant_name'):
            st.caption(f"🤖 Assistant: {operation.get('assistant_name')}")
    
    with col2:
        st.caption(f"Stage: {stage.title()}")
    
    with col3:
        if is_active and status not in ['completed', 'failed']:
            st.progress(progress / 100, text=f"{progress}%")
        else:
            st.caption(f"Status: {status.title()}")
    
    # Show error message if failed
    if status == 'failed' and operation.get('error_message'):
        st.error(f"Error: {operation.get('error_message')}")
    
    # Show detailed file status for active operations
    if is_active and files_count > 1:
        with st.expander("📄 File Details", expanded=False):
            for file_info in operation.get('files', []):
                file_status = file_info.get('status', 'pending')
                file_name = file_info.get('name', 'Unknown')
                
                if file_status == 'completed':
                    st.success(f"✅ {file_name}")
                elif file_status == 'failed':
                    st.error(f"❌ {file_name}: {file_info.get('error', 'Unknown error')}")
                elif file_status == 'uploaded':
                    st.info(f"🔄 {file_name} - Processing...")
                else:
                    st.info(f"⏳ {file_name} - Pending...")