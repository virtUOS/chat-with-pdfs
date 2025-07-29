"""
RAGFlow-based query engine and response synthesis for the Chat with Docs application.
"""

import streamlit as st
from typing import Dict, Any, List, Optional

from ..utils.logger import Logger
from ..utils.image import get_document_images
from ..ragflow_client import create_client


class RAGFlowChatEngine:
    """Manages query processing and response generation using RAGFlow."""
    
    def __init__(self):
        """Initialize the RAGFlow chat engine."""
        self.client = create_client()
        self._ensure_chat_assistant()
    
    def _ensure_chat_assistant(self):
        """Ensure a chat assistant exists for the current dataset."""
        try:
            # Check if we have a stored chat assistant ID
            if 'ragflow_chat_id' not in st.session_state:
                dataset_id = st.session_state.get('ragflow_dataset_id')
                if not dataset_id:
                    raise Exception("No RAGFlow dataset ID found")
                
                # Try to find existing chat assistant or create new one
                assistants_response = self.client.get_chat_assistants()
                
                if assistants_response.get('code') == 0:
                    assistants = assistants_response.get('data', [])
                    
                    # Look for existing "chat-with-docs" assistant
                    existing_assistant = None
                    for assistant in assistants:
                        if assistant.get('name') == 'chat-with-docs':
                            existing_assistant = assistant
                            break
                    
                    if existing_assistant:
                        st.session_state.ragflow_chat_id = existing_assistant.get('id')
                        Logger.info(f"Using existing RAGFlow chat assistant: {existing_assistant.get('id')}")
                    else:
                        # Get the selected model for RAGFlow
                        from ..utils.ragflow_common import get_ragflow_model_for_assistant
                        selected_model = get_ragflow_model_for_assistant()
                        
                        # Create new chat assistant
                        create_response = self.client.create_chat_assistant(
                            name='chat-with-docs',
                            dataset_ids=[dataset_id],
                            llm=selected_model,
                            prompt='You are a helpful assistant that answers questions based on the provided documents. Always cite your sources and be precise in your responses.'
                        )
                        
                        if create_response.get('code') == 0:
                            assistant_data = create_response.get('data', {})
                            st.session_state.ragflow_chat_id = assistant_data.get('id')
                            Logger.info(f"Created new RAGFlow chat assistant: {assistant_data.get('id')}")
                        else:
                            raise Exception(f"Failed to create chat assistant: {create_response.get('message')}")
                else:
                    raise Exception(f"Failed to get chat assistants: {assistants_response.get('message')}")
                    
        except Exception as e:
            Logger.error(f"Error ensuring chat assistant: {str(e)}")
            raise
    
    @staticmethod
    def process_query(prompt: str, file_name: str) -> Dict[str, Any]:
        """
        Process a query and return the response with sources and images using RAGFlow.
        
        Args:
            prompt: The user query
            file_name: The name of the file to query
            
        Returns:
            Dictionary containing answer, sources, and images
        """
        try:
            Logger.info(f"Processing query for document {file_name} with RAGFlow: {prompt[:50]}...")
            
            # Initialize RAGFlow chat engine
            chat_engine = RAGFlowChatEngine()
            
            # Get chat assistant ID
            chat_id = st.session_state.get('ragflow_chat_id')
            if not chat_id:
                raise Exception("No RAGFlow chat assistant found")
            
            # Get or create session ID for this file
            session_key = f'ragflow_session_{file_name}'
            session_id = st.session_state.get(session_key)
            
            # Execute query with RAGFlow
            response = chat_engine.client.chat_completion(
                chat_id=chat_id,
                question=prompt,
                stream=False,
                session_id=session_id
            )
            
            if response.get('code') != 0:
                raise Exception(f"RAGFlow query failed: {response.get('message')}")
            
            data = response.get('data', {})
            answer = data.get('answer', '')
            reference = data.get('reference', {})
            
            # Update session ID if provided
            if data.get('session_id'):
                st.session_state[session_key] = data.get('session_id')
            
            # Process sources from RAGFlow response
            sources = RAGFlowChatEngine._process_ragflow_sources(reference)
            
            # Extract images from sources
            images = RAGFlowChatEngine._extract_images_from_ragflow_sources(
                reference, file_name
            )
            
            # Store response for future reference
            if 'document_responses' not in st.session_state:
                st.session_state['document_responses'] = {}
            
            st.session_state['document_responses'][file_name] = {
                'last_query': prompt,
                'last_response': answer,
                'answer': answer,
                'sources': sources,
                'images': images,
                'ragflow_reference': reference  # Store original RAGFlow reference
            }
            
            Logger.info(f"RAGFlow query completed successfully. Found {len(sources)} sources and {len(images)} images")
            
            return {
                'answer': answer,
                'sources': sources,
                'images': images
            }
        
        except Exception as e:
            Logger.error(f"Error processing RAGFlow query: {str(e)}")
            return {
                'answer': f"Error processing your query: {str(e)}",
                'sources': [],
                'images': []
            }
    
    @staticmethod
    def _process_ragflow_sources(reference: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process RAGFlow reference data into source format compatible with the UI.
        
        Args:
            reference: RAGFlow reference data
            
        Returns:
            List of processed source dictionaries
        """
        sources = []
        
        if not reference or not reference.get('chunks'):
            return sources
        
        chunks = reference.get('chunks', [])
        
        for i, chunk in enumerate(chunks):
            # Create a source object compatible with existing UI
            source = {
                'id': chunk.get('id', f'chunk_{i}'),
                'text': chunk.get('content', ''),
                'metadata': {
                    'page': chunk.get('page_number'),
                    'document_name': chunk.get('document_name', 'Unknown Document'),
                    'similarity': chunk.get('similarity', 0.0),
                    'chunk_id': chunk.get('id'),
                    'document_id': chunk.get('document_id')
                },
                'score': chunk.get('similarity', 0.0)
            }
            
            # Add any additional metadata from RAGFlow
            if chunk.get('positions'):
                source['metadata']['positions'] = chunk.get('positions')
            
            sources.append(source)
        
        return sources
    
    @staticmethod
    def _extract_images_from_ragflow_sources(reference: Dict[str, Any], file_name: str) -> List[Dict[str, Any]]:
        """
        Extract images from RAGFlow reference data.
        
        Args:
            reference: RAGFlow reference data
            file_name: Current file name
            
        Returns:
            List of image information dictionaries
        """
        images = []
        
        if not reference or not reference.get('chunks'):
            Logger.info("No RAGFlow chunks provided, cannot extract images")
            return images
        
        # Get the document ID for the current file
        doc_id = st.session_state.get('file_document_id', {}).get(file_name)
        if not doc_id:
            Logger.warning(f"Document ID not found for file: {file_name}")
            return images
        
        # Get all available images for this document
        available_images = get_document_images(doc_id)
        Logger.info(f"Found {len(available_images)} available images for document {doc_id}")
        
        chunks = reference.get('chunks', [])
        
        for chunk in chunks:
            try:
                # Check if chunk has image references
                chunk_content = chunk.get('content', '')
                page_number = chunk.get('page_number')
                
                # Look for images on the same page as the chunk
                if page_number and available_images:
                    page_images = [
                        img for img in available_images 
                        if img.get('page') == page_number
                    ]
                    
                    for img_info in page_images:
                        if not any(img.get('file_path') == img_info.get('file_path') for img in images):
                            images.append({
                                'file_path': img_info.get('file_path'),
                                'caption': img_info.get('caption', ''),
                                'page': page_number,
                                'chunk_id': chunk.get('id')
                            })
                            Logger.debug(f"Added image from RAGFlow chunk: {img_info.get('file_path')}")
                
                # Check for image references in chunk content
                import re
                image_refs = re.findall(r'!\[.*?\]\((.*?)\)', chunk_content)
                for img_path in image_refs:
                    if not any(img.get('file_path') == img_path for img in images):
                        images.append({
                            'file_path': img_path,
                            'caption': '',
                            'page': page_number,
                            'chunk_id': chunk.get('id')
                        })
                        Logger.debug(f"Added image from chunk content: {img_path}")
                
            except Exception as e:
                Logger.warning(f"Error processing images from RAGFlow chunk: {e}")
        
        Logger.info(f"Found {len(images)} images in RAGFlow sources")
        return images
    
    def get_chat_history(self, file_name: str) -> List[Dict[str, Any]]:
        """
        Get chat history for a specific file.
        
        Args:
            file_name: Name of the file
            
        Returns:
            List of chat history entries
        """
        session_key = f'ragflow_session_{file_name}'
        session_id = st.session_state.get(session_key)
        
        if not session_id:
            return []
        
        # RAGFlow doesn't provide direct chat history API in the current implementation
        # Return the stored chat history from session state
        return st.session_state.get('chat_history', {}).get(file_name, [])
    
    def clear_chat_history(self, file_name: str):
        """
        Clear chat history for a specific file.
        
        Args:
            file_name: Name of the file
        """
        session_key = f'ragflow_session_{file_name}'
        if session_key in st.session_state:
            del st.session_state[session_key]
        
        if file_name in st.session_state.get('chat_history', {}):
            st.session_state['chat_history'][file_name] = []
        
        Logger.info(f"Cleared chat history for file: {file_name}")