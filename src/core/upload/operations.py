"""
Upload operations management.
"""

import streamlit as st
from datetime import datetime
from typing import Dict, List, Any, Optional
from .status import UploadStatus, ProcessingStage
from ...utils.logger import Logger


class UploadOperations:
    """Manages individual upload operations."""
    
    @staticmethod
    def get_active_operations() -> List[Dict[str, Any]]:
        """Get list of active (non-completed, non-failed) upload operations."""
        if 'upload_operations' not in st.session_state:
            return []
            
        active_ops = []
        for op_id, operation in st.session_state.upload_operations.items():
            status = operation.get('status')
            if status not in [UploadStatus.COMPLETED.value, UploadStatus.FAILED.value]:
                active_ops.append(operation)
        
        return active_ops
    
    @staticmethod
    def get_recent_operations(limit: int = 10) -> List[Dict[str, Any]]:
        """Get list of recent upload operations."""
        if 'upload_operations' not in st.session_state:
            return []
            
        operations = list(st.session_state.upload_operations.values())
        # Sort by creation time, most recent first
        operations.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return operations[:limit]
    
    @staticmethod
    def get_operation_status(operation_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific operation."""
        if 'upload_operations' not in st.session_state:
            return None
        return st.session_state.upload_operations.get(operation_id)
    
    @staticmethod
    def delete_operation(operation_id: str) -> bool:
        """Delete an upload operation and clean up its files."""
        if 'upload_operations' not in st.session_state:
            return False
            
        if operation_id not in st.session_state.upload_operations:
            return False
        
        try:
            # Clean up files first
            UploadOperations._cleanup_operation_files(operation_id)
            
            # Remove from session state
            del st.session_state.upload_operations[operation_id]
            Logger.info(f"Deleted upload operation {operation_id}")
            return True
            
        except Exception as e:
            Logger.error(f"Error deleting operation {operation_id}: {e}")
            return False
    
    @staticmethod
    def retry_failed_operation(operation_id: str) -> bool:
        """Manually retry a failed operation."""
        if 'upload_operations' not in st.session_state:
            return False
            
        if operation_id not in st.session_state.upload_operations:
            return False
            
        operation = st.session_state.upload_operations[operation_id]
        if operation.get('status') != UploadStatus.FAILED.value:
            return False
            
        # Reset operation for retry
        operation['status'] = UploadStatus.PENDING.value
        operation['error_message'] = None
        operation['retry_count'] = 0
        operation['last_activity'] = datetime.now().isoformat()
        
        st.session_state.upload_operations[operation_id] = operation
        Logger.info(f"Manual retry initiated for operation {operation_id}")
        
        return True
    
    @staticmethod
    def pause_operation(operation_id: str) -> bool:
        """Pause an active operation."""
        if 'upload_operations' not in st.session_state:
            return False
            
        if operation_id not in st.session_state.upload_operations:
            return False
            
        operation = st.session_state.upload_operations[operation_id]
        if operation.get('status') in [UploadStatus.COMPLETED.value, UploadStatus.FAILED.value]:
            return False
            
        operation['status'] = UploadStatus.PAUSED.value
        operation['last_activity'] = datetime.now().isoformat()
        st.session_state.upload_operations[operation_id] = operation
        
        Logger.info(f"Operation {operation_id} paused by user")
        return True
    
    @staticmethod
    def resume_operation(operation_id: str) -> bool:
        """Resume a paused operation."""
        if 'upload_operations' not in st.session_state:
            return False
            
        if operation_id not in st.session_state.upload_operations:
            return False
            
        operation = st.session_state.upload_operations[operation_id]
        if operation.get('status') != UploadStatus.PAUSED.value:
            return False
            
        operation['status'] = UploadStatus.PENDING.value
        operation['last_activity'] = datetime.now().isoformat()
        st.session_state.upload_operations[operation_id] = operation
        
        Logger.info(f"Operation {operation_id} resumed by user")
        return True
    
    @staticmethod
    def _cleanup_operation_files(operation_id: str):
        """Clean up temporary files for an operation."""
        if 'upload_operations' not in st.session_state:
            return
            
        if operation_id not in st.session_state.upload_operations:
            return
        
        operation = st.session_state.upload_operations[operation_id]
        
        for file_info in operation.get('files', []):
            temp_path = file_info.get('temp_path')
            if temp_path:
                try:
                    import os
                    # Remove the file
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                    # Try to remove the directory if empty
                    temp_dir = os.path.dirname(temp_path)
                    if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                        os.rmdir(temp_dir)
                except Exception as e:
                    Logger.warning(f"Could not clean up temporary file {temp_path}: {e}")