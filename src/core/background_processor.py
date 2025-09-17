"""
Background Processor for Upload Operations

Handles background processing coordination using Streamlit-compatible patterns.
Since Streamlit doesn't support true multithreading, this uses session state
and periodic refresh patterns to simulate background processing.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Any

import streamlit as st

from .upload_manager import get_upload_manager
from ..utils.logger import Logger


class BackgroundProcessor:
    """Handles background processing of upload operations using Streamlit patterns."""
    
    def __init__(self):
        """Initialize the background processor."""
        self.upload_manager = get_upload_manager()
        self._init_session_state()
    
    def _init_session_state(self):
        """Initialize session state for background processing."""
        if 'background_processor_last_run' not in st.session_state:
            st.session_state.background_processor_last_run = datetime.now()
        
        if 'background_processor_enabled' not in st.session_state:
            st.session_state.background_processor_enabled = True
    
    def should_process(self) -> bool:
        """Check if background processing should run."""
        if not st.session_state.background_processor_enabled:
            return False
        
        # Only process every 3 seconds to avoid overwhelming the UI
        last_run = st.session_state.background_processor_last_run
        if isinstance(last_run, str):
            last_run = datetime.fromisoformat(last_run)
        
        time_since_last = datetime.now() - last_run
        return time_since_last.total_seconds() >= 3
    
    def process_operations(self) -> bool:
        """
        Process pending upload operations.
        
        Returns:
            True if any operations were processed, False if none were active
        """
        if not self.should_process():
            return False
        
        # Update last run time
        st.session_state.background_processor_last_run = datetime.now()
        
        # Get active operations
        active_operations = self.upload_manager.get_active_operations()
        
        if not active_operations:
            return False
        
        Logger.info(f"Processing {len(active_operations)} active upload operations")
        
        # Process operations
        processed_any = False
        for operation in active_operations:
            operation_id = operation['id']
            
            try:
                # Process one step of this operation
                completed = self.upload_manager.process_upload_operation(operation_id)
                processed_any = True
                
                if completed:
                    operation_status = self.upload_manager.get_operation_status(operation_id)
                    if operation_status and operation_status.get('status') == 'completed':
                        # Operation completed successfully - trigger assistant list refresh
                        self._trigger_assistant_list_refresh()
                        Logger.info(f"Upload operation {operation_id} completed successfully")
                
                # Only process one operation per call to keep UI responsive
                break
                
            except Exception as e:
                Logger.error(f"Error processing operation {operation_id}: {e}")
                self.upload_manager._mark_operation_failed(operation_id, str(e))
        
        return processed_any
    
    def _trigger_assistant_list_refresh(self):
        """Trigger a refresh of the assistant list."""
        try:
            # Clear assistant cache to force refresh
            if 'ragflow_assistants_cache' in st.session_state:
                del st.session_state.ragflow_assistants_cache
            
            if 'available_ragflow_assistants' in st.session_state:
                del st.session_state.available_ragflow_assistants
            
            # Set flag to indicate refresh needed
            st.session_state.assistants_list_needs_refresh = True
            
            Logger.info("Triggered assistant list refresh")
            
        except Exception as e:
            Logger.error(f"Error triggering assistant list refresh: {e}")
    
    def get_processing_notification(self) -> Dict[str, Any]:
        """
        Get notification information for current processing status.
        
        Returns:
            Dict with notification type, message, and details
        """
        active_operations = self.upload_manager.get_active_operations()
        recent_completed = []
        
        # Check for recently completed operations (last 30 seconds)
        cutoff_time = datetime.now() - timedelta(seconds=30)
        
        for operation in self.upload_manager.get_recent_operations(limit=10):
            if operation.get('status') == 'completed':
                completed_at = operation.get('completed_at')
                if completed_at:
                    if isinstance(completed_at, str):
                        completed_at = datetime.fromisoformat(completed_at)
                    if completed_at > cutoff_time:
                        recent_completed.append(operation)
        
        # Prioritize notifications
        if recent_completed:
            # Show completion notification
            operation = recent_completed[0]  # Most recent
            return {
                'type': 'success',
                'title': '🎉 Assistant Ready!',
                'message': f"Your assistant '{operation.get('assistant_name')}' is ready to use!",
                'action': 'refresh_assistants'
            }
        
        elif active_operations:
            # Show processing notification
            total_files = sum(len(op.get('files', [])) for op in active_operations)
            return {
                'type': 'info',
                'title': '🔄 Processing Documents',
                'message': f"Processing {total_files} documents in {len(active_operations)} operation(s)...",
                'action': 'show_status'
            }
        
        else:
            return {'type': 'none'}
    
    def enable_processing(self):
        """Enable background processing."""
        st.session_state.background_processor_enabled = True
    
    def disable_processing(self):
        """Disable background processing."""
        st.session_state.background_processor_enabled = False
    
    def cleanup_old_operations(self, max_age_hours: int = 24):
        """Clean up old completed/failed operations."""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        operations_to_remove = []
        
        for op_id, operation in st.session_state.upload_operations.items():
            created_at = operation.get('created_at')
            if created_at:
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at)
                
                if created_at < cutoff_time and operation.get('status') in ['completed', 'failed']:
                    operations_to_remove.append(op_id)
        
        for op_id in operations_to_remove:
            self.upload_manager.delete_operation(op_id)
            Logger.info(f"Cleaned up old operation {op_id}")
        
        if operations_to_remove:
            Logger.info(f"Cleaned up {len(operations_to_remove)} old operations")


# Global background processor instance
_background_processor = None

def get_background_processor() -> BackgroundProcessor:
    """Get the global background processor instance."""
    global _background_processor
    if _background_processor is None:
        _background_processor = BackgroundProcessor()
    return _background_processor


def process_background_operations() -> bool:
    """
    Convenience function to process background operations.
    Call this in UI components that need to trigger background processing.
    
    Returns:
        True if any operations were processed
    """
    processor = get_background_processor()
    return processor.process_operations()


def render_processing_notification() -> None:
    """Render processing notifications in the UI."""
    processor = get_background_processor()
    notification = processor.get_processing_notification()
    
    if notification.get('type') == 'success':
        st.success(f"**{notification.get('title')}**\n\n{notification.get('message')}")
        
        # Auto-refresh assistants if needed
        if notification.get('action') == 'refresh_assistants':
            if st.button("🔄 Refresh Assistant List", key="refresh_assistants_btn"):
                processor._trigger_assistant_list_refresh()
                st.rerun()
    
    elif notification.get('type') == 'info':
        st.info(f"**{notification.get('title')}**\n\n{notification.get('message')}")
    
    # Let the upload status panel handle the rerun logic
    # Don't automatically rerun here to avoid infinite loops