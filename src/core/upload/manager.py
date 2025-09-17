"""
Main upload manager that coordinates all upload functionality.
"""

import os
import time
import tempfile
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

import streamlit as st

from ...ragflow_client import create_client
from ...utils.logger import Logger
from ...config import MAX_FILE_SIZE_MB, SUPPORTED_FILE_TYPES
from .status import UploadStatus, ProcessingStage
from .operations import UploadOperations


class UploadManager:
    """Main upload manager that coordinates all upload functionality."""
    
    def __init__(self):
        """Initialize the upload manager."""
        self.client = create_client()
        self.operations = UploadOperations()
        self._init_session_state()
    
    def _init_session_state(self):
        """Initialize session state for upload tracking."""
        if 'upload_operations' not in st.session_state:
            st.session_state.upload_operations = {}
        
        if 'upload_datasets' not in st.session_state:
            st.session_state.upload_datasets = {}
        
        if 'upload_assistants' not in st.session_state:
            st.session_state.upload_assistants = {}
        
        # Initialize other components - removed history and statistics
    
    def validate_files(self, uploaded_files: List[Any]) -> Tuple[List[Any], List[str]]:
        """Validate uploaded files for type, size, and duplicates."""
        valid_files = []
        errors = []
        
        # Use centralized configuration
        supported_types = SUPPORTED_FILE_TYPES
        max_file_size = MAX_FILE_SIZE_MB * 1024 * 1024  # Convert MB to bytes
        
        seen_hashes = set()
        
        for file in uploaded_files:
            # Check file type
            file_ext = os.path.splitext(file.name)[1].lower()
            if file_ext not in supported_types:
                errors.append(f"❌ {file.name}: Unsupported file type. Only PDF files are supported.")
                continue
            
            # Check file size
            if file.size > max_file_size:
                size_mb = file.size / (1024 * 1024)
                errors.append(f"❌ {file.name}: File too large ({size_mb:.1f}MB). Maximum: {MAX_FILE_SIZE_MB}MB")
                continue
            
            # Check for duplicates by content hash
            file.seek(0)
            file_hash = hashlib.md5(file.read()).hexdigest()
            file.seek(0)
            
            if file_hash in seen_hashes:
                errors.append(f"❌ {file.name}: Duplicate file detected")
                continue
            
            seen_hashes.add(file_hash)
            valid_files.append(file)
        
        return valid_files, errors
    
    def start_upload_operation(self, files: List[Any], dataset_option: str,
                             dataset_id: Optional[str] = None, dataset_name: Optional[str] = None,
                             dataset_description: str = "") -> str:
        """Start a new upload operation."""
        operation_id = f"upload_{int(time.time())}_{len(st.session_state.upload_operations)}"
        
        # Calculate total size for statistics
        total_size_mb = sum(file.size for file in files) / (1024 * 1024)
        
        # Create operation record
        operation = {
            'id': operation_id,
            'status': UploadStatus.PENDING.value,
            'stage': ProcessingStage.UPLOAD.value,
            'created_at': datetime.now().isoformat(),
            'started_at': datetime.now().isoformat(),
            'dataset_option': dataset_option,
            'dataset_id': dataset_id,
            'dataset_name': dataset_name or f"Upload {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            'dataset_description': dataset_description,
            'files': [],
            'progress': 0,
            'error_message': None,
            'assistant_id': None,
            'assistant_name': None,
            'retry_count': 0,
            'total_size_mb': total_size_mb,
            'upload_speed_mbps': 0,
            'network_errors': 0,
            'last_activity': datetime.now().isoformat()
        }
        
        # Process files and save temporarily
        for file in files:
            file_info = {
                'name': file.name,
                'size': file.size,
                'type': file.type,
                'status': UploadStatus.PENDING.value,
                'document_id': None,
                'temp_path': None
            }
            
            # Save file to temporary location
            try:
                temp_dir = tempfile.mkdtemp(prefix=f"upload_{operation_id}_")
                temp_path = os.path.join(temp_dir, file.name)
                
                with open(temp_path, 'wb') as f:
                    f.write(file.read())
                
                file_info['temp_path'] = temp_path
                Logger.info(f"Saved uploaded file {file.name} to {temp_path}")
                
            except Exception as e:
                file_info['status'] = UploadStatus.FAILED.value
                file_info['error'] = str(e)
                Logger.error(f"Error saving uploaded file {file.name}: {e}")
            
            operation['files'].append(file_info)
        
        # Store operation in session state
        st.session_state.upload_operations[operation_id] = operation
        
        Logger.info(f"Started upload operation {operation_id} with {len(files)} files")
        
        return operation_id
    
    # Delegate to modular components
    def get_active_operations(self) -> List[Dict[str, Any]]:
        """Get list of active upload operations."""
        return self.operations.get_active_operations()
    
    def get_recent_operations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get list of recent upload operations."""
        return self.operations.get_recent_operations(limit)
    
    def get_operation_status(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific operation."""
        return self.operations.get_operation_status(operation_id)
    
    def delete_operation(self, operation_id: str) -> bool:
        """Delete an upload operation."""
        return self.operations.delete_operation(operation_id)
    
    def retry_failed_operation(self, operation_id: str) -> bool:
        """Retry a failed operation."""
        return self.operations.retry_failed_operation(operation_id)
    
    def pause_operation(self, operation_id: str) -> bool:
        """Pause an active operation."""
        return self.operations.pause_operation(operation_id)
    
    def resume_operation(self, operation_id: str) -> bool:
        """Resume a paused operation."""
        return self.operations.resume_operation(operation_id)
    
    
    def process_upload_operation(self, operation_id: str) -> bool:
        """Process a single step of an upload operation."""
        if operation_id not in st.session_state.upload_operations:
            Logger.error(f"Upload operation {operation_id} not found")
            return True
        
        operation = st.session_state.upload_operations[operation_id]
        status = operation.get('status')
        stage = operation.get('stage')
        
        Logger.info(f"Processing operation {operation_id}, current status: {status}, stage: {stage}")
        
        try:
            if status == UploadStatus.PENDING.value and stage == ProcessingStage.UPLOAD.value:
                # Stage 1: Upload files to RAGFlow
                return self._process_upload_stage(operation_id)
            
            elif status == UploadStatus.UPLOADING.value and stage == ProcessingStage.PARSING.value:
                # Stage 2: Wait for parsing to complete
                return self._process_parsing_stage(operation_id)
            
            elif status == UploadStatus.PROCESSING.value and stage == ProcessingStage.CHUNKING.value:
                # Stage 3: Wait for chunking to complete
                return self._process_chunking_stage(operation_id)
            
            elif status == UploadStatus.PROCESSING.value and stage == ProcessingStage.EMBEDDING.value:
                # Stage 4: Wait for embedding to complete
                return self._process_embedding_stage(operation_id)
            
            elif status == UploadStatus.PROCESSING.value and stage == ProcessingStage.ASSISTANT_CREATION.value:
                # Stage 5: Create chat assistant
                return self._process_assistant_creation_stage(operation_id)
            
            else:
                Logger.warning(f"Unknown operation state: status={status}, stage={stage}")
                return False
                
        except Exception as e:
            Logger.error(f"Error processing operation {operation_id}: {str(e)}")
            self._mark_operation_failed(operation_id, str(e))
            return True
    
    def _process_upload_stage(self, operation_id: str) -> bool:
        """Process the file upload stage."""
        operation = st.session_state.upload_operations[operation_id]
        
        # Create dataset if needed (only once per operation)
        dataset_option = operation.get('dataset_option')
        if dataset_option == 'new' and not operation.get('dataset_id'):
            # Create new dataset only if we don't have one yet
            try:
                dataset_response = self.client.create_dataset_with_validation(
                    name=operation.get('dataset_name'),
                    description=operation.get('dataset_description', '')
                )
                
                if dataset_response.get('code') == 0:
                    dataset_id = dataset_response.get('data', {}).get('id')
                    operation['dataset_id'] = dataset_id
                    Logger.info(f"Created new dataset {dataset_id} for operation {operation_id}")
                elif "already exists" in dataset_response.get('message', ''):
                    # Dataset already exists, try to find it
                    Logger.info(f"Dataset '{operation.get('dataset_name')}' already exists, trying to find it")
                    datasets_response = self.client.get_datasets()
                    if datasets_response.get('code') == 0:
                        datasets = datasets_response.get('data', [])
                        for dataset in datasets:
                            if dataset.get('name') == operation.get('dataset_name'):
                                operation['dataset_id'] = dataset.get('id')
                                Logger.info(f"Found existing dataset {dataset.get('id')} for operation {operation_id}")
                                break
                        else:
                            raise Exception(f"Could not find existing dataset: {operation.get('dataset_name')}")
                    else:
                        raise Exception(f"Failed to find existing dataset: {datasets_response.get('message')}")
                else:
                    raise Exception(f"Failed to create dataset: {dataset_response.get('message')}")
                    
            except Exception as e:
                self._mark_operation_failed(operation_id, f"Failed to create dataset: {str(e)}")
                return True
        
        # Upload files to the dataset
        dataset_id = operation.get('dataset_id')
        if not dataset_id:
            self._mark_operation_failed(operation_id, "No dataset ID available")
            return True
        
        files_to_upload = []
        for file_info in operation.get('files', []):
            if file_info.get('status') == UploadStatus.PENDING.value and file_info.get('temp_path'):
                files_to_upload.append(file_info)
        
        if not files_to_upload:
            # No files to upload, move to next stage
            operation['stage'] = ProcessingStage.PARSING.value
            operation['status'] = UploadStatus.UPLOADING.value
            operation['progress'] = 20
            st.session_state.upload_operations[operation_id] = operation
            return False
        
        # Upload one file at a time to avoid overwhelming the system
        file_info = files_to_upload[0]
        temp_path = file_info.get('temp_path')
        
        try:
            # Upload file to RAGFlow using the enhanced method
            upload_response = self.client.upload_document_with_progress(
                dataset_id,
                temp_path,
                file_name=file_info['name']
            )
            
            if upload_response.get('code') == 0:
                document_id = upload_response.get('data', {}).get('id')
                file_info['document_id'] = document_id
                file_info['status'] = UploadStatus.UPLOADED.value
                Logger.info(f"Successfully uploaded {file_info['name']} as document {document_id}")
                
                # Calculate progress based on uploaded files
                uploaded_files = len([f for f in operation['files'] if f.get('status') == UploadStatus.UPLOADED.value])
                total_files = len(operation['files'])
                operation['progress'] = int(uploaded_files / total_files * 20)  # Upload stage is 20% of total
                
            else:
                file_info['status'] = UploadStatus.FAILED.value
                file_info['error'] = upload_response.get('message', 'Upload failed')
                Logger.error(f"Failed to upload {file_info['name']}: {file_info['error']}")
        
        except Exception as e:
            file_info['status'] = UploadStatus.FAILED.value
            file_info['error'] = str(e)
            Logger.error(f"Error uploading {file_info['name']}: {str(e)}")
        
        # Update operation
        st.session_state.upload_operations[operation_id] = operation
        
        # Check if all files are done uploading (either successful or failed)
        pending_files = [f for f in operation['files'] if f.get('status') == UploadStatus.PENDING.value]
        if not pending_files:
            # Check if any files were uploaded successfully
            uploaded_files = [f for f in operation['files'] if f.get('status') == UploadStatus.UPLOADED.value]
            if uploaded_files:
                # Move to parsing stage
                operation['stage'] = ProcessingStage.PARSING.value
                operation['status'] = UploadStatus.UPLOADING.value
                operation['progress'] = 20
                st.session_state.upload_operations[operation_id] = operation
                Logger.info(f"All files processed, moving to parsing stage. {len(uploaded_files)} files uploaded successfully.")
            else:
                # All files failed
                self._mark_operation_failed(operation_id, "All files failed to upload")
                return True
        
        return False  # Continue processing
    
    def _process_parsing_stage(self, operation_id: str) -> bool:
        """Wait for document parsing to complete."""
        operation = st.session_state.upload_operations[operation_id]
        dataset_id = operation.get('dataset_id')
        
        if not dataset_id:
            self._mark_operation_failed(operation_id, "No dataset ID for parsing check")
            return True
        
        try:
            # Check parsing status
            status_response = self.client.check_dataset_processing_status(dataset_id)
            if status_response.get('code') == 0:
                status_data = status_response.get('data', {})
                processing_docs = status_data.get('processing_docs', 0)
                
                if processing_docs == 0:
                    # Parsing complete, move to chunking
                    operation['stage'] = ProcessingStage.CHUNKING.value
                    operation['status'] = UploadStatus.PROCESSING.value
                    operation['progress'] = 40
                    st.session_state.upload_operations[operation_id] = operation
                    Logger.info(f"Parsing completed for operation {operation_id}")
                else:
                    # Still parsing
                    operation['progress'] = 30
                    st.session_state.upload_operations[operation_id] = operation
            else:
                Logger.warning(f"Could not check parsing status: {status_response.get('message')}")
        
        except Exception as e:
            Logger.error(f"Error checking parsing status: {str(e)}")
        
        return False  # Continue processing
    
    def _process_chunking_stage(self, operation_id: str) -> bool:
        """Wait for document chunking to complete."""
        operation = st.session_state.upload_operations[operation_id]
        
        # Simulate chunking progress (RAGFlow handles this automatically)
        operation['stage'] = ProcessingStage.EMBEDDING.value
        operation['progress'] = 60
        st.session_state.upload_operations[operation_id] = operation
        Logger.info(f"Chunking completed for operation {operation_id}")
        
        return False  # Continue processing
    
    def _process_embedding_stage(self, operation_id: str) -> bool:
        """Wait for embedding generation to complete."""
        operation = st.session_state.upload_operations[operation_id]
        
        # Check if all documents are fully processed
        dataset_id = operation.get('dataset_id')
        if dataset_id:
            try:
                status_response = self.client.check_dataset_processing_status(dataset_id)
                if status_response.get('code') == 0:
                    status_data = status_response.get('data', {})
                    processing_docs = status_data.get('processing_docs', 0)
                    processed_docs = status_data.get('processed_docs', 0)
                    
                    if processing_docs == 0 and processed_docs > 0:
                        # Embedding complete, move to assistant creation
                        operation['stage'] = ProcessingStage.ASSISTANT_CREATION.value
                        operation['progress'] = 80
                        st.session_state.upload_operations[operation_id] = operation
                        Logger.info(f"Embedding completed for operation {operation_id}")
                    else:
                        # Still processing
                        operation['progress'] = 70
                        st.session_state.upload_operations[operation_id] = operation
            except Exception as e:
                Logger.error(f"Error checking embedding status: {str(e)}")
        
        return False  # Continue processing
    
    def _process_assistant_creation_stage(self, operation_id: str) -> bool:
        """Create chat assistant for the dataset."""
        operation = st.session_state.upload_operations[operation_id]
        dataset_id = operation.get('dataset_id')
        
        if not dataset_id:
            self._mark_operation_failed(operation_id, "No dataset ID for assistant creation")
            return True
        
        try:
            # Create chat assistant
            assistant_name = f"{operation.get('dataset_name')} Assistant"
            assistant_response = self.client.create_chat_assistant(
                name=assistant_name,
                dataset_ids=[dataset_id],
                description=f"Chat assistant for {operation.get('dataset_name')} documents"
            )
            
            if assistant_response.get('code') == 0:
                assistant_id = assistant_response.get('data', {}).get('id')
                operation['assistant_id'] = assistant_id
                operation['assistant_name'] = assistant_name
                operation['status'] = UploadStatus.COMPLETED.value
                operation['progress'] = 100
                operation['completed_at'] = datetime.now().isoformat()
                
                st.session_state.upload_operations[operation_id] = operation
                
                Logger.info(f"Successfully created assistant {assistant_id} for operation {operation_id}")
                return True  # Operation complete
            else:
                raise Exception(f"Failed to create assistant: {assistant_response.get('message')}")
                
        except Exception as e:
            self._mark_operation_failed(operation_id, f"Failed to create assistant: {str(e)}")
            return True
    
    def _mark_operation_failed(self, operation_id: str, error_message: str):
        """Mark an operation as failed."""
        if operation_id in st.session_state.upload_operations:
            operation = st.session_state.upload_operations[operation_id]
            operation['status'] = UploadStatus.FAILED.value
            operation['error_message'] = error_message
            operation['completed_at'] = datetime.now().isoformat()
            st.session_state.upload_operations[operation_id] = operation
            Logger.error(f"Operation {operation_id} failed: {error_message}")
    
    def get_user_datasets(self) -> List[Dict[str, Any]]:
        """Get list of available datasets for selection."""
        try:
            response = self.client.get_datasets()
            if response.get('code') == 0:
                # The data field contains the list of datasets directly
                return response.get('data', [])
            else:
                Logger.error(f"Error fetching datasets: {response.get('message')}")
                return []
        except Exception as e:
            Logger.error(f"Error fetching user datasets: {e}")
            return []
    
    def refresh_assistants_list(self):
        """Refresh the assistants list to include newly created ones."""
        try:
            # Clear cache to force refresh
            if 'ragflow_assistants_cache' in st.session_state:
                del st.session_state.ragflow_assistants_cache
            if 'available_ragflow_assistants' in st.session_state:
                del st.session_state.available_ragflow_assistants
            Logger.info("Assistants list cache cleared for refresh")
        except Exception as e:
            Logger.error(f"Error refreshing assistants list: {e}")


# Global upload manager instance
_upload_manager = None

def get_upload_manager() -> UploadManager:
    """Get the global upload manager instance."""
    global _upload_manager
    if _upload_manager is None:
        _upload_manager = UploadManager()
    return _upload_manager