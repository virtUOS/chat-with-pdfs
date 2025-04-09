"""
Document management for the Chat with Docs application.
Handles document processing, storage, and retrieval.
"""

import os
import uuid
import time
import streamlit as st

from llama_index.core import Document as LlamaDocument
from llama_index.core import VectorStoreIndex, SimpleKeywordTableIndex
from llama_index.core.storage.docstore import SimpleDocumentStore


def serialize_rects(obj):
    import fitz
    if isinstance(obj, fitz.Rect):
        return [obj.x0, obj.y0, obj.x1, obj.y1]
    elif isinstance(obj, dict):
        new_obj = {}
        for k, v in obj.items():
            # Force convert known bbox keys
            if k.lower() in ('bbox', 'rect', 'clip', 'cropbox', 'mediabox') and isinstance(v, fitz.Rect):
                new_obj[k] = [v.x0, v.y0, v.x1, v.y1]
            else:
                new_obj[k] = serialize_rects(v)
        return new_obj
    elif isinstance(obj, list):
        return [serialize_rects(i) for i in obj]
    else:
        return obj

from ..utils.logger import Logger
from ..config import IMAGES_PATH, SUMMARY_MODEL
from .file_processor import FileProcessor
from .state_manager import StateManager

class DocumentManager:
    """Manages document processing, storage, and retrieval."""
    
    @staticmethod
    def process_document(uploaded_file, set_as_current=True, multi_upload=False) -> bool:
        """Process an uploaded document file.
        
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
            Logger.info(f"Processing new document: {file_name}")
            
            # Save uploaded file to temp location
            pdf_path = DocumentManager._save_uploaded_file(uploaded_file)
            
            # Process the PDF
            vector_index, keyword_index, doc_id = DocumentManager._process_pdf(pdf_path, file_name)
            
            # Create query engine
            from ..core.chat_engine import ChatEngine
            query_engine = ChatEngine.create_query_engine(
                vector_index,
                keyword_index,
                doc_id
            )
            
            # Store data for reuse using StateManager
            pdf_data = {
                'path': pdf_path,
                'vector_index': vector_index,
                'keyword_index': keyword_index,
                'doc_id': doc_id,
                'invalid': False
            }
            StateManager.store_pdf_data(file_name, pdf_data)
            
            # Store binary data for reliable access
            binary_data = FileProcessor.get_file_binary(pdf_path)
            if binary_data:
                StateManager.store_pdf_binary(file_name, binary_data)
            
            # Store query engine
            StateManager.store_query_engine(file_name, query_engine)
            
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
    def _process_pdf(pdf_path, pdf_name):
        """Process a PDF file and create indexes.
        
        Args:
            pdf_path: Path to the PDF file
            pdf_name: Name of the PDF file
            
        Returns:
            tuple: (vector_index, keyword_index, document_id)
        """
        # Generate a unique ID for this document
        pdf_id = str(uuid.uuid4())
        
        # Update file to document ID mapping
        st.session_state['file_document_id'][pdf_name] = pdf_id
        
        # Create image directory using FileProcessor
        doc_image_path = FileProcessor.create_image_directory(IMAGES_PATH, pdf_id)
        
        # Extract documents with pymupdf4llm
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

        # DEBUG: Log pymupdf4llm.to_markdown() output
        for idx, doc in enumerate(docs):
            meta = doc.get('metadata', {})
            Logger.info(f"Doc chunk {idx}: metadata keys: {list(meta.keys())}")
            Logger.info(f"Doc chunk {idx}: page metadata: {meta.get('page')}")
        # Process document and images using the refactored methods
        llama_documents = DocumentManager._process_document_content(docs, pdf_id)
        
        # Create vector and keyword indexes
        vector_index, keyword_index = DocumentManager._create_vector_database(llama_documents, pdf_id)
        
        # Generate document summary
        DocumentManager._generate_document_summary(llama_documents, pdf_id)
        
        # Generate query suggestions
        DocumentManager._generate_query_suggestions(llama_documents, pdf_id)
        
        return vector_index, keyword_index, pdf_id
    
    @staticmethod
    def _process_document_content(docs, pdf_id):
        """Process document content extracted from PDF.
        
        Args:
            docs: Document content from PDF extraction
            pdf_id: Document ID
            
        Returns:
            list: Llama index documents
        """
        import re
        import json

        Logger.debug(f"Process document {pdf_id} with {len(docs)} pages.")
        
        # Track image paths for this document
        image_paths = []
        
        # Convert to Llama Index documents
        llama_documents = []
        for document in docs:
            # DEBUG: Log chunk info
            page_num = document.get('metadata', {}).get('page')
            text_len = len(document.get('text', ''))
            preview = document.get('text', '')[:200].replace('\n', ' ')
            Logger.info(f"Chunk page: {page_num}, length: {text_len}, preview: {preview}")

            # Extract Markdown image references from text
            markdown_images = list(re.finditer(r'!\[.*?\]\((.*?)\)', document["text"]))
            image_paths_dict = {}
            image_refs = []
            
            Logger.info(f"Found {len(markdown_images)} Markdown image references in text on page {page_num}")

            for match in markdown_images:
                img_path = match.group(1).strip()
                start_offset = match.start()
                Logger.info(f"Processing image reference: {img_path}")

                # Look for caption immediately after image link
                caption = ""
                # Get text after image link
                after = document["text"][match.end():]
                # Split into lines
                lines = after.splitlines()
                caption_lines = []
                caption_started = False
                max_caption_length = 300
                skip_blank_lines = True
                for line in lines:
                    line = line.strip()
                    # Skip initial empty, ellipsis, or page number lines after image link
                    if skip_blank_lines and (not line or line == '...' or re.match(r'^\d{1,4}$', line)):
                        continue
                    skip_blank_lines = False  # stop skipping once a non-empty, non-page-number line is found
                    # Stop if empty or ellipsis line after caption started
                    if caption_started and (not line or line == '...'):
                        break
                    # Stop if new section header
                    if re.match(r'^(#|##|\s*INTRODUCTION|ABSTRACT|REFERENCES|ACKNOWLEDGMENTS)', line, re.IGNORECASE):
                        break
                    # Heuristic: caption start if matches or is short
                    if (re.match(r'^(Figure|Fig\.|Table|Diagram|Chart|Image|Photo)', line, re.IGNORECASE)
                        or (len(line) > 0 and len(line) < 200)):
                        caption_lines.append(line)
                        caption_started = True
                    elif caption_started:
                        # After caption start, append more lines
                        caption_lines.append(line)
                    # Stop if caption too long
                    if sum(len(l) for l in caption_lines) > max_caption_length:
                        break
                caption = ' '.join(caption_lines).strip()
                if caption:
                    Logger.info(f"Extracted caption: '{caption[:100]}...' on page {page_num}")
                else:
                    Logger.info(f"No caption found after image link on page {page_num}")

                image_refs.append({
                    "file_path": img_path,  # Use consistent key 'file_path'
                    "caption": caption,
                    "offset": start_offset
                })
                Logger.info(f"Added image reference with caption: '{caption}'")
                # Convert to absolute path if relative
                abs_img_path = img_path
                if not os.path.isabs(img_path):

                    abs_img_path = os.path.join(os.getcwd(), img_path)
                
                # Check if image exists
                if os.path.exists(abs_img_path) or os.path.exists(img_path):
                    # Use the absolute path if it exists, otherwise use the original path
                    path_to_use = abs_img_path if os.path.exists(abs_img_path) else img_path
                    # Add to image_paths
                    if path_to_use not in image_paths:
                        image_paths.append(path_to_use)
                        Logger.debug(f"Found image path in text: {path_to_use}")
                    
                    # Extract the image number from the filename
                    try:
                        # Pattern is usually: filename-page-index.jpg
                        idx_part = img_path.split('-')[-1].split('.')[0]
                        img_index = int(idx_part)
                        image_paths_dict[img_index] = img_path
                    except Exception as e:
                        Logger.debug(f"Error extracting image index from {img_path}: {e}")
                        # If we can't extract the index, just store by position
                        image_paths_dict[len(image_paths_dict)] = img_path
            
            # Process images to make them JSON serializable
            # Unify images and image_refs into one metadata list
            unified_images = []

            # Build a map of markdown captions by filename (basename)
            markdown_captions = {}
            for ref in image_refs:
                filename = os.path.basename(ref["file_path"])
                markdown_captions[filename] = {
                    "caption": ref.get("caption", ""),
                    "offset": ref.get("offset", -1)
                }

            # Add images from PDF metadata, assign captions if available
            if document.get("images"):
                for i, img in enumerate(document.get("images")):
                    img_entry = {}
                    for key, value in img.items():
                        img_entry[key] = value

                    # Add the file path based on the image position within the current page
                    img_path = None
                    img_position = i
                    if img_position in image_paths_dict:
                        img_path = image_paths_dict[img_position]
                    elif len(image_paths_dict) == 1:
                        img_path = list(image_paths_dict.values())[0]
                    elif image_paths_dict:
                        pass  # no match

                    if img_path:
                        if not os.path.isabs(img_path) and os.path.exists(os.path.join(os.getcwd(), img_path)):
                            img_entry['file_path'] = os.path.join(os.getcwd(), img_path)
                        else:
                            img_entry['file_path'] = img_path

                    # Assign caption if markdown reference exists for this filename
                    filename = os.path.basename(img_entry.get('file_path', ''))
                    caption_info = markdown_captions.get(filename)
                    if caption_info:
                        img_entry['caption'] = caption_info.get('caption', '')
                        img_entry['offset'] = caption_info.get('offset', -1)
                    else:
                        # Otherwise, empty caption and offset
                        img_entry['caption'] = ""
                        img_entry['offset'] = -1

                    unified_images.append(img_entry)

            # Store unified images for this page
            # Add page number to each image from document metadata
            page_num = document["metadata"].get("page")
            if page_num is not None:
                for img in unified_images:
                    img['page'] = int(page_num)
            
            # Collect all unified images from all pages
            if 'all_unified_images' not in locals():
                all_unified_images = []
            all_unified_images.extend(unified_images)
            
            try:
                images_json = json.dumps(serialize_rects(unified_images))
            except Exception as e:
                Logger.warning(f"Could not serialize unified images: {e}")
                images_json = "[]"
            
            # Create metadata
            metadata = {
                "page": int(document["metadata"].get("page")) if document["metadata"].get("page") is not None else None,
                "images": images_json,
                "toc_items": str(document.get("toc_items")),
                "title": str(document["metadata"].get("title")),
                "author": str(document["metadata"].get("author")),
                "keywords": str(document["metadata"].get("keywords")),
                "document_id": pdf_id,  # Add document ID to track which document this is from
            }
            
            # Create a Document object with just the text and the cleaned metadata
            llama_document = LlamaDocument(
                text=document["text"],
                metadata=metadata,
                text_template="Metadata: {metadata_str}\n-----\nContent: {content}",
            )
            
            llama_documents.append(llama_document)
        
        # Store the image paths for this document using StateManager
        StateManager.store_document_image_map(pdf_id, image_paths)
        Logger.info(f"Stored {len(image_paths)} image paths for document {pdf_id}")
        
        # Also store the unified image metadata with captions
        if 'all_unified_images' in locals() and all_unified_images:
            # Debug log a few of the unified images with their captions
            for i, img in enumerate(all_unified_images[:5]):  # Log first 5 images
                Logger.info(f"Unified image {i+1} before storage: path={img.get('file_path', 'None')}, "
                           f"page={img.get('page', 'None')}, caption='{img.get('caption', 'None')}'")
            
            StateManager.store_document_unified_images(pdf_id, all_unified_images)
            Logger.info(f"Stored {len(all_unified_images)} unified images with captions for document {pdf_id}")
        
        return llama_documents
    
    @staticmethod
    def _create_vector_database(documents, pdf_id):
        """Create vector and keyword indexes from documents.
        
        Args:
            documents: List of Llama Document objects
            pdf_id: Document ID
            
        Returns:
            tuple: (vector_index, keyword_index)
        """
        # Create the vector index
        vector_index = VectorStoreIndex.from_documents(
            documents,
            docstore=SimpleDocumentStore(),
            show_progress=True
        )
        
        # Create a keyword index
        keyword_index = SimpleKeywordTableIndex.from_documents(documents)
        
        return vector_index, keyword_index
    
    @staticmethod
    def _generate_document_summary(documents, pdf_id):
        """Generate and store document summary.
        
        Args:
            documents: List of Llama Document objects
            pdf_id: Document ID
        """
        try:
            Logger.info(f"Generating document summary using {SUMMARY_MODEL} model...")
            # Extract text from documents (limit to first few docs for efficiency)
            sample_docs = documents[:min(3, len(documents))]
            sample_text = "\n\n".join([doc.text for doc in sample_docs])
            
            # Limit text length to avoid token limits
            max_chars = 5000
            if len(sample_text) > max_chars:
                sample_text = sample_text[:max_chars] + "..."
            

            from ..config import OLLAMA_MODELS, OLLAMA_ENDPOINT, OLLAMA_API_KEY
            from llama_index.llms.openai import OpenAI
            try:
                from llama_index.llms.ollama import Ollama
            except ImportError:
                Ollama = None

            if SUMMARY_MODEL in OLLAMA_MODELS and Ollama is not None:
                llm = Ollama(
                    model=SUMMARY_MODEL,
                    base_url=OLLAMA_ENDPOINT,
                    api_key=OLLAMA_API_KEY or None
                )
            else:
                llm = OpenAI(model=SUMMARY_MODEL)

            from llama_index.llms.openai import OpenAI
            
            # Initialize the LLM with the summary model
            llm = OpenAI(model=SUMMARY_MODEL)
            
            # Create a prompt for summarization
            prompt = f"""
            Please provide a concise summary of the following document.
            Focus on the main topics, key findings, and overall purpose.
            Format the summary as 3-5 sentences of clear, informative text.
            
            DOCUMENT:
            {sample_text}
            
            SUMMARY:
            """
            
            # Generate the summary
            response = llm.complete(prompt)
            summary = response.text.strip()
            
            # Store the summary using StateManager
            StateManager.store_document_summary(pdf_id, summary)
            
            Logger.info(f"Generated summary for document {pdf_id}")
            
        except Exception as e:
            Logger.error(f"Failed to generate summary: {e}")
    
    @staticmethod
    def _generate_query_suggestions(documents, pdf_id):
        """Generate and store query suggestions.
        
        Args:
            documents: List of Llama Document objects
            pdf_id: Document ID
        """
        try:
            Logger.info(f"Generating query suggestions using {SUMMARY_MODEL} model...")
            # Extract text from documents (limit to first few docs for efficiency)
            sample_docs = documents[:min(3, len(documents))]
            sample_text = "\n\n".join([doc.text for doc in sample_docs])
            
            # Limit text length to avoid token limits
            max_chars = 5000
            if len(sample_text) > max_chars:
                sample_text = sample_text[:max_chars] + "..."
            
            from llama_index.llms.openai import OpenAI
            
            # Initialize the LLM with the specified model
            llm = OpenAI(model=SUMMARY_MODEL)
            
            # Create a prompt for generating queries
            prompt = f"""
            Please generate 3 interesting and diverse questions that someone might want to ask about the following document.
            Make the questions specific to the content and insightful.
            Format your response as a simple Python list with exactly 3 questions, each enclosed in quotes.
            Example format: ["Question 1?", "Question 2?", "Question 3?"]
            Do not include any other text, just the Python list.
            
            DOCUMENT:
            {sample_text}
            
            QUESTIONS:
            """
            
            # Generate the suggestions
            response = llm.complete(prompt)
            response_text = response.text.strip()
            
            # Try to parse the response to get a list of questions
            suggestions = []
            try:
                import ast
                # Try to parse as Python list
                suggestions = ast.literal_eval(response_text)
                if not isinstance(suggestions, list):
                    raise ValueError("Response is not a list")
            except Exception as parse_error:
                Logger.warning(f"Could not parse suggestions as list: {parse_error}")
                
                # Alternative parsing: extract questions using regex
                import re
                # Look for text in quotes
                quote_matches = re.findall(r'"([^"]*)"', response_text)
                if quote_matches:
                    suggestions = quote_matches[:3]
                else:
                    # If no quotes, try to extract questions by lines or question marks
                    line_matches = re.findall(r'[^\n\r.?!]+[.?!]', response_text)
                    if line_matches:
                        suggestions = [line.strip() for line in line_matches if '?' in line][:3]
            
            # Ensure we have exactly 3 questions
            if len(suggestions) > 3:
                suggestions = suggestions[:3]
            elif len(suggestions) < 3:
                # Add default questions if we don't have enough
                default_questions = [
                    "What is the main topic of this document?",
                    "What are the key findings in this document?",
                    "Summarize this document briefly."
                ]
                
                # Fill in with default questions as needed
                suggestions = suggestions + default_questions[:(3 - len(suggestions))]
            
            # Store the suggestions using StateManager
            StateManager.store_query_suggestions(pdf_id, suggestions)
            
            Logger.info(f"Generated query suggestions for document {pdf_id}")
            
        except Exception as e:
            Logger.error(f"Failed to generate query suggestions: {e}")
            # Fallback suggestions using StateManager
            fallback_suggestions = [
                "What is the main topic of this document?",
                "What are the key findings in this document?",
                "Summarize this document briefly."
            ]
            StateManager.store_query_suggestions(pdf_id, fallback_suggestions)