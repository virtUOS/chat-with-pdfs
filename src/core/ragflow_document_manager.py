"""
RAGFlow-based document management for the Chat with Docs application.
Handles document processing, storage, and retrieval using RAGFlow API.
"""

import os
import uuid
import time
import streamlit as st
import fitz  # PyMuPDF

from ..config import IMAGES_PATH
from ..utils.logger import Logger
from ..utils.i18n import I18n
from .file_processor import FileProcessor
from .state_manager import StateManager
from ..ragflow_client import create_client


class RAGFlowDocumentManager:
    """Manages document processing, storage, and retrieval using RAGFlow."""
    
    def __init__(self):
        """Initialize the RAGFlow document manager."""
        self.client = create_client()
        self._ensure_default_dataset()
    
    def _ensure_default_dataset(self):
        """Ensure a default dataset exists for the application."""
        try:
            # Check if we have a stored dataset ID
            if 'ragflow_dataset_id' not in st.session_state:
                # Try to find existing dataset or create new one
                datasets_response = self.client.get_datasets()
                
                if datasets_response.get('code') == 0:
                    datasets = datasets_response.get('data', [])
                    
                    # Look for existing "chat-with-docs" dataset
                    existing_dataset = None
                    for dataset in datasets:
                        if dataset.get('name') == 'chat-with-docs':
                            existing_dataset = dataset
                            break
                    
                    if existing_dataset:
                        st.session_state.ragflow_dataset_id = existing_dataset.get('id')
                        Logger.info(f"Using existing RAGFlow dataset: {existing_dataset.get('id')}")
                    else:
                        # Create new dataset
                        create_response = self.client.create_dataset(
                            name='chat-with-docs',
                            description='Default dataset for Chat with Docs application',
                            embedding_model='BAAI/bge-large-en-v1.5',
                            chunk_method='naive'
                        )
                        
                        if create_response.get('code') == 0:
                            dataset_data = create_response.get('data', {})
                            st.session_state.ragflow_dataset_id = dataset_data.get('id')
                            Logger.info(f"Created new RAGFlow dataset: {dataset_data.get('id')}")
                        else:
                            raise Exception(f"Failed to create dataset: {create_response.get('message')}")
                else:
                    raise Exception(f"Failed to get datasets: {datasets_response.get('message')}")
                    
        except Exception as e:
            Logger.error(f"Error ensuring default dataset: {str(e)}")
            raise
    
    @staticmethod
    def process_document(uploaded_file, set_as_current=True, multi_upload=False) -> bool:
        """Process an uploaded document file using RAGFlow.
        
        Args:
            uploaded_file: The file to process
            set_as_current: If True, set this file as the current file
            multi_upload: Whether this is part of a multi-file upload
            
        Returns:
            bool: True if processing was successful, False otherwise
        """
        if not uploaded_file:
            return False
        
        # Initialize file queue tracking if not exists
        if 'file_queue' not in st.session_state:
            st.session_state.file_queue = []
        
        # Record file upload interaction
        file_name = uploaded_file.name
        st.session_state.last_uploaded_file_name = file_name
        st.session_state.last_upload_timestamp = str(int(time.time()))
        
        # Check if file is already processed
        if file_name in StateManager.get_processed_files():
            if set_as_current:
                StateManager.set_current_file(file_name)
            return True
        
        # Process new file
        try:
            Logger.info(f"Processing new document with RAGFlow: {file_name}")
            
            # Initialize RAGFlow document manager
            ragflow_manager = RAGFlowDocumentManager()
            
            # Save uploaded file to temp location
            pdf_path = RAGFlowDocumentManager._save_uploaded_file(uploaded_file)
            
            # Process the PDF with RAGFlow
            doc_id = RAGFlowDocumentManager._process_pdf_with_ragflow(
                ragflow_manager, pdf_path, file_name
            )
            
            # Store data for reuse using StateManager
            pdf_data = {
                'path': pdf_path,
                'ragflow_doc_id': doc_id,
                'dataset_id': st.session_state.ragflow_dataset_id,
                'invalid': False
            }
            StateManager.store_pdf_data(file_name, pdf_data)
            
            # Store binary data for reliable access
            binary_data = FileProcessor.get_file_binary(pdf_path)
            if binary_data:
                StateManager.store_pdf_binary(file_name, binary_data)
            
            # Initialize chat history for this file
            if file_name not in st.session_state.chat_history:
                st.session_state.chat_history[file_name] = []
            
            # Store the name of the processed file
            if "last_processed_files" not in st.session_state:
                st.session_state["last_processed_files"] = []
            st.session_state["last_processed_files"].append(file_name)
            
            # Set as current file if requested
            if set_as_current or not StateManager.get_current_file():
                StateManager.set_current_file(file_name)
            
            # Add file name to processed files set
            st.session_state.processed_files.add(file_name)
            
            # Store the complete state before rerunning
            st.session_state.file_processed = True
            
            # Update processing status
            if file_name in st.session_state.get('file_processing_status', {}):
                st.session_state.file_processing_status[file_name]['processing_time'] = (
                    time.time() - st.session_state.file_processing_status[file_name].get('started_at', time.time())
                )
                st.session_state.file_processing_status[file_name]['status'] = 'completed'
            
            # For multi-uploads, store success
            if multi_upload:
                if 'multi_upload_results' not in st.session_state:
                    st.session_state.multi_upload_results = {'success': [], 'failed': []}
                st.session_state.multi_upload_results['success'].append(file_name)
            
            return True
            
        except Exception as e:
            Logger.error(f"Error processing file {file_name}: {str(e)}")
            
            # Store error information
            if "display_errors" not in st.session_state:
                st.session_state["display_errors"] = {}
            st.session_state["display_errors"][file_name] = str(e)
            
            # Update processing status
            if file_name in st.session_state.get('file_processing_status', {}):
                st.session_state.file_processing_status[file_name]['status'] = 'failed'
                st.session_state.file_processing_status[file_name]['error'] = str(e)
            
            # For multi-uploads, track failures
            if multi_upload:
                if 'multi_upload_results' not in st.session_state:
                    st.session_state.multi_upload_results = {'success': [], 'failed': []}
                st.session_state.multi_upload_results['failed'].append({
                    'name': file_name,
                    'error': str(e)
                })
            
            # Clean up the file if processing failed
            if 'pdf_path' in locals() and os.path.exists(pdf_path):
                os.remove(pdf_path)
                
            return False
    
    @staticmethod
    def _save_uploaded_file(uploaded_file):
        """Save an uploaded file to a temporary location.
        
        Args:
            uploaded_file: The file to save
            
        Returns:
            str: Path to the saved file
        """
        # Use the FileProcessor to save the uploaded file
        return FileProcessor.save_uploaded_file(uploaded_file)
    
    @staticmethod
    def _process_pdf_with_ragflow(ragflow_manager, pdf_path, pdf_name):
        """Process a PDF file using RAGFlow.
        
        Args:
            ragflow_manager: RAGFlowDocumentManager instance
            pdf_path: Path to the PDF file
            pdf_name: Name of the PDF file
            
        Returns:
            str: Document ID from RAGFlow
        """
        # Generate a unique ID for this document
        pdf_id = str(uuid.uuid4())
        
        # Update file to document ID mapping
        st.session_state['file_document_id'][pdf_name] = pdf_id
        
        # Create image directory using FileProcessor
        doc_image_path = FileProcessor.create_image_directory(IMAGES_PATH, pdf_id)
        
        # Extract documents with pymupdf4llm for OCR analysis
        import pymupdf4llm
        docs = pymupdf4llm.to_markdown(
            doc=pdf_path,
            write_images=True,
            image_path=doc_image_path,
            image_format="jpg",
            dpi=200,
            page_chunks=True,
            extract_words=True
        )

        # RAGFlow handles OCR analysis internally, no need for custom OCR analysis
        
        # Upload document to RAGFlow
        try:
            upload_response = ragflow_manager.client.upload_document(
                dataset_id=st.session_state.ragflow_dataset_id,
                file_path=pdf_path
            )
            
            if upload_response.get('code') == 0:
                ragflow_doc_data = upload_response.get('data', {})
                ragflow_doc_id = ragflow_doc_data.get('id')
                
                Logger.info(f"Successfully uploaded document to RAGFlow: {ragflow_doc_id}")
                
                # Store RAGFlow document ID mapping
                if 'ragflow_document_mapping' not in st.session_state:
                    st.session_state.ragflow_document_mapping = {}
                st.session_state.ragflow_document_mapping[pdf_name] = ragflow_doc_id
                
                return ragflow_doc_id
            else:
                raise Exception(f"RAGFlow upload failed: {upload_response.get('message')}")
                
        except Exception as e:
            Logger.error(f"Error uploading to RAGFlow: {str(e)}")
            raise
    
    def get_dataset_id(self):
        """Get the current dataset ID."""
        return st.session_state.get('ragflow_dataset_id')
    
    def get_documents(self):
        """Get all documents in the current dataset."""
        try:
            dataset_id = self.get_dataset_id()
            if not dataset_id:
                return []
            
            response = self.client.get_documents(dataset_id)
            if response.get('code') == 0:
                return response.get('data', [])
            else:
                Logger.error(f"Failed to get documents: {response.get('message')}")
                return []
        except Exception as e:
            Logger.error(f"Error getting documents: {str(e)}")
            return []
    
    def delete_document(self, document_id: str):
        """Delete a document from RAGFlow."""
        try:
            dataset_id = self.get_dataset_id()
            if not dataset_id:
                return False
            
            response = self.client.delete_documents(dataset_id, [document_id])
            if response.get('code') == 0:
                Logger.info(f"Successfully deleted document: {document_id}")
                return True
            else:
                Logger.error(f"Failed to delete document: {response.get('message')}")
                return False
        except Exception as e:
            Logger.error(f"Error deleting document: {str(e)}")
            return False