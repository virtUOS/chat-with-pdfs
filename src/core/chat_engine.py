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
        
        # Define custom refine prompt template
        CUSTOM_REFINE_PROMPT_TMPL = (
            "The original query is as follows: {query_str}\n"
            "We have provided an existing answer: {existing_answer}\n"
            "We have the opportunity to refine the existing answer "
            "(only if needed) with some more context below.\n"
            "------------\n"
            "{context_msg}\n"
            "------------\n"
            "Given the new context, refine the original answer to better "
            "answer the query. Ensure that you include citations from the new context where appropriate, "
            "and retain any relevant citations from the original answer. Citations MUST be in the format [<number>]. "
            "If the context isn't useful, return the original answer.\n"
            "Refined Answer: "
        )
        CUSTOM_REFINE_PROMPT = PromptTemplate(
            CUSTOM_REFINE_PROMPT_TMPL
        )
        prompt_template = PromptTemplate(prompt_template_str)
        
        # Create response synthesizer
        response_synthesizer = get_response_synthesizer(
            response_mode=ResponseMode.COMPACT,
            text_qa_template=prompt_template,
            refine_template=CUSTOM_REFINE_PROMPT
        )
        
        query_engine = RetrieverQueryEngine(
            retriever=retriever,
            response_synthesizer=response_synthesizer
        )

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
        if file_name not in st.session_state.query_engine:
            Logger.warning(f"Query engine not found for file: {file_name}. Attempting to re-create it.")
            vector_index = st.session_state.get('vector_index', {}).get(file_name)
            keyword_index = st.session_state.get('keyword_index', {}).get(file_name)
            doc_id = st.session_state.get('file_document_id', {}).get(file_name)
            if vector_index is not None and keyword_index is not None and doc_id is not None:
                try:
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
            from llama_index.core import Settings
            current_model = getattr(Settings.llm, 'model', 'unknown') if hasattr(Settings.llm, 'model') else str(Settings.llm)
            Logger.info(f"Executing query with model: {current_model}")
            
            query_engine = st.session_state.query_engine[file_name]
            
            if hasattr(query_engine._response_synthesizer, "_llm"):
                query_engine._response_synthesizer._llm = Settings.llm
                Logger.info(f"Using model: {getattr(Settings.llm, 'model', str(Settings.llm))} for this query")
            
            Logger.debug(f"Final prompt sent to LLM: {prompt}")
            response = query_engine.query(prompt)
            
            if hasattr(response, 'response'):
                synthesized_answer = response.response
            else:
                synthesized_answer = str(response)

            Logger.debug(f"Raw LLM response before citation extraction: {synthesized_answer[:500].replace('\n', ' ')}")

            source_nodes = []
            if hasattr(response, 'source_nodes'):
                source_nodes = response.source_nodes
            elif 'source_nodes' in dir(response):
                source_nodes = response.source_nodes

            for idx, src_with_score in enumerate(source_nodes):
                try:
                    actual_node = src_with_score.node
                    full_text = getattr(actual_node, 'text', '')
                    Logger.info(f"Retrieved source {idx} full text (len={len(full_text)}): {full_text[:500].replace('\n', ' ')}")
                except Exception as e:
                    Logger.warning(f"Error logging retrieved source text: {e}")

            for idx, src_with_score in enumerate(source_nodes):
                actual_node = src_with_score.node
                meta = getattr(actual_node, 'metadata', {})
                page = meta.get('page') if isinstance(meta, dict) else None
                text_preview = getattr(actual_node, 'text', '')[:200].replace('\n', ' ')
                Logger.info(f"Retrieved source {idx}: page {page}, length {len(getattr(actual_node, 'text', ''))}, preview: {text_preview}")

            from ..utils.source import extract_citation_indices
            import re

            original_citation_indices = extract_citation_indices(synthesized_answer)

            citation_map = {}
            for idx in original_citation_indices:
                if idx not in citation_map:
                    citation_map[idx] = len(citation_map) + 1 

            reverse_citation_map = {}
            for orig_citation_num, new_citation_num in citation_map.items():
                reverse_citation_map[new_citation_num] = orig_citation_num - 1 

            def replace_citation(match):
                orig_num = int(match.group(1))
                new_num = citation_map.get(orig_num, orig_num)
                return f"[{new_num}]"

            synthesized_answer = re.sub(r"\[(\d+)\]", replace_citation, synthesized_answer)
            
            renumbered_citations = extract_citation_indices(synthesized_answer)
            original_citations_for_filtering = [reverse_citation_map.get(c, c-1) for c in renumbered_citations] # Ensure 0-based if not in map
            Logger.info(f"Using original citation indices passed from process_query: {original_citations_for_filtering}")


            images = ChatEngine._extract_images_from_sources(source_nodes, file_name, original_citations_for_filtering)
            
            if 'document_responses' not in st.session_state:
                st.session_state['document_responses'] = {}
            if file_name not in st.session_state['document_responses']:
                st.session_state['document_responses'][file_name] = {}
            
            reverse_citation_map_str_keys = {str(k).strip(): v for k, v in reverse_citation_map.items()}

            st.session_state['document_responses'][file_name] = {
                'last_query': prompt,
                'last_response': synthesized_answer,
                'answer': synthesized_answer,
                'sources': source_nodes,
                'images': images,
                'citation_mapping': reverse_citation_map_str_keys 
            }

            return {
                'answer': synthesized_answer,
                'sources': source_nodes,
                'images': images,
                'citation_mapping': reverse_citation_map_str_keys
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
            source_nodes: Source nodes from query response (List[NodeWithScore])
            file_name: Current file name
            citation_indices: (Optional) List of original 0-based source node indices that were cited
            
        Returns:
            List of image information dictionaries
        """
        images = []
        
        if not source_nodes:
            Logger.info("No source nodes provided, cannot extract images")
            return images
        
        doc_id = st.session_state.file_document_id.get(file_name)
        if not doc_id:
            Logger.warning(f"Document ID not found for file: {file_name}")
            return images
        
        available_images = get_document_images(doc_id)
        Logger.info(f"Found {len(available_images)} available images for document {doc_id}")
        
        cited_source_objects = []
        processed_indices_for_images = set()

        if citation_indices is not None:
            Logger.info(f"Received original_citations_for_filtering: {citation_indices}")
            for original_idx in citation_indices:
                if 0 <= original_idx < len(source_nodes) and original_idx not in processed_indices_for_images:
                    cited_source_objects.append(source_nodes[original_idx])
                    processed_indices_for_images.add(original_idx)
        else: # Fallback if no specific citation_indices provided (e.g. LLM didn't cite)
            Logger.info("No specific citation_indices provided for image extraction. Will not extract images.")
            return images # Or process all source_nodes if that's desired

        Logger.info(f"Number of unique cited source objects to process for images: {len(cited_source_objects)}")
        Logger.info(f"Cited sources pages: {[getattr(s.node, 'metadata', {}).get('page') for s in cited_source_objects]}")

        if not cited_source_objects:
            Logger.info("No valid cited sources to process for images.")
            return images

        for i, source_with_score_obj in enumerate(cited_source_objects):
            source_node = source_with_score_obj.node 
            try:
                node_id = getattr(source_node, 'id_', 'N/A')
                node_text_preview = getattr(source_node, 'text', '')[:70].replace('\n', ' ')
                node_image_paths = getattr(source_node, 'metadata', {}).get('image_paths', 'Not present') # List of paths
                Logger.debug(f"  Processing cited_source_object {i} for images: ID='{node_id}', Text='{node_text_preview}...', image_paths_metadata='{node_image_paths}'")

                meta = getattr(source_node, 'metadata', {})
                images_meta_json_str = meta.get('images', '[]') if isinstance(meta, dict) else '[]'
                Logger.info(f"  Cited source node raw 'images' metadata (JSON string): {images_meta_json_str[:200]}")

                page = meta.get('page') if isinstance(meta, dict) else None
                text_content = getattr(source_node, 'text', '')
                Logger.info(f"  Processing text of cited source node (page {page}) for image markdown: '{text_content[:200].replace('\n', ' ')}...'")
            except Exception as e:
                Logger.warning(f"Error during detailed logging of cited source for image extraction: {e}")
            
            # Option 1: Extract from Markdown in text
            source_images_from_text = process_source_for_images(source_node, doc_id, available_images)
            for img_info in source_images_from_text:
                if not any(img.get('file_path') == img_info.get('file_path') for img in images):
                    images.append(img_info)
                    Logger.debug(f"Added image via markdown in text: {img_info.get('file_path')}")

            # Option 2: Extract from 'image_paths' in metadata (list of file paths)
            # This was added in document_manager.py
            if isinstance(node_image_paths, list):
                for img_path_from_meta in node_image_paths:
                    # Find this img_path in available_images_for_doc to get full metadata
                    found_in_available = False
                    for available_img_info in available_images:
                        if available_img_info.get("file_path") == img_path_from_meta:
                            if not any(img.get('file_path') == img_path_from_meta for img in images):
                                images.append(available_img_info.copy()) # Add a copy
                                Logger.debug(f"Added image via metadata 'image_paths': {img_path_from_meta}")
                            found_in_available = True
                            break
                    if not found_in_available:
                         Logger.warning(f"Image path '{img_path_from_meta}' from metadata not found in available_images for doc {doc_id}")
        
        Logger.info(f"Found {len(images)} images in total for cited sources.")
        return images