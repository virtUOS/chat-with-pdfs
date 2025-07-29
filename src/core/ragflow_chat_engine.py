"""
RAGFlow-based query engine and response synthesis for the Chat with Docs application.
"""

import streamlit as st
from typing import Dict, Any, List

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
        """Ensure a chat assistant is selected."""
        # Check if we have a selected chat assistant ID
        chat_id = st.session_state.get('ragflow_chat_id') or st.session_state.get('selected_ragflow_assistant')
        
        if not chat_id:
            raise Exception("No chat assistant selected. Please select a chat assistant from the sidebar.")
        
        # Store the chat ID for use
        st.session_state.ragflow_chat_id = chat_id
        Logger.info(f"Using selected RAGFlow chat assistant: {chat_id}")
    
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
            
            # If no session exists, create one first (like in the test script)
            if not session_id:
                Logger.info("No session found, creating new RAGFlow session...")
                init_response = chat_engine.client.chat_completion(
                    chat_id=chat_id,
                    question="",  # Empty question to initialize session
                    stream=False
                )
                
                if init_response.get('code') == 0:
                    init_data = init_response.get('data', {})
                    session_id = init_data.get('session_id')
                    if session_id:
                        st.session_state[session_key] = session_id
                        Logger.info(f"Created new RAGFlow session: {session_id}")
                    else:
                        Logger.warning("Session initialization didn't return session_id")
                else:
                    Logger.error(f"Failed to initialize RAGFlow session: {init_response.get('message')}")
            
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
            
            # Log basic response info
            Logger.info(f"RAGFlow response - Answer length: {len(answer)}, Found {len(reference.get('chunks', []))} source chunks")
            
            # Update session ID if provided
            if data.get('session_id'):
                st.session_state[session_key] = data.get('session_id')
            
            # Process sources from RAGFlow response
            sources = RAGFlowChatEngine._process_ragflow_sources(reference)
            
            # Extract images from sources
            images = RAGFlowChatEngine._extract_images_from_ragflow_sources(
                reference, file_name
            )
            
            # Create citation mapping for the UI (RAGFlow uses 0-based indexing)
            citation_mapping = {}
            for i, source in enumerate(sources):
                citation_mapping[str(i)] = i  # Map citation number to source index (0-based for RAGFlow)
            
            # Store response for future reference
            if 'document_responses' not in st.session_state:
                st.session_state['document_responses'] = {}
            
            st.session_state['document_responses'][file_name] = {
                'last_query': prompt,
                'last_response': answer,
                'answer': answer,
                'sources': sources,
                'images': images,
                'citation_mapping': citation_mapping,
                'ragflow_reference': reference  # Store original RAGFlow reference
            }
            
            Logger.info(f"RAGFlow query completed successfully. Found {len(sources)} sources and {len(images)} images")
            
            return {
                'answer': answer,
                'sources': sources,
                'images': images,
                'citation_mapping': citation_mapping
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
            # Extract page number from positions if available
            page_number = None
            positions = chunk.get('positions', [])
            if positions and len(positions) > 0:
                # First position should contain page number
                page_number = positions[0][0] if len(positions[0]) > 0 else None
            
            # Create a source object compatible with existing UI
            source = {
                'id': chunk.get('id', f'chunk_{i}'),
                'text': chunk.get('content', ''),
                'metadata': {
                    'page': page_number,
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