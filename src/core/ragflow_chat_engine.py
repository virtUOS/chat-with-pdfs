"""
RAGFlow-based query engine and response synthesis for the Chat with Docs application.
"""
import re
import time

import streamlit as st
from typing import Dict, Any, List

from ..utils.logger import Logger
from ..utils.image import get_document_images
from ..ragflow_client import create_client
from ..utils.prompts import PromptTemplates


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
    def process_query(prompt: str, file_name: str, store_for_annotations: bool = True) -> Dict[str, Any]:
        """
        Process a query and return the response with sources and images using RAGFlow.
        
        Args:
            prompt: The user query
            file_name: The name of the file to query
            store_for_annotations: Whether to store response in document_responses for annotations (default: True)
            
        Returns:
            Dictionary containing answer, sources, and images
        """
        try:
            Logger.info(f"Processing query for document {file_name} with RAGFlow: {prompt[:50]}...")
            
            # Use document scoping approach with proper prompt templates
            scoped_prompt = PromptTemplates.get_document_scoping_prompt().format(doc_name=file_name, question=prompt)
            Logger.info(f"Scoped query: {scoped_prompt[:100]}...")
            
            # Initialize RAGFlow chat engine
            chat_engine = RAGFlowChatEngine()
            
            # Get chat assistant ID
            chat_id = st.session_state.get('ragflow_chat_id')
            if not chat_id:
                raise Exception("No RAGFlow chat assistant found")
            
            # Use session management only for user queries (store_for_annotations=True)
            # Skip session management for suggestions and summaries to avoid context issues
            session_key = f'ragflow_session_{file_name}'
            session_id = None
            
            if store_for_annotations:
                # For user queries, try to maintain session continuity
                session_id = st.session_state.get(session_key)
                Logger.info(f"User query using session: {session_id or 'None (will create new)'}")
            else:
                # For suggestions and summaries, always use fresh sessions
                Logger.info("Using fresh session for suggestions/summary (no session management)")
            
            # Language analysis for cross-language debugging
            def detect_language_hints(text):
                """Simple language detection based on common words."""
                text_lower = text.lower()
                german_indicators = ['der', 'die', 'das', 'und', 'oder', 'ist', 'sind', 'haben', 'werden', 'können', 'soll', 'wird', 'wurde', 'dass', 'wenn', 'aber', 'auch', 'nicht', 'nur', 'noch', 'mehr', 'sehr', 'nach', 'beim', 'zwischen', 'unterschied', 'unterschiede', 'welche', 'warum', 'wie', 'inwiefern']
                english_indicators = ['the', 'and', 'or', 'is', 'are', 'have', 'will', 'can', 'should', 'was', 'that', 'if', 'but', 'also', 'not', 'only', 'more', 'very', 'after', 'between', 'difference', 'differences', 'which', 'why', 'how']
                
                german_score = sum(1 for word in german_indicators if word in text_lower)
                english_score = sum(1 for word in english_indicators if word in text_lower)
                
                if german_score > english_score and german_score > 0:
                    return 'likely_german'
                elif english_score > german_score and english_score > 0:
                    return 'likely_english'
                else:
                    return 'unclear'
            
            query_language = detect_language_hints(prompt)
            scoped_query_language = detect_language_hints(scoped_prompt)
            
            # Log detailed request information for debugging
            request_info = {
                'chat_id': chat_id,
                'session_id': session_id,
                'prompt_length': len(scoped_prompt),
                'original_prompt_length': len(prompt),
                'file_name': file_name,
                'store_for_annotations': store_for_annotations,
                'query_language_hint': query_language,
                'scoped_query_language_hint': scoped_query_language,
                'contains_german_chars': any(char in prompt for char in 'äöüßÄÖÜ'),
                'ui_language': st.session_state.get('language', 'unknown')
            }
            Logger.info(f"RAGFlow request details: {request_info}")
            
            # Execute query with RAGFlow using the scoped prompt
            start_time = time.time()
            
            # Execute query without session management to avoid context issues
            response = chat_engine.client.chat_completion(
                chat_id=chat_id,
                question=scoped_prompt,
                stream=False
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            if response.get('code') != 0:
                raise Exception(f"RAGFlow query failed: {response.get('message')}")
            
            data = response.get('data', {})
            answer = data.get('answer', '')
            reference = data.get('reference', {})
            
            # Clean up answer by removing RAGFlow fallback messages ONLY if there's substantial content before it
            if answer:
                fallback_message = "The answer you are looking for is not found in the knowledge base!"
                
                # Check if the answer contains the fallback message
                if fallback_message in answer:
                    # Split the answer at the fallback message
                    parts = answer.split(fallback_message)
                    if len(parts) > 1:
                        # Get the content before the fallback message
                        content_before = parts[0].strip()
                        
                        # Only remove the fallback if there's substantial content (more than just whitespace/newlines)
                        if content_before and len(content_before) > 10:  # Arbitrary threshold for "substantial"
                            answer = content_before
                            Logger.info(f"Removed RAGFlow fallback message, kept substantial content ({len(content_before)} chars)")
                        # If there's no substantial content before the fallback, keep the original answer
            
            # Enhanced logging with more diagnostic information
            Logger.warning(f"RAGFlow RAW response: {response}")
            chunks = reference.get('chunks') or []  # Handle None case
            Logger.info(f"RAGFlow response - Answer length: {len(answer)}, Found {len(chunks)} source chunks, Response time: {response_time:.2f}s")
            Logger.info(f"RAGFlow response keys: {list(data.keys())}")
            Logger.info(f"Reference keys: {list(reference.keys()) if reference else 'No reference object'}")
            
            # Enhanced citation and reference analysis
            from ..utils.citations import extract_citation_indices
            citation_ids = [str(cid) for cid in extract_citation_indices(answer)]
            citation_matches = citation_ids  # For backwards compatibility with logging
            has_citations = len(citation_ids) > 0
            has_chunks = len(chunks) > 0
            
            # Log citation analysis
            Logger.info(f"Citation analysis: Found {len(citation_ids)} unique citations: {citation_ids}")
            Logger.info(f"Total citation occurrences: {len(citation_matches)}")
            
            # Log detailed response structure for diagnostic purposes
            Logger.info(f"Response data structure analysis:")
            Logger.info(f"  - Session ID in response: {data.get('session_id', 'Not provided')}")
            Logger.info(f"  - Answer contains newlines: {'Yes' if '\\n' in answer else 'No'}")
            Logger.info(f"  - Reference type: {type(reference)}")
            Logger.info(f"  - Reference is empty dict: {reference == {}}")
            
            if has_citations and not has_chunks:
                Logger.warning(f"RAGFlow inconsistency: Answer contains {len(citation_ids)} citations but no chunks provided")
                Logger.warning(f"Citations found: {citation_ids}")
                Logger.warning(f"LANGUAGE ANALYSIS - Query: {query_language}, UI: {request_info['ui_language']}, German chars: {request_info['contains_german_chars']}")
                Logger.info(f"Full RAGFlow response structure:")
                Logger.info(f"  - response keys: {list(response.keys()) if isinstance(response, dict) else 'Not a dict'}")
                Logger.info(f"  - data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                Logger.info(f"  - reference data: {reference}")
                Logger.info(f"  - prompt length: {len(scoped_prompt)}")
                Logger.info(f"  - session_id used: {session_id}")
                Logger.info(f"  - original prompt: {prompt[:100]}...")
                Logger.info(f"Answer with citations: {answer[:300]}...")
            elif not has_citations and not has_chunks:
                Logger.info(f"RAGFlow provided answer without retrieval (no citations, no chunks)")
                Logger.info(f"Answer length: {len(answer)}")
            elif has_citations and has_chunks:
                Logger.info(f"RAGFlow working correctly: {len(chunks)} chunks with {len(citation_ids)} unique citations")
                # Log chunk information for successful cases
                chunk_info = []
                for i, chunk in enumerate(chunks[:3]):  # First 3 chunks only
                    chunk_info.append({
                        'chunk_id': chunk.get('id', 'No ID'),
                        'content_length': len(chunk.get('content', '')),
                        'doc_name': chunk.get('document_name', 'Unknown'),
                        'similarity': chunk.get('similarity', 'N/A')
                    })
                Logger.info(f"Sample chunk info: {chunk_info}")
            else:
                Logger.warning(f"RAGFlow unusual case: {len(chunks)} chunks without citations")
            
            # Store session ID only for user queries to maintain document context
            response_session_id = data.get('session_id')
            if response_session_id and store_for_annotations:
                # Only store session for user queries, not suggestions/summaries
                st.session_state[session_key] = response_session_id
                Logger.info(f"Stored session ID for user queries: {response_session_id}")
            else:
                Logger.info(f"RAGFlow session ID (not stored): {response_session_id}")
            
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
            
            # Store response for future reference (only if store_for_annotations is True)
            if store_for_annotations:
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
    