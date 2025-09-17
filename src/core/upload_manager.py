"""
Upload Manager for RAGFlow Document Processing

Handles document upload workflow, status tracking, and background processing
coordination using Streamlit-compatible patterns.
"""

import os
import time
import tempfile
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum

import streamlit as st

from ..ragflow_client import create_client
from ..utils.logger import Logger
from ..config import MAX_FILE_SIZE_MB, SUPPORTED_FILE_TYPES


class UploadStatus(Enum):
    """Upload operation status enumeration."""
    PENDING = "pending"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingStage(Enum):
    """Document processing stage enumeration."""
    UPLOAD = "upload"
    PARSING = "parsing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    ASSISTANT_CREATION = "assistant_creation"
    COMPLETED = "completed"


class UploadManager:
    """Manages document upload workflow and background processing coordination."""
    
    def __init__(self):
        """Initialize the upload manager."""
        self.client = create_client()
        self._init_session_state()
    
    def _init_session_state(self):
        """Initialize session state for upload tracking."""
        if 'upload_operations' not in st.session_state:
            st.session_state.upload_operations = {}
        
        if 'upload_datasets' not in st.session_state:
            st.session_state.upload_datasets = {}
        
        if 'upload_assistants' not in st.session_state:
            st.session_state.upload_assistants = {}
    
    def validate_files(self, uploaded_files: List[Any]) -> Tuple[List[Any], List[str]]:
        """
        Validate uploaded files for type, size, and duplicates.
        
        Args:
            uploaded_files: List of Streamlit uploaded file objects
            
        Returns:
            Tuple of (valid_files, error_messages)
        """
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
                errors.append(f"❌ {file.name}: Unsupported file type. Supported: PDF, TXT, DOCX, MD")
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
        """
        Start a new upload operation.
        
        Args:
            files: List of Streamlit uploaded file objects
            dataset_option: "new" or "existing"
            dataset_id: ID of existing dataset (if dataset_option is "existing")
            dataset_name: Name for new dataset (if dataset_option is "new")
            dataset_description: Description for new dataset
            
        Returns:
            Operation ID for tracking
        """
        operation_id = f"upload_{int(time.time())}_{len(st.session_state.upload_operations)}"
        
        # Create operation record
        operation = {
            'id': operation_id,
            'status': UploadStatus.PENDING.value,
            'stage': ProcessingStage.UPLOAD.value,
            'created_at': datetime.now().isoformat(),
            'dataset_option': dataset_option,
            'dataset_id': dataset_id,
            'dataset_name': dataset_name or f"Upload {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            'dataset_description': dataset_description,
            'files': [],
            'progress': 0,
            'error_message': None,
            'assistant_id': None,
            'assistant_name': None
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
    
    def process_upload_operation(self, operation_id: str) -> bool:
        """
        Process a single step of an upload operation.
        
        Args:
            operation_id: ID of the operation to process
            
        Returns:
            True if operation completed (success or failure), False if still processing
        """
        if operation_id not in st.session_state.upload_operations:
            Logger.error(f"Upload operation {operation_id} not found")
            return True
        
        operation = st.session_state.upload_operations[operation_id]
        current_stage = operation.get('stage')
        
        try:
            if current_stage == ProcessingStage.UPLOAD.value:
                return self._process_dataset_creation(operation_id)
            
            elif current_stage == ProcessingStage.PARSING.value:
                return self._process_document_upload(operation_id)
            
            elif current_stage == ProcessingStage.CHUNKING.value:
                return self._check_document_processing(operation_id)
            
            elif current_stage == ProcessingStage.EMBEDDING.value:
                return self._check_document_processing(operation_id)
            
            elif current_stage == ProcessingStage.ASSISTANT_CREATION.value:
                return self._process_assistant_creation(operation_id)
            
            elif current_stage == ProcessingStage.COMPLETED.value:
                return True
            
            else:
                Logger.error(f"Unknown processing stage: {current_stage}")
                self._mark_operation_failed(operation_id, f"Unknown processing stage: {current_stage}")
                return True
                
        except Exception as e:
            Logger.error(f"Error processing upload operation {operation_id}: {e}")
            self._mark_operation_failed(operation_id, str(e))
            return True
    
    def _process_dataset_creation(self, operation_id: str) -> bool:
        """Process dataset creation step."""
        operation = st.session_state.upload_operations[operation_id]
        
        try:
            if operation['dataset_option'] == 'new':
                # Create new dataset
                response = self.client.create_dataset_with_validation(
                    name=operation['dataset_name'],
                    description=operation['dataset_description']
                )
                
                if response.get('code') == 0:
                    dataset_data = response.get('data', {})
                    operation['dataset_id'] = dataset_data.get('id')
                    Logger.info(f"Created new dataset {dataset_data.get('id')} for operation {operation_id}")
                else:
                    self._mark_operation_failed(operation_id, f"Dataset creation failed: {response.get('message')}")
                    return True
            
            # Move to document upload stage
            operation['stage'] = ProcessingStage.PARSING.value
            operation['progress'] = 20
            st.session_state.upload_operations[operation_id] = operation
            
            return False  # Continue processing
            
        except Exception as e:
            self._mark_operation_failed(operation_id, f"Dataset creation error: {str(e)}")
            return True
    
    def _process_document_upload(self, operation_id: str) -> bool:
        """Process document upload step."""
        operation = st.session_state.upload_operations[operation_id]
        
        try:
            dataset_id = operation.get('dataset_id')
            if not dataset_id:
                self._mark_operation_failed(operation_id, "No dataset ID available for upload")
                return True
            
            uploaded_any = False
            
            # Upload each file
            for file_info in operation['files']:
                if file_info['status'] != UploadStatus.PENDING.value:
                    continue
                
                temp_path = file_info.get('temp_path')
                if not temp_path or not os.path.exists(temp_path):
                    file_info['status'] = UploadStatus.FAILED.value
                    file_info['error'] = "Temporary file not found"
                    continue
                
                # Upload to RAGFlow using the enhanced method
                try:
                    response = self.client.upload_document_with_progress(
                        dataset_id=dataset_id,
                        file_path=temp_path,
                        file_name=file_info['name']
                    )
                except Exception as e:
                    # Fallback to basic upload method if enhanced fails
                    Logger.warning(f"Enhanced upload failed for {file_info['name']}, trying basic upload: {e}")
                    response = self.client.upload_document(dataset_id, temp_path)
                
                if response.get('code') == 0:
                    doc_data = response.get('data', {})
                    file_info['document_id'] = doc_data.get('id')
                    file_info['status'] = UploadStatus.UPLOADED.value
                    uploaded_any = True
                    Logger.info(f"Uploaded {file_info['name']} with document ID {doc_data.get('id')}")
                else:
                    file_info['status'] = UploadStatus.FAILED.value
                    file_info['error'] = response.get('message', 'Upload failed')
                    Logger.error(f"Failed to upload {file_info['name']}: {response.get('message')}")
            
            if uploaded_any:
                # Trigger parsing for uploaded documents
                dataset_id = operation.get('dataset_id')
                parse_response = self.client.trigger_document_parsing(dataset_id)
                
                if parse_response.get('code') == 0:
                    Logger.info(f"Document parsing triggered for dataset {dataset_id}")
                    # Move to processing check stage
                    operation['stage'] = ProcessingStage.CHUNKING.value
                    operation['progress'] = 40
                else:
                    Logger.warning(f"Failed to trigger parsing: {parse_response.get('message')}")
                    # Continue anyway - parsing might start automatically
                    operation['stage'] = ProcessingStage.CHUNKING.value
                    operation['progress'] = 40
            else:
                self._mark_operation_failed(operation_id, "No files were successfully uploaded")
                return True
            
            st.session_state.upload_operations[operation_id] = operation
            return False  # Continue processing
            
        except Exception as e:
            self._mark_operation_failed(operation_id, f"Document upload error: {str(e)}")
            return True
    
    def _check_document_processing(self, operation_id: str) -> bool:
        """Check document processing status."""
        operation = st.session_state.upload_operations[operation_id]
        
        try:
            dataset_id = operation.get('dataset_id')
            response = self.client.check_dataset_processing_status(dataset_id)
            
            if response.get('code') != 0:
                self._mark_operation_failed(operation_id, f"Error checking processing status: {response.get('message')}")
                return True
            
            status_data = response.get('data', {})
            all_processed = status_data.get('all_processed', False)
            processed_docs = status_data.get('processed_docs', 0)
            total_docs = status_data.get('total_docs', 0)
            failed_docs = status_data.get('failed_docs', 0)
            processing_docs = status_data.get('processing_docs', 0)
            documents = status_data.get('documents', [])
            
            # Update individual file statuses in operation
            for file_info in operation.get('files', []):
                doc_id = file_info.get('document_id')
                if doc_id:
                    # Find this document in the status response
                    for doc in documents:
                        if doc.get('id') == doc_id:
                            doc_status = str(doc.get('status', ''))
                            chunk_count = doc.get('chunk_count', 0)
                            
                            if doc_status == "2" or chunk_count > 0:
                                file_info['status'] = 'completed'
                            elif doc_status == "-1":
                                file_info['status'] = 'failed'
                                file_info['error'] = 'Document parsing failed in RAGFlow'
                            else:
                                file_info['status'] = 'processing'
                            break
            
            # Update operation error message if there are failures
            if failed_docs > 0:
                failed_files = [f.get('name', 'Unknown') for f in operation.get('files', []) if f.get('status') == 'failed']
                operation['error_message'] = f"{failed_docs} documents failed: {', '.join(failed_files)}"
            
            if all_processed:
                # All documents finished processing (either success or failure)
                if processed_docs > 0:
                    # At least some succeeded - move to assistant creation
                    operation['stage'] = ProcessingStage.ASSISTANT_CREATION.value
                    operation['progress'] = 80
                    st.session_state.upload_operations[operation_id] = operation
                    return False  # Continue to assistant creation
                else:
                    # All failed - mark operation as failed
                    self._mark_operation_failed(operation_id, f"All {total_docs} documents failed to process")
                    return True
            else:
                # Update progress based on processing
                if total_docs > 0:
                    progress_percent = ((processed_docs + failed_docs) / total_docs) * 40  # 40% allocated to processing
                    operation['progress'] = 40 + progress_percent
                
                st.session_state.upload_operations[operation_id] = operation
                return False  # Still processing
            
        except Exception as e:
            self._mark_operation_failed(operation_id, f"Processing status check error: {str(e)}")
            return True
    
    def _process_assistant_creation(self, operation_id: str) -> bool:
        """Process assistant creation step."""
        operation = st.session_state.upload_operations[operation_id]
        
        try:
            dataset_id = operation.get('dataset_id')
            dataset_name = operation.get('dataset_name')
            
            response = self.client.auto_create_assistant(dataset_id, dataset_name)
            
            if response.get('code') == 0:
                assistant_data = response.get('data', {})
                operation['assistant_id'] = assistant_data.get('id')
                operation['assistant_name'] = assistant_data.get('name')
                operation['stage'] = ProcessingStage.COMPLETED.value
                operation['status'] = UploadStatus.COMPLETED.value
                operation['progress'] = 100
                
                # Store assistant info for easy access
                st.session_state.upload_assistants[assistant_data.get('id')] = {
                    'id': assistant_data.get('id'),
                    'name': assistant_data.get('name'),
                    'dataset_id': dataset_id,
                    'created_at': datetime.now().isoformat()
                }
                
                Logger.info(f"Created assistant {assistant_data.get('name')} for operation {operation_id}")
                
                # Clean up temporary files
                self._cleanup_operation_files(operation_id)
                
                return True  # Operation completed
            else:
                self._mark_operation_failed(operation_id, f"Assistant creation failed: {response.get('message')}")
                return True
            
        except Exception as e:
            self._mark_operation_failed(operation_id, f"Assistant creation error: {str(e)}")
            return True
    
    def _mark_operation_failed(self, operation_id: str, error_message: str):
        """Mark an operation as failed with error message."""
        if operation_id in st.session_state.upload_operations:
            operation = st.session_state.upload_operations[operation_id]
            operation['status'] = UploadStatus.FAILED.value
            operation['error_message'] = error_message
            st.session_state.upload_operations[operation_id] = operation
            
            # Clean up temporary files
            self._cleanup_operation_files(operation_id)
            
            Logger.error(f"Upload operation {operation_id} failed: {error_message}")
    
    def _cleanup_operation_files(self, operation_id: str):
        """Clean up temporary files for an operation."""
        if operation_id not in st.session_state.upload_operations:
            return
        
        operation = st.session_state.upload_operations[operation_id]
        
        for file_info in operation.get('files', []):
            temp_path = file_info.get('temp_path')
            if temp_path and os.path.exists(temp_path):
                try:
                    # Remove the file
                    os.unlink(temp_path)
                    # Try to remove the directory if empty
                    temp_dir = os.path.dirname(temp_path)
                    if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                        os.rmdir(temp_dir)
                except Exception as e:
                    Logger.warning(f"Could not clean up temporary file {temp_path}: {e}")
    
    def get_active_operations(self) -> List[Dict[str, Any]]:
        """Get list of active (non-completed, non-failed) upload operations."""
        active_ops = []
        
        for op_id, operation in st.session_state.upload_operations.items():
            status = operation.get('status')
            if status not in [UploadStatus.COMPLETED.value, UploadStatus.FAILED.value]:
                active_ops.append(operation)
        
        return active_ops
    
    def get_recent_operations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get list of recent upload operations."""
        operations = list(st.session_state.upload_operations.values())
        # Sort by creation time, most recent first
        operations.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return operations[:limit]
    
    def get_operation_status(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific operation."""
        return st.session_state.upload_operations.get(operation_id)
    
    def delete_operation(self, operation_id: str) -> bool:
        """Delete an upload operation and clean up its files."""
        if operation_id not in st.session_state.upload_operations:
            return False
        
        try:
            # Clean up files first
            self._cleanup_operation_files(operation_id)
            
            # Remove from session state
            del st.session_state.upload_operations[operation_id]
            
            Logger.info(f"Deleted upload operation {operation_id}")
            return True
            
        except Exception as e:
            Logger.error(f"Error deleting upload operation {operation_id}: {e}")
            return False
    
    def process_pending_operations(self):
        """Process all pending upload operations (call this periodically)."""
        active_operations = self.get_active_operations()
        
        for operation in active_operations:
            operation_id = operation['id']
            
            # Process this operation
            completed = self.process_upload_operation(operation_id)
            
            # Don't process too many at once to avoid blocking UI
            if not completed:
                # Only process one operation per call to keep UI responsive
                break
    
    def get_user_datasets(self) -> List[Dict[str, Any]]:
        """Get list of available datasets for selection."""
        try:
            response = self.client.get_datasets()
            if response.get('code') == 0:
                return response.get('data', [])
            else:
                Logger.error(f"Error getting datasets: {response.get('message')}")
                return []
        except Exception as e:
            Logger.error(f"Error retrieving user datasets: {e}")
            return []
    
    def get_dataset_info(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific dataset."""
        try:
            response = self.client.get_dataset_by_id(dataset_id)
            if response.get('code') == 0:
                return response.get('data')
            else:
                return None
        except Exception as e:
            Logger.error(f"Error getting dataset info for {dataset_id}: {e}")
            return None
    
    def refresh_assistants_list(self):
        """Refresh the assistants list to include newly created ones."""
        try:
            # This will trigger a refresh of the assistant list in the UI
            if 'ragflow_assistants_cache' in st.session_state:
                del st.session_state.ragflow_assistants_cache
            
            # Force reload of assistants
            if 'available_ragflow_assistants' in st.session_state:
                del st.session_state.available_ragflow_assistants
                
            Logger.info("Refreshed assistants list cache")
            
        except Exception as e:
            Logger.error(f"Error refreshing assistants list: {e}")
    
    def get_processing_summary(self) -> Dict[str, Any]:
        """Get summary of all upload operations."""
        operations = st.session_state.upload_operations
        
        total_ops = len(operations)
        active_ops = len(self.get_active_operations())
        completed_ops = sum(1 for op in operations.values() if op.get('status') == UploadStatus.COMPLETED.value)
        failed_ops = sum(1 for op in operations.values() if op.get('status') == UploadStatus.FAILED.value)
        
        return {
            'total_operations': total_ops,
            'active_operations': active_ops,
            'completed_operations': completed_ops,
            'failed_operations': failed_ops,
            'success_rate': (completed_ops / total_ops * 100) if total_ops > 0 else 0
        }


# Global upload manager instance
_upload_manager = None

def get_upload_manager() -> UploadManager:
    """Get the global upload manager instance."""
    global _upload_manager
    if _upload_manager is None:
        _upload_manager = UploadManager()
    return _upload_manager