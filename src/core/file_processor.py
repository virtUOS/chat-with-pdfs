"""
File processing functionality for the Chat with Docs application.
Handles PDF file operations, saving and loading files from disk.
"""

import os
import time
from pathlib import Path
from typing import Optional

from ..utils.logger import Logger

class FileProcessor:
    """Handles file operations for document processing."""
    
    @staticmethod
    def ensure_dir_exists(path: str) -> None:
        """Create directory if it doesn't exist.
        
        Args:
            path: Path to the directory to create
        """
        os.makedirs(path, exist_ok=True)
    
    @staticmethod
    def save_uploaded_file(uploaded_file, directory: str = None) -> str:
        """Save an uploaded file to a temporary location.
        
        Args:
            uploaded_file: The file to save
            directory: Target directory for the saved file. If None, uses TEMP_FILES_PATH from environment.
            
        Returns:
            str: Path to the saved file
        """
        # Use environment variable if directory is not specified
        if directory is None:
            directory = os.environ.get("TEMP_FILES_PATH", "/tmp/chat-with-pdfs/temp_files")
        
        # Get absolute path for temp directory
        temp_dir = directory if os.path.isabs(directory) else os.path.join(os.getcwd(), directory)
        
        # Create directory if it doesn't exist
        FileProcessor.ensure_dir_exists(temp_dir)
        
        # Clean the filename to ensure it's valid
        clean_filename = os.path.basename(uploaded_file.name)
        
        # Create an absolute file path
        temp_file_path = os.path.join(temp_dir, clean_filename)
        
        # Check if file already exists and add timestamp if needed
        if os.path.exists(temp_file_path):
            base, ext = os.path.splitext(clean_filename)
            timestamp = int(time.time())
            clean_filename = f"{base}_{timestamp}{ext}"
            temp_file_path = os.path.join(temp_dir, clean_filename)
        
        # Write the file
        with open(temp_file_path, "wb") as f:
            f.write(uploaded_file.getvalue())
        
        # Verify file was saved correctly
        if not os.path.exists(temp_file_path):
            raise FileNotFoundError(f"Failed to save file to {temp_file_path}")
        
        Logger.info(f"Saved uploaded file to {temp_file_path}")
        return temp_file_path
    
    @staticmethod
    def get_file_binary(file_path: str) -> Optional[bytes]:
        """Get binary data from a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            bytes: Binary content of the file or None if the file doesn't exist
        """
        if not os.path.exists(file_path):
            Logger.error(f"File not found: {file_path}")
            return None
            
        try:
            with open(file_path, 'rb') as f:
                return f.read()
        except Exception as e:
            Logger.error(f"Error reading file {file_path}: {e}")
            return None
    
    @staticmethod
    def verify_file_exists(file_path: str) -> bool:
        """Check if a file exists and is accessible.
        
        Args:
            file_path: Path to the file
            
        Returns:
            bool: True if the file exists and is accessible, False otherwise
        """
        return os.path.exists(file_path) and os.access(file_path, os.R_OK)
    
    @staticmethod
    def create_image_directory(base_dir: str, identifier: str) -> str:
        """Create a directory for storing document images.
        
        Args:
            base_dir: Base directory for images
            identifier: Unique identifier for the document
            
        Returns:
            str: Path to the created directory
        """
        # Create the base directory if it doesn't exist
        FileProcessor.ensure_dir_exists(base_dir)
        
        # Create a unique directory for this document's images
        doc_image_path = os.path.join(base_dir, identifier)
        FileProcessor.ensure_dir_exists(doc_image_path)
        
        return doc_image_path
    
    @staticmethod
    def clean_up_file(file_path: str) -> bool:
        """Remove a file from the filesystem.
        
        Args:
            file_path: Path to the file to remove
            
        Returns:
            bool: True if the file was removed, False otherwise
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                Logger.info(f"Removed file: {file_path}")
                return True
            return False
        except Exception as e:
            Logger.error(f"Error removing file {file_path}: {e}")
            return False