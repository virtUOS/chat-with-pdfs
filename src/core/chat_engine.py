"""
Query engine and response synthesis for the Chat with Docs application.
"""

import streamlit as st
from typing import Dict, Any

from llama_index.core import PromptTemplate
from llama_index.core.response_synthesizers import ResponseMode, get_response_synthesizer
from llama_index.core.query_engine import RetrieverQueryEngine

from ..utils.logger import Logger
from ..utils.image import process_source_for_images, get_document_images
from ..config import CITATION_PROMPT

class ChatEngine:
    """Manages query processing and response generation."""
    
    @staticmethod
    def create_query_engine(vector_index, keyword_index, doc_id):
        """Create a query engine for a document.
        
        Args:
            vector_index: Vector store index for the document
            keyword_index: Keyword index for the document
            doc_id: Document ID
            
        Returns:
            Object: Query engine for the document
        """
        from ..custom_retriever import CustomRetriever
        
        Logger.info(f"Creating query engine for document {doc_id}")
        
        # Initialize retrievers
        vector_retriever = vector_index.as_retriever(similarity_top_k=3)
        keyword_retriever = keyword_index.as_retriever(similarity_top_k=3)
        
        # Create custom retriever that combines both methods
        retriever = CustomRetriever(
            vector_retriever=vector_retriever,
            keyword_retriever=keyword_retriever,
            mode="OR",
        )
        
        # Use citation prompt (now the default)
        prompt_template_str = CITATION_PROMPT
        
        # Convert string template to PromptTemplate
        prompt_template = PromptTemplate(prompt_template_str)
        
        # Create response synthesizer
        response_synthesizer = get_response_synthesizer(
            response_mode=ResponseMode.COMPACT,
            text_qa_template=prompt_template
            # LLM will be updated at query time, no need to set it here
        )
        
        # Note: We don't need to explicitly set the LLM here since it will be
        # updated in process_query just before execution
        
        # Create query engine
        query_engine = RetrieverQueryEngine(
            retriever=retriever,
            response_synthesizer=response_synthesizer
        )

        # Note: The LLM will be set at query time, not during engine creation

        return query_engine
    
    @staticmethod
    def process_query(prompt: str, file_name: str) -> Dict[str, Any]:
        """
        Process a query and return the response with sources and images.
        
        Args:
            prompt: The user query
            file_name: The name of the file to query
            
        Returns:
            Dictionary containing answer, sources, and images
        """
        # Check if file_name exists in the session state
        if file_name not in st.session_state.query_engine:
            Logger.warning(f"Query engine not found for file: {file_name}. Attempting to re-create it.")
            # Try to re-create the query engine if possible
            vector_index = st.session_state.get('vector_index', {}).get(file_name)
            keyword_index = st.session_state.get('keyword_index', {}).get(file_name)
            doc_id = st.session_state.get('file_document_id', {}).get(file_name)
            if vector_index is not None and keyword_index is not None and doc_id is not None:
                try:
                    # Re-create query engine with the current model settings
                    from llama_index.core import Settings
                    Logger.info(f"Re-creating query engine for file: {file_name} with model: {Settings.llm.model if hasattr(Settings.llm, 'model') else 'unknown'}")
                    query_engine = ChatEngine.create_query_engine(vector_index, keyword_index, doc_id)
                    if 'query_engine' not in st.session_state:
                        st.session_state['query_engine'] = {}
                    st.session_state['query_engine'][file_name] = query_engine
                    Logger.info(f"Successfully re-created query engine for file: {file_name}")
                except Exception as e:
                    Logger.error(f"Failed to re-create query engine for file {file_name}: {e}")
                    return {
                        'answer': f"Error: Could not re-create query engine for file: {file_name}. {e}",
                        'sources': [],
                        'images': []
                    }
            else:
                Logger.error(f"Required indices or document ID missing for file: {file_name}. Cannot re-create query engine.")
                return {
                    'answer': "Error: File not loaded or processed correctly.",
                    'sources': [],
                    'images': []
                }
        
        Logger.info(f"Processing query for document {file_name}: {prompt[:50]}...")
        
        try:
            # Log which model is being used just before executing the query
            from llama_index.core import Settings
            current_model = getattr(Settings.llm, 'model', 'unknown') if hasattr(Settings.llm, 'model') else str(Settings.llm)
            Logger.info(f"Executing query with model: {current_model}")
            
            # Get the query engine
            query_engine = st.session_state.query_engine[file_name]
            
            # Ensure the query engine is using the current LLM
            from llama_index.core import Settings
            if hasattr(query_engine._response_synthesizer, "_llm"):
                # Set the LLM directly on the response synthesizer to ensure it's using the latest
                query_engine._response_synthesizer._llm = Settings.llm
                Logger.info(f"Using model: {getattr(Settings.llm, 'model', str(Settings.llm))} for this query")
            
            # Execute query
            response = query_engine.query(prompt)
            
            # Get the answer text
            if hasattr(response, 'response'):
                synthesized_answer = response.response
            else:
                synthesized_answer = str(response)
            
            # Get source nodes if available
            source_nodes = []
            if hasattr(response, 'source_nodes'):
                source_nodes = response.source_nodes
            elif 'source_nodes' in dir(response):
                source_nodes = response.source_nodes

            # DEBUG: Log full retrieved source node text
            for idx, src in enumerate(source_nodes):
                try:
                    full_text = getattr(src, 'text', '')
                    Logger.info(f"Retrieved source {idx} full text (len={len(full_text)}): {full_text[:500].replace('\n', ' ')}")
                except Exception as e:
                    Logger.warning(f"Error logging retrieved source text: {e}")


            # DEBUG: Log retrieved source nodes
            for idx, src in enumerate(source_nodes):
                meta = getattr(src, 'metadata', {})
                page = meta.get('page') if isinstance(meta, dict) else None
                text = getattr(src, 'text', '')
                Logger.info(f"Retrieved source {idx}: page {page}, length {len(text)}, preview: {text[:200].replace('\n', ' ')}")


            # --- Citation renumbering ---
            from ..utils.source import extract_citation_indices
            import re

            # Extract all citation indices from the answer text
            original_citation_indices = extract_citation_indices(synthesized_answer)

            # Create mapping from original citation numbers to new sequential numbers
            citation_map = {}
            for idx in original_citation_indices:
                if idx not in citation_map:
                    citation_map[idx] = len(citation_map) + 1  # assign next sequential number

            # Build reverse map: new citation number -> original source node index (0-based)
            reverse_citation_map = {}
            for orig_citation_num, new_citation_num in citation_map.items():
                # orig_citation_num is 1-based original citation number (== source node index +1)
                # new_citation_num is 1-based new citation number
                reverse_citation_map[new_citation_num] = orig_citation_num - 1  # convert to 0-based index

            # Replace all citation markers in the answer text
            def replace_citation(match):
                orig_num = int(match.group(1))
                new_num = citation_map.get(orig_num, orig_num)
                return f"[{new_num}]"

            synthesized_answer = re.sub(r"\[(\d+)\]", replace_citation, synthesized_answer)
            # --- End citation renumbering ---
            
            # Map new citation numbers back to original indices for filtering
            renumbered_citations = extract_citation_indices(synthesized_answer)
            # Convert new citation numbers to original 0-based source node indices
            original_citations_for_filtering = [reverse_citation_map.get(c, c) for c in renumbered_citations]

            # Store response for future reference
            if 'document_responses' not in st.session_state:
                st.session_state['document_responses'] = {}
            if file_name not in st.session_state['document_responses']:
                st.session_state['document_responses'][file_name] = {}
            
            # Look for image references in relevant text nodes BEFORE storing the response
            images = ChatEngine._extract_images_from_sources(source_nodes, file_name, original_citations_for_filtering)
            
            # Store this response with its sources AND images
            st.session_state['document_responses'][file_name] = {
                'last_query': prompt,
                'last_response': synthesized_answer,
                'answer': synthesized_answer,  # Add 'answer' key for compatibility
                'sources': source_nodes,
                'images': images  # Add images to the stored response
            }
            
            # Convert citation mapping keys to strings and strip whitespace for consistent UI lookup
            reverse_citation_map = {str(k).strip(): v for k, v in reverse_citation_map.items()}

            # Store this response with its sources, images, and normalized citation mapping
            st.session_state['document_responses'][file_name] = {
                'last_query': prompt,
                'last_response': synthesized_answer,
                'answer': synthesized_answer,
                'sources': source_nodes,
                'images': images,
                'citation_mapping': reverse_citation_map  # Store normalized mapping
            }

            return {
                'answer': synthesized_answer,
                'sources': source_nodes,
                'images': images,
                'citation_mapping': reverse_citation_map  # Use string keys
            }
        
        except Exception as e:
            Logger.error(f"Error processing query: {str(e)}")
            return {
                'answer': f"Error processing your query: {str(e)}",
                'sources': [],
                'images': []
            }
    
    @staticmethod
    def _extract_images_from_sources(source_nodes, file_name, citation_indices=None):
        """
        Extract images from source nodes.
        
        Args:
            source_nodes: Source nodes from query response
            file_name: Current file name
            citation_indices: (Optional) List of original citation indices before renumbering
            
        Returns:
            List of image information dictionaries
        """
        images = []
        
        if not source_nodes:
            Logger.info("No source nodes provided, cannot extract images")
            return images
        
        # Get the document ID for the current file
        doc_id = st.session_state.file_document_id.get(file_name)
        if not doc_id:
            Logger.warning(f"Document ID not found for file: {file_name}")
            return images
        
        # Get all available images for this document
        available_images = get_document_images(doc_id)
        Logger.info(f"Found {len(available_images)} available images for document {doc_id}")
        
        # Determine which sources are actually cited in the response
        cited_sources = []
        cited_indices = []
        
        if citation_indices is not None:
            # Use provided original citation indices
            cited_indices = citation_indices
            Logger.info(f"Using original citation indices passed from process_query: {cited_indices}")
        else:
            # Fallback: extract from current answer text (may be renumbered, less accurate)
            if file_name in st.session_state.get('document_responses', {}):
                last_response = st.session_state['document_responses'][file_name]
                answer_text = last_response.get('answer', '')
                from ..utils.source import extract_citation_indices
                cited_indices = extract_citation_indices(answer_text)
                Logger.info(f"Extracted citation indices from answer text: {cited_indices}")
        
        # Map the citations to source indices (0-based)
        for idx in cited_indices:
            if 0 <= idx < len(source_nodes):
                cited_sources.append(source_nodes[idx])

        Logger.info(f"Cited indices: {cited_indices}")
        Logger.info(f"Number of source nodes: {len(source_nodes)}")
        Logger.info(f"Cited sources pages: {[getattr(s, 'metadata', {}).get('page') for s in cited_sources]}")

        # If no citations found, don't show any images
        if not cited_sources and cited_indices:
            Logger.info(f"No valid cited sources found for indices: {cited_indices}")
            return images
        
        # Only use cited sources for images; do not fallback to all sources
        sources_to_process = cited_sources

        # If no cited sources, return no images
        if not sources_to_process:
            Logger.info("No cited sources with images found; returning no images")
            return images

        # Process only the cited sources for images
        for i, source in enumerate(sources_to_process):
            try:
                # DEBUG: Log cited source content before image extraction
                meta = getattr(source, 'metadata', {})

                # DEBUG: Log images metadata of this cited source
                images_meta_str = meta.get('images', '') if isinstance(meta, dict) else ''
                Logger.info(f"Cited source images metadata: {images_meta_str[:500]}")

                page = meta.get('page') if isinstance(meta, dict) else None
                text = getattr(source, 'text', '')
                Logger.info(f"Processing cited source page {page}, preview: {text[:200].replace('\\n', ' ')}")
            except Exception as e:
                Logger.warning(f"Error logging cited source: {e}")
            Logger.debug(f"Processing cited source {i+1}/{len(sources_to_process)} for images")
            
            # Only use pattern matches from available images, no fallbacks
            source_images = process_source_for_images(source, doc_id, available_images)

            # Also parse images from metadata
            meta = getattr(source, 'metadata', {})
            try:
                import json
                image_meta_list = json.loads(meta.get('images', '[]')) if isinstance(meta, dict) else []
                for img_meta in image_meta_list:
                    img_path = img_meta.get('file_path') or img_meta.get('path')
                    caption = img_meta.get('caption', '')
                    if img_path and not any(img.get('file_path') == img_path for img in images):
                        images.append({
                            'file_path': img_path,
                            'caption': '' if caption.strip() == '-----' else caption,
                            'page': meta.get('page') if isinstance(meta, dict) else None
                        })
                        Logger.debug(f"Added image from metadata: {img_path}")
            except Exception as e:
                Logger.warning(f"Error parsing images metadata: {e}")

            # Add all images found for this source (avoiding duplicates)
            for img_info in source_images:
                if not any(img.get('file_path') == img_info.get('file_path') for img in images):
                    images.append(img_info)
                    Logger.debug(f"Added image: {img_info.get('file_path')}")
        
        Logger.info(f"Found {len(images)} images in source nodes")
        return images