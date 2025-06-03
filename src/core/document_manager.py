"""
Document management for the Chat with Docs application.
Handles document processing, storage, and retrieval.
"""

import os
import uuid
import time
import re
import fitz
import json
import streamlit as st

from llama_index.core import Document as LlamaDocument
from llama_index.core import VectorStoreIndex, SimpleKeywordTableIndex
from llama_index.core.storage.docstore import SimpleDocumentStore


def serialize_rects(obj):
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
from ..config import IMAGES_PATH, SUMMARY_MODEL, DEFAULT_CHUNK_OVERLAP
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
            # Check for words in the document output
            Logger.info(f"Doc chunk {idx} keys: {list(doc.keys())}")
            if 'words' in doc:
                Logger.info(f"Doc chunk {idx}: has {len(doc['words'])} words")
                if len(doc['words']) > 0:
                    Logger.info(f"Word data format sample: {doc['words'][0]}")
            else:
                Logger.info(f"Doc chunk {idx}: No 'words' key found")
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
    def _chunk_document_text(text, chunk_size, chunk_overlap, original_metadata, words_data=None):
        """
        Split document text into chunks while preserving word boundaries,
        tracking image references, and calculating chunk bounding boxes.
        """

        # Log input values
        Logger.debug(f"Chunking document text: {len(text)} chars, target size={chunk_size}, overlap={chunk_overlap}")
        if words_data:
            Logger.debug(f"Received {len(words_data)} word items for bbox calculation.")
        else:
            Logger.debug("No word data received for bbox calculation.")

        # Extract image references from text
        image_references = list(re.finditer(r'!\[.*?\]\((.*?)\)', text))
        Logger.debug(f"Found {len(image_references)} image references in document")

        # Split text into words (tokens for chunking)
        text_tokens = re.findall(r'\S+|\s+', text)
        
        chunks = []
        current_chunk_tokens = []
        current_chunk_word_data = [] # Store corresponding word data for bbox
        current_length = 0
        chunk_start_offset_chars = 0 # Character offset in the original page text
        
        # Track which image references are in which chunk
        current_chunk_images = []
        
        word_data_idx = 0 # To iterate through words_data

        for token_idx, token in enumerate(text_tokens):
            # Try to match token with words_data for bbox
            token_word_data = None
            if token.strip() and words_data: # Only process if token is not just whitespace
                # Simple sequential matching. This assumes text_tokens and words_data are somewhat aligned.
                # A more robust matching might be needed if they diverge significantly.
                temp_idx = word_data_idx
                # Logger.debug(f"Attempting to match token: '{token}' (stripped: '{token.strip()}') starting from words_data index {word_data_idx}")
                while temp_idx < len(words_data):
                    word_from_data = words_data[temp_idx][4].strip()
                    # Logger.debug(f"  Comparing with word_data[{temp_idx}]: '{word_from_data}'")
                    if word_from_data == token.strip(): # Compare stripped text
                        token_word_data = words_data[temp_idx]
                        # Logger.debug(f"    Exact match found: {token_word_data}")
                        word_data_idx = temp_idx + 1 # Move to next word_data for next token
                        break
                    elif token.strip() in word_from_data: # Token is part of word_data
                        token_word_data = words_data[temp_idx]
                        # Logger.debug(f"    Partial match (token in word_data): {token_word_data}")
                        # Don't advance word_data_idx yet, next token might be part of same word_data
                        break
                    # Optimization: if current token is much shorter than word_from_data, it's unlikely to be found further if not a substring
                    # elif len(token.strip()) < len(word_from_data) and not word_from_data.startswith(token.strip()):
                    #    pass # continue search
                    temp_idx += 1
                
                # if not token_word_data and token.strip():
                #     Logger.debug(f"Token '{token.strip()}' not matched with any word_data entry.")
            # elif not token.strip():
                # Logger.debug(f"Skipping word_data match for whitespace token: '{token}'")


            # Check if adding this token would exceed chunk size
            if current_length + len(token) > chunk_size and current_length > 0:
                # Complete current chunk
                chunk_text = ''.join(current_chunk_tokens)
                
                # Create metadata for this chunk, copy from original
                chunk_metadata = original_metadata.copy()
                
                # Calculate chunk_bbox
                chunk_bbox = None
                if current_chunk_word_data:
                    # Union of all bboxes in current_chunk_word_data
                    final_rect = fitz.Rect() # Empty rect
                    for wd in current_chunk_word_data:
                        try:
                            # wd[0:4] are x0, y0, x1, y1
                            word_rect = fitz.Rect(wd[0], wd[1], wd[2], wd[3])
                            if final_rect.is_empty:
                                final_rect = word_rect
                            else:
                                final_rect.include_rect(word_rect)
                        except Exception as e:
                            Logger.warning(f"Could not form Rect from word data {wd}: {e}")
                    if not final_rect.is_empty:
                         chunk_bbox = [final_rect.x0, final_rect.y0, final_rect.x1, final_rect.y1]

                chunk_metadata.update({
                    "chunk_start_offset": chunk_start_offset_chars,
                    "chunk_end_offset": chunk_start_offset_chars + len(chunk_text),
                    "is_partial_page": True,
                    "chunk_bbox": chunk_bbox
                })
                
                # Add to chunks list
                chunks.append({
                    "text": chunk_text,
                    "metadata": chunk_metadata,
                    "images": current_chunk_images.copy()  # Create a copy
                })
                
                # Start new chunk with overlap
                # Calculate overlap in terms of tokens
                approx_chars_per_token = current_length / len(current_chunk_tokens) if current_chunk_tokens else 1
                overlap_token_count = int(chunk_overlap / approx_chars_per_token) if approx_chars_per_token > 0 else 0
                
                overlap_start_token_idx = max(0, len(current_chunk_tokens) - overlap_token_count)

                # Recalculate character offset for the new chunk based on tokens kept for overlap
                new_chunk_start_offset_chars = chunk_start_offset_chars
                for i in range(overlap_start_token_idx):
                    new_chunk_start_offset_chars += len(current_chunk_tokens[i])

                current_chunk_tokens = current_chunk_tokens[overlap_start_token_idx:]
                current_chunk_word_data = current_chunk_word_data[overlap_start_token_idx:] # Align word data with tokens
                current_length = sum(len(w) for w in current_chunk_tokens)
                chunk_start_offset_chars = new_chunk_start_offset_chars
                
                # Update images for new chunk
                current_chunk_images = [img for img in current_chunk_images
                                      if img["offset"] >= chunk_start_offset_chars]
            
            # Add token to current chunk
            current_chunk_tokens.append(token)
            if token_word_data:
                current_chunk_word_data.append(token_word_data)
            current_length += len(token)
            
            # Check if this token contains or completes an image reference
            # Image offset is relative to the start of the page text
            token_end_char_offset_in_page = chunk_start_offset_chars + current_length
            
            for img_ref in image_references:
                if (chunk_start_offset_chars <= img_ref.start() < token_end_char_offset_in_page and
                    not any(img["offset"] == img_ref.start() for img in current_chunk_images)):
                    # This image reference starts within the current token's span in the page
                    img_path = img_ref.group(1).strip()
                    current_chunk_images.append({
                        "file_path": img_path,
                        "offset": img_ref.start(), # Store original offset from page start
                        "page": original_metadata.get("page")
                    })
                    Logger.debug(f"Added image {img_path} to chunk at offset {img_ref.start()}")
        
        # Don't forget the last chunk
        if current_chunk_tokens:
            chunk_text = ''.join(current_chunk_tokens)
            chunk_metadata = original_metadata.copy()

            chunk_bbox = None
            if current_chunk_word_data:
                final_rect = fitz.Rect()
                for wd in current_chunk_word_data:
                    try:
                        word_rect = fitz.Rect(wd[0], wd[1], wd[2], wd[3])
                        if final_rect.is_empty:
                            final_rect = word_rect
                        else:
                            final_rect.include_rect(word_rect)
                    except Exception as e:
                        Logger.warning(f"Could not form Rect from word data {wd} for last chunk: {e}")
                if not final_rect.is_empty:
                    chunk_bbox = [final_rect.x0, final_rect.y0, final_rect.x1, final_rect.y1]
            
            chunk_metadata.update({
                "chunk_start_offset": chunk_start_offset_chars,
                "chunk_end_offset": chunk_start_offset_chars + len(chunk_text),
                "is_partial_page": True,
                "chunk_bbox": chunk_bbox
            })
            
            chunks.append({
                "text": chunk_text,
                "metadata": chunk_metadata,
                "images": current_chunk_images
            })
        
        Logger.debug(f"Chunking completed: Document split into {len(chunks)} chunks")
        return chunks
    
    @staticmethod
    def _process_document_content(docs, pdf_id):
        """Process document content extracted from PDF with configurable chunk sizes.
        
        Args:
            docs: Document content from PDF extraction
            pdf_id: Document ID
            
        Returns:
            list: Llama index documents
        """

        # Get configured chunk size from state manager
        chunk_size = StateManager.get_chunk_size()
        chunk_overlap = DEFAULT_CHUNK_OVERLAP
        
        Logger.debug(f"Processing document {pdf_id} with {len(docs)} pages.")
        Logger.debug(f"Using chunk_size={chunk_size}, chunk_overlap={chunk_overlap}")
        
        # Track image paths for this document
        image_paths = []
        
        # Track all unified images across pages
        all_unified_images = []
        
        # Convert to Llama Index documents
        llama_documents = []
        for document in docs:
            # DEBUG: Log chunk info
            page_num = document.get('metadata', {}).get('page')
            text_len = len(document.get('text', ''))
            preview = document.get('text', '')[:50].replace('\n', ' ')
            Logger.info(f"Document page: {page_num}, length: {text_len}, preview: {preview}")
            
            # Determine if chunking is needed for this page
            if text_len > chunk_size:
                # Need to split the page into chunks
                Logger.debug(f"Chunking page {page_num}: {text_len} chars > {chunk_size} threshold")
                
                # Extract Markdown image references once from the original document
                image_paths_dict = {}
                image_refs = []
                markdown_images = list(re.finditer(r'!\[.*?\]\((.*?)\)', document["text"]))
                Logger.info(f"Found {len(markdown_images)} Markdown image references on page {page_num} before chunking")
                
                # Process all image references from the original document
                for match in markdown_images:
                    img_path = match.group(1).strip()
                    start_offset = match.start()
                    
                    # Look for caption immediately after image link
                    caption = ""
                    after = document["text"][match.end():]
                    lines = after.splitlines()
                    caption_lines = []
                    caption_started = False
                    max_caption_length = 300
                    skip_blank_lines = True
                    
                    for line in lines:
                        line = line.strip()
                        if skip_blank_lines and (not line or line == '...' or re.match(r'^\d{1,4}$', line)):
                            continue
                        skip_blank_lines = False
                        if caption_started and (not line or line == '...'):
                            break
                        if re.match(r'^(#|##|\s*INTRODUCTION|ABSTRACT|REFERENCES|ACKNOWLEDGMENTS)', line, re.IGNORECASE):
                            break
                        if (re.match(r'^(Figure|Fig\.|Table|Diagram|Chart|Image|Photo)', line, re.IGNORECASE)
                            or (len(line) > 0 and len(line) < 200)):
                            caption_lines.append(line)
                            caption_started = True
                        elif caption_started:
                            caption_lines.append(line)
                        if sum(len(l) for l in caption_lines) > max_caption_length:
                            break
                    
                    caption = ' '.join(caption_lines).strip()
                    if caption:
                        Logger.info(f"Extracted caption: '{caption[:100]}...' on page {page_num}")
                    else:
                        Logger.info(f"No caption found after image link on page {page_num}")
                    
                    # Store image reference info
                    image_refs.append({
                        "file_path": img_path,
                        "caption": caption,
                        "offset": start_offset
                    })
                    
                    # Process file path
                    abs_img_path = img_path
                    if not os.path.isabs(img_path):
                        abs_img_path = os.path.join(os.getcwd(), img_path)
                    
                    if os.path.exists(abs_img_path) or os.path.exists(img_path):
                        path_to_use = abs_img_path if os.path.exists(abs_img_path) else img_path
                        if path_to_use not in image_paths:
                            image_paths.append(path_to_use)
                            Logger.debug(f"Found image path in document: {path_to_use}")
                        
                        try:
                            idx_part = img_path.split('-')[-1].split('.')[0]
                            img_index = int(idx_part)
                            image_paths_dict[img_index] = img_path
                        except Exception as e:
                            Logger.debug(f"Error extracting image index from {img_path}: {e}")
                            image_paths_dict[len(image_paths_dict)] = img_path
                
                # Build a map of markdown captions by filename for later use
                markdown_captions = {}
                for ref in image_refs:
                    filename = os.path.basename(ref["file_path"])
                    markdown_captions[filename] = {
                        "caption": ref.get("caption", ""),
                        "offset": ref.get("offset", -1)
                    }
                
                # Now create chunks
                chunks = DocumentManager._chunk_document_text(
                    document["text"],
                    chunk_size,
                    chunk_overlap,
                    document["metadata"],
                    words_data=document.get("words") # Pass word data
                )
                
                # Process each chunk using the already extracted image references
                for i, chunk in enumerate(chunks):
                    # Filter image references that belong to this chunk
                    chunk_start = chunk["metadata"].get("chunk_start_offset", 0)
                    chunk_end = chunk["metadata"].get("chunk_end_offset", 0)
                    
                    # Get images that fall within this chunk's bounds
                    chunk_image_refs = [
                        img for img in image_refs
                        if chunk_start <= img["offset"] < chunk_end
                    ]
                    
                    # Process images for this chunk
                    unified_images = []
                    
                    # Add images extracted from document that fall within this chunk
                    if "images" in document and document["images"]:
                        for img in document["images"]:
                            img_entry = {}
                            for key, value in img.items():
                                img_entry[key] = value
                            
                            # Add file path based on position
                            img_path = None
                            img_position = i  # Use chunk index as a position hint
                            if img_position in image_paths_dict:
                                img_path = image_paths_dict[img_position]
                            elif len(image_paths_dict) == 1:
                                img_path = list(image_paths_dict.values())[0]
                            
                            if img_path:
                                if not os.path.isabs(img_path) and os.path.exists(os.path.join(os.getcwd(), img_path)):
                                    img_entry['file_path'] = os.path.join(os.getcwd(), img_path)
                                else:
                                    img_entry['file_path'] = img_path
                            
                            # Assign caption if available
                            filename = os.path.basename(img_entry.get('file_path', ''))
                            caption_info = markdown_captions.get(filename)
                            if caption_info:
                                img_entry['caption'] = caption_info.get('caption', '')
                                img_entry['offset'] = caption_info.get('offset', -1)
                            else:
                                img_entry['caption'] = ""
                                img_entry['offset'] = -1
                            
                            # Only add if this image's offset falls within this chunk
                            if img_entry.get('offset', -1) >= 0:
                                if chunk_start <= img_entry['offset'] < chunk_end:
                                    unified_images.append(img_entry)
                            else:
                                # If no offset information, add based on chunk index
                                unified_images.append(img_entry)
                            
                            # Add page number to images
                            page_num = chunk["metadata"].get("page")
                            if page_num is not None:
                                for img in unified_images:
                                    img['page'] = int(page_num)
                            
                            # Add to all_unified_images with deduplication
                            for img in unified_images:
                                if img.get('file_path') and not any(
                                    existing.get('file_path') == img.get('file_path')
                                    for existing in all_unified_images
                                ):
                                    all_unified_images.append(img)
                            
                            # Serialize images for storage
                            try:
                                images_json = json.dumps(serialize_rects(unified_images))
                            except Exception as e:
                                Logger.warning(f"Could not serialize unified images for chunk {i}: {e}")
                                images_json = "[]"
                            
                            # Create metadata for this chunk
                            metadata = chunk["metadata"].copy()
                            metadata["images"] = images_json # This is JSON string of image dicts
                            
                            # Define original_page_num before using it in the log
                            original_page_num_for_log = chunk["metadata"].get("page", "unknown")

                            # Populate 'image_paths' for compatibility with _extract_images_from_sources
                            if unified_images: # unified_images is a list of dicts for this chunk
                                metadata["image_paths"] = [img_info["file_path"] for img_info in unified_images if img_info.get("file_path")]
                                Logger.debug(f"    Chunk {i} (page {original_page_num_for_log}) assigned image_paths: {metadata.get('image_paths')} for text: '{chunk['text'][:70].replace(chr(10), ' ')}...'")
                            else:
                                Logger.debug(f"    Chunk {i} (page {original_page_num_for_log}) has NO unified_images, so no image_paths assigned for text: '{chunk['text'][:70].replace(chr(10), ' ')}...'")
                            metadata["document_id"] = pdf_id
                            metadata["chunk_number"] = i
                            metadata["chunk_total"] = len(chunks)
                            
                            # Create LlamaDocument for chunk
                            # Ensure metadata has page_num correctly from the original document metadata
                            original_page_num = chunk["metadata"].get("page", "unknown")
                            chunk_doc_id = f"{pdf_id}_page{original_page_num}_chunk{i}"
                            llama_document = LlamaDocument(
                                id_=chunk_doc_id,
                                text=chunk["text"],
                                metadata=metadata, # metadata already contains page, chunk_number, etc.
                                text_template="Metadata: {metadata_str}\n-----\nContent: {content}",
                            )
                            Logger.debug(f"Created LlamaDocument chunk with id_: {chunk_doc_id}, text length: {len(chunk['text'])}, bbox: {metadata.get('chunk_bbox')}")
                            llama_documents.append(llama_document)
                        img_path = match.group(1).strip()
                        start_offset = match.start() + chunk["metadata"].get("chunk_start_offset", 0)
                        
                        # Look for caption as in original method
                        caption = ""
                        after = chunk["text"][match.end():]
                        lines = after.splitlines()
                        caption_lines = []
                        caption_started = False
                        max_caption_length = 300
                        skip_blank_lines = True
                        
                        for line in lines:
                            line = line.strip()
                            if skip_blank_lines and (not line or line == '...' or re.match(r'^\d{1,4}$', line)):
                                continue
                            skip_blank_lines = False
                            if caption_started and (not line or line == '...'):
                                break
                            if re.match(r'^(#|##|\s*INTRODUCTION|ABSTRACT|REFERENCES|ACKNOWLEDGMENTS)', line, re.IGNORECASE):
                                break
                            if (re.match(r'^(Figure|Fig\.|Table|Diagram|Chart|Image|Photo)', line, re.IGNORECASE)
                                or (len(line) > 0 and len(line) < 200)):
                                caption_lines.append(line)
                                caption_started = True
                            elif caption_started:
                                caption_lines.append(line)
                            if sum(len(l) for l in caption_lines) > max_caption_length:
                                break
                        
                        caption = ' '.join(caption_lines).strip()
                        
                        image_refs.append({
                            "file_path": img_path,
                            "caption": caption,
                            "offset": start_offset
                        })
                        
                        # Add to image paths
                        abs_img_path = img_path
                        if not os.path.isabs(img_path):
                            abs_img_path = os.path.join(os.getcwd(), img_path)
                        
                        if os.path.exists(abs_img_path) or os.path.exists(img_path):
                            path_to_use = abs_img_path if os.path.exists(abs_img_path) else img_path
                            if path_to_use not in image_paths:
                                image_paths.append(path_to_use)
                                Logger.debug(f"Found image path in chunk text: {path_to_use}")
                            
                            try:
                                idx_part = img_path.split('-')[-1].split('.')[0]
                                img_index = int(idx_part)
                                image_paths_dict[img_index] = img_path
                            except Exception as e:
                                Logger.debug(f"Error extracting image index from {img_path}: {e}")
                                image_paths_dict[len(image_paths_dict)] = img_path
                    
                    # Build unified images for this chunk
                    unified_images = []
                    markdown_captions = {}
                    for ref in image_refs:
                        filename = os.path.basename(ref["file_path"])
                        markdown_captions[filename] = {
                            "caption": ref.get("caption", ""),
                            "offset": ref.get("offset", -1)
                        }
                    
                    # Incorporate the chunk's original images
                    chunk_images = chunk.get("images", [])
                    for i, img in enumerate(chunk_images):
                        img_entry = {}
                        for key, value in img.items():
                            img_entry[key] = value
                        
                        # Add file path based on position
                        img_path = None
                        img_position = i
                        if img_position in image_paths_dict:
                            img_path = image_paths_dict[img_position]
                        elif len(image_paths_dict) == 1:
                            img_path = list(image_paths_dict.values())[0]
                        
                        if img_path:
                            if not os.path.isabs(img_path) and os.path.exists(os.path.join(os.getcwd(), img_path)):
                                img_entry['file_path'] = os.path.join(os.getcwd(), img_path)
                            else:
                                img_entry['file_path'] = img_path
                        
                        # Assign caption if available
                        filename = os.path.basename(img_entry.get('file_path', ''))
                        caption_info = markdown_captions.get(filename)
                        if caption_info:
                            img_entry['caption'] = caption_info.get('caption', '')
                            img_entry['offset'] = caption_info.get('offset', -1)
                        else:
                            img_entry['caption'] = ""
                            img_entry['offset'] = -1
                        
                        unified_images.append(img_entry)
                    
                    # Add page number to images
                    page_num = chunk["metadata"].get("page")
                    if page_num is not None:
                        for img in unified_images:
                            img['page'] = int(page_num)
                    
                    # Add images to collection
                    all_unified_images.extend(unified_images)
                    
                    try:
                        images_json = json.dumps(serialize_rects(unified_images))
                    except Exception as e:
                        Logger.warning(f"Could not serialize unified images in chunk: {e}")
                        images_json = "[]"
                    
                    # Create metadata for this chunk
                    metadata = chunk["metadata"].copy()
                    metadata["images"] = images_json
                    metadata["document_id"] = pdf_id
                    metadata["chunk_number"] = i
                    metadata["chunk_total"] = len(chunks)
                    
                    # Create LlamaDocument for chunk
                    llama_document = LlamaDocument(
                        text=chunk["text"],
                        metadata=metadata,
                        text_template="Metadata: {metadata_str}\n-----\nContent: {content}",
                    )
                    
                    llama_documents.append(llama_document)
            else:
                # Page is small enough to be a single chunk
                Logger.debug(f"Page {page_num} does not need chunking: {text_len} chars <= {chunk_size} threshold")
                
                current_page_image_paths_dict = {}
                current_page_markdown_captions = {}

                if document.get("text"):
                    page_md_images = list(re.finditer(r'!\[.*?\]\((.*?)\)', document["text"]))
                    for idx, match_obj in enumerate(page_md_images):
                        current_page_image_paths_dict[idx] = match_obj.group(1).strip()

                    page_md_images_for_captions = list(re.finditer(r'!\[(.*?)]\((.*?)\)', document["text"]))
                    for match_obj_cap in page_md_images_for_captions:
                        img_filename_cap = os.path.basename(match_obj_cap.group(2).strip())
                        current_page_markdown_captions[img_filename_cap] = {
                            "caption": match_obj_cap.group(1).strip(),
                            "offset": match_obj_cap.start()
                        }
                
                unified_images_for_page = []
                if "images" in document and document["images"]:
                    for img_idx, img_info_raw in enumerate(document["images"]):
                        img_entry = serialize_rects(img_info_raw)
                        img_path = current_page_image_paths_dict.get(img_idx)

                        if img_path:
                            if not os.path.isabs(img_path) and os.path.exists(os.path.join(os.getcwd(), img_path)):
                                img_entry['file_path'] = os.path.join(os.getcwd(), img_path)
                            elif os.path.exists(img_path):
                                img_entry['file_path'] = img_path
                        
                        filename = os.path.basename(img_entry.get('file_path', ''))
                        if filename in current_page_markdown_captions:
                            img_entry['caption'] = current_page_markdown_captions[filename].get('caption', img_entry.get('caption', ''))
                        
                        if 'page' not in img_entry or img_entry.get('page') is None:
                            img_entry['page'] = page_num
                            
                        unified_images_for_page.append(img_entry)
                
                for u_img in unified_images_for_page:
                    if u_img.get('file_path') and not any(
                        existing_img.get('file_path') == u_img['file_path']
                        for existing_img in all_unified_images if existing_img.get('file_path') is not None
                    ):
                        all_unified_images.append(u_img)
                
                doc_metadata = document.get("metadata", {}).copy()
                doc_metadata["images"] = json.dumps(serialize_rects(unified_images_for_page))

                page_bbox = None
                page_words_data = document.get("words")

                if page_words_data:
                    Logger.debug(f"Page {page_num} (not chunked): Attempting to calculate bbox from {len(page_words_data)} words.")
                    final_rect = fitz.Rect() # Requires: import fitz at the top of the file or class
                    for wd in page_words_data:
                        try:
                            # wd is expected to be a list/tuple like (x0, y0, x1, y1, word_text, ...)
                            word_rect = fitz.Rect(wd[0], wd[1], wd[2], wd[3])
                            if final_rect.is_empty:
                                final_rect = word_rect
                            else:
                                final_rect.include_rect(word_rect)
                        except Exception as e:
                            Logger.warning(f"Page {page_num} (not chunked): Could not form Rect from word data {wd}: {e}")
                    if not final_rect.is_empty:
                        page_bbox = [final_rect.x0, final_rect.y0, final_rect.x1, final_rect.y1]
                        Logger.debug(f"Page {page_num} (not chunked) calculated bbox from words: {page_bbox}")
                
                if not page_bbox: # Fallback if words_data not present or bbox calculation failed
                    raw_rect_data = doc_metadata.get("rect")
                    if isinstance(raw_rect_data, (list, tuple)) and len(raw_rect_data) == 4:
                        page_bbox = list(raw_rect_data)
                        Logger.debug(f"Page {page_num} (not chunked) using 'rect' metadata for bbox: {page_bbox}")
                    elif isinstance(doc_metadata.get("mediabox"), (list, tuple)) and len(doc_metadata["mediabox"]) == 4:
                        page_bbox = list(doc_metadata["mediabox"])
                        Logger.debug(f"Page {page_num} (not chunked) using 'mediabox' metadata for bbox: {page_bbox}")
                
                doc_metadata["chunk_bbox"] = page_bbox # page_bbox will be None if all attempts failed
                if page_bbox:
                    Logger.debug(f"Page {page_num} (not chunked) final chunk_bbox: {page_bbox}")
                else:
                    Logger.debug(f"Page {page_num} (not chunked) could not determine page bbox. Raw rect: {doc_metadata.get('rect')}, Raw mediabox: {doc_metadata.get('mediabox')}")
                
                llama_doc = LlamaDocument(
                    id_=f"{pdf_id}_page_{page_num}", # Use id_ for the node's unique identifier
                    text=document["text"],
                    metadata=doc_metadata, # metadata already contains page number
                    # doc_id=f"{pdf_id}_page_{page_num}" # doc_id is for relating to parent, id_ is node id
                )
                Logger.debug(f"Created LlamaDocument (non-chunked) with id_: {llama_doc.id_}, text length: {len(document['text'])}, bbox: {doc_metadata.get('chunk_bbox')}")
                llama_documents.append(llama_doc)
            
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
            # Properly deduplicate images by file path before storage
            deduplicated_images = []
            seen_paths = set()
            
            for img in all_unified_images:
                img_path = img.get('file_path')
                if img_path and img_path not in seen_paths:
                    seen_paths.add(img_path)
                    deduplicated_images.append(img)
            
            # Debug log a few of the deduplicated images with their captions
            for i, img in enumerate(deduplicated_images[:5]):  # Log first 5 images
                Logger.info(f"Unified image {i+1} before storage: path={img.get('file_path', 'None')}, "
                           f"page={img.get('page', 'None')}, caption='{img.get('caption', 'None')}'")
            
            StateManager.store_document_unified_images(pdf_id, deduplicated_images)
            Logger.info(f"Stored {len(deduplicated_images)} unified images with captions for document {pdf_id}")
        
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
        from llama_index.core import Settings, StorageContext
        from llama_index.core.node_parser import SentenceSplitter # Import SentenceSplitter
        # SimpleDocumentStore is already imported at the top of the file from llama_index.core.storage.docstore

        Logger.info(f"Creating vector database for document {pdf_id} with {len(documents)} document chunks...")

        docstore = SimpleDocumentStore()
        docstore.add_documents(documents)
        
        storage_context = StorageContext.from_defaults(docstore=docstore)
        
        noop_text_splitter = SentenceSplitter(
            chunk_size=4096,
            chunk_overlap=0,
            include_metadata=True,
            include_prev_next_rel=False
        )

        vector_transformations = [noop_text_splitter, Settings.embed_model]
        
        vector_index = VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_context,
            transformations=vector_transformations,
            show_progress=True
        )
        
        keyword_transformations = [noop_text_splitter]
        keyword_index = SimpleKeywordTableIndex.from_documents(
            documents,
            storage_context=storage_context,
            transformations=keyword_transformations,
            show_progress=True
        )
        
        Logger.info(f"Vector and keyword indexes created for document {pdf_id}")
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