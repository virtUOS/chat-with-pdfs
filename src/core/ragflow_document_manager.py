"""
RAGFlow-based document management for the Chat with Docs application.
Handles document processing, storage, and retrieval using RAGFlow API.
"""

import os
import re
import shutil
import tempfile
import fitz
import streamlit as st

import pymupdf4llm

from ..config import IMAGES_PATH
from ..utils.logger import Logger
from ..utils.i18n import I18n
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
    
    @staticmethod
    def _process_document_images(docs, pdf_id, pdf_path):
        """Process document images extracted by pymupdf4llm and store them in session state.
        
        This method extracts the image processing logic from the LlamaIndex pipeline
        but without the LlamaIndex-specific parts (vector indexes, etc.).
        
        Args:
            docs: Document content from pymupdf4llm extraction
            pdf_id: Document ID
            pdf_path: Path to the PDF file
        """
        
        Logger.debug(f"Processing images for document {pdf_id} with {len(docs)} pages.")
        
        # Track image paths for this document
        image_paths = []
        all_unified_images = []
        
        for document in docs:
            page_num = document.get('metadata', {}).get('page')
            text_len = len(document.get('text', ''))
            preview = document.get('text', '')[:200].replace('\n', ' ')
            Logger.info(f"Processing page: {page_num}, text length: {text_len}, preview: {preview}")

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
                    else:
                        # Image detected in PDF metadata but no extracted file found
                        Logger.warning(f"Image {i} detected in PDF metadata but no extracted file found - skipping")
                        continue
    
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
            all_unified_images.extend(unified_images)
        
        # Store the image paths for this document using StateManager
        StateManager.store_document_image_map(pdf_id, image_paths)
        Logger.info(f"Stored {len(image_paths)} image paths for document {pdf_id}")
        
        # Also store the unified image metadata with captions
        if all_unified_images:
            # Debug log a few of the unified images with their captions
            for i, img in enumerate(all_unified_images[:5]):  # Log first 5 images
                Logger.info(f"Unified image {i+1} before storage: path={img.get('file_path', 'None')}, "
                           f"page={img.get('page', 'None')}, caption='{img.get('caption', 'None')}'")
            
            StateManager.store_document_unified_images(pdf_id, all_unified_images)
            Logger.info(f"Stored {len(all_unified_images)} unified images with captions for document {pdf_id}")
    
    @staticmethod
    def _process_ragflow_document_images(pdf_data: bytes, doc_name: str, doc_id: str):
        """Process images on-demand for RAGFlow documents that weren't processed locally.
        
        This method extracts images from downloaded PDF data and stores them in session state
        for display purposes.
        
        Args:
            pdf_data: Binary PDF data
            doc_name: Name of the document
            doc_id: Document ID to use for storage
        """        
        Logger.info(f"Processing images on-demand for RAGFlow document: {doc_name}")
        
        try:
            # Save PDF data to a temporary file since pymupdf4llm needs a file path
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_file.write(pdf_data)
                temp_pdf_path = temp_file.name
            
            try:
                # Create a temporary directory for images
                with tempfile.TemporaryDirectory() as temp_image_dir:
                    # Use pymupdf4llm to extract markdown with images
                    docs = pymupdf4llm.to_markdown(
                        doc=temp_pdf_path,
                        write_images=True,
                        image_path=temp_image_dir,
                        image_format="png",
                        dpi=200,
                        page_chunks=True,
                        extract_words=True
                    )
                    
                    Logger.info(f"Extracted {len(docs)} pages from {doc_name}")
                    
                    # Process the extracted content using the EXACT same logic as LlamaIndex
                    RAGFlowDocumentManager._process_document_content_like_llamaindex(docs, doc_id, temp_pdf_path, temp_image_dir)
                    
            finally:
                # Clean up the temporary PDF file
                if os.path.exists(temp_pdf_path):
                    os.unlink(temp_pdf_path)
                    
        except Exception as e:
            Logger.error(f"Error processing images on-demand for {doc_name}: {e}")
            raise

    @staticmethod
    def _process_document_content_like_llamaindex(docs, doc_id, pdf_path, temp_image_dir):
        """Process document content using the EXACT same logic as LlamaIndex DocumentManager.
        
        This replicates the flawless image and caption extraction from the original implementation.
        """

        Logger.debug(f"Process document {doc_id} with {len(docs)} pages using LlamaIndex logic.")
        
        # Track image paths for this document
        image_paths = []
        
        # Convert to unified images format
        all_unified_images = []
        
        # Extract page dimensions for annotation boundary validation
        page_dimensions = {}
        try:
            pdf_doc = fitz.open(pdf_path)
            for page_num in range(len(pdf_doc)):
                page = pdf_doc[page_num]
                rect = page.rect
                page_dimensions[page_num + 1] = {  # 1-based page numbering
                    'width': float(rect.width),
                    'height': float(rect.height)
                }
            pdf_doc.close()
            Logger.info(f"Extracted page dimensions for {len(page_dimensions)} pages")
            Logger.info(f"DEBUG: Sample page dimensions - Page 1: {page_dimensions.get(1, 'Not found')}")
            Logger.info(f"DEBUG: All page numbers: {list(page_dimensions.keys())}")
        except Exception as e:
            Logger.warning(f"Could not extract page dimensions: {e}")
            page_dimensions = {}
        
        for document in docs:
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

                # Look for caption immediately after image link using EXACT LlamaIndex logic
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
                
                # Clean up markdown formatting like LlamaIndex version
                caption = ' '.join(caption_lines).strip()
                # Remove **bold** and *italic* formatting
                caption = re.sub(r'\*\*(.*?)\*\*', r'\1', caption)  # **bold**
                caption = re.sub(r'\*(.*?)\*', r'\1', caption)      # *italic*
                caption = caption.strip()
                
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
                
                # Check if image exists in temp directory
                temp_img_path = os.path.join(temp_image_dir, os.path.basename(img_path))
                if os.path.exists(temp_img_path):
                    # Copy to permanent location
                    permanent_dir = os.path.join("/tmp/chat-with-pdfs/tmp_assets/tmp_images", doc_id)
                    os.makedirs(permanent_dir, exist_ok=True)
                    
                    permanent_path = os.path.join(permanent_dir, os.path.basename(img_path))
                    shutil.copy2(temp_img_path, permanent_path)
                    
                    # Add to image_paths
                    if permanent_path not in image_paths:
                        image_paths.append(permanent_path)
                        Logger.debug(f"Found image path in text: {permanent_path}")
                    
                    # Extract the image number from the filename
                    try:
                        # Pattern is usually: filename-page-index.jpg
                        idx_part = img_path.split('-')[-1].split('.')[0]
                        img_index = int(idx_part)
                        image_paths_dict[img_index] = permanent_path
                    except Exception as e:
                        Logger.debug(f"Error extracting image index from {img_path}: {e}")
                        # If we can't extract the index, just store by position
                        image_paths_dict[len(image_paths_dict)] = permanent_path
            
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
                        img_entry['file_path'] = img_path
                    else:
                        # Image detected in PDF metadata but no extracted file found
                        # Try to extract the image using coordinates from the PDF (EXACT LlamaIndex logic)
                        try:
                            extracted_path = RAGFlowDocumentManager._extract_image_from_coordinates(
                                pdf_path,
                                document["metadata"].get("page", 1),
                                img,
                                doc_id,
                                i
                            )
                            if extracted_path:
                                img_entry['file_path'] = extracted_path
                                Logger.info(f"Successfully extracted image from coordinates: {extracted_path}")
                            else:
                                Logger.warning(f"Failed to extract image {i} from coordinates - skipping")
                                continue
                        except Exception as e:
                            Logger.error(f"Error extracting image {i} from coordinates: {e}")
                            continue
    
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
            all_unified_images.extend(unified_images)
        
        # Store the image paths for this document using StateManager
        StateManager.store_document_image_map(doc_id, image_paths)
        Logger.info(f"Stored {len(image_paths)} image paths for document {doc_id}")
        
        # Store page dimensions for annotation boundary validation
        if page_dimensions:
            StateManager.store_document_page_dimensions(doc_id, page_dimensions)
            Logger.info(f"Stored page dimensions for {len(page_dimensions)} pages for document {doc_id}")
            Logger.info(f"DEBUG: Verifying storage - retrieved back: {len(StateManager.get_document_page_dimensions(doc_id))} pages")
        
        # Also store the unified image metadata with captions
        if all_unified_images:
            # Debug log a few of the unified images with their captions
            for i, img in enumerate(all_unified_images[:5]):  # Log first 5 images
                Logger.info(f"Unified image {i+1} before storage: path={img.get('file_path', 'None')}, "
                           f"page={img.get('page', 'None')}, caption='{img.get('caption', 'None')}'")
            
            StateManager.store_document_unified_images(doc_id, all_unified_images)
            Logger.info(f"Stored {len(all_unified_images)} unified images with captions for document {doc_id}")

    @staticmethod
    def _extract_image_from_coordinates(pdf_path, page_num, img_metadata, pdf_id, img_index):
        """Extract an image from PDF using its coordinates and save it to disk.
        
        This is the EXACT same method as in LlamaIndex DocumentManager.
        """
        try:
            
            # Open the PDF
            pdf_doc = fitz.open(pdf_path)
            page = pdf_doc[page_num - 1]  # Convert to 0-based indexing
            
            # Get image bbox from metadata
            bbox = img_metadata.get('bbox')
            if not bbox:
                Logger.warning(f"No bbox found for image {img_index} on page {page_num}")
                return None
            
            # Create image directory
            image_dir = os.path.join("/tmp/chat-with-pdfs/tmp_assets/tmp_images", pdf_id)
            os.makedirs(image_dir, exist_ok=True)
            
            # Extract image using bbox
            rect = fitz.Rect(bbox)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=rect)
            
            # Save image
            img_filename = f"{pdf_id}_page_{page_num}_img_{img_index}.png"
            img_path = os.path.join(image_dir, img_filename)
            pix.save(img_path)
            
            pdf_doc.close()
            pix = None
            
            return img_path
            
        except Exception as e:
            Logger.error(f"Error extracting image from coordinates: {e}")
            return None
    
    @staticmethod
    def _process_document_images_from_temp(docs, doc_id: str, temp_image_dir: str):
        """Process document images from temporary directory and store them permanently.
        
        Args:
            docs: Document content from pymupdf4llm extraction
            doc_id: Document ID
            temp_image_dir: Temporary directory containing extracted images
        """
        
        Logger.info(f"Processing images from temporary directory for document {doc_id}")
        
        # Create permanent image directory
        permanent_image_dir = os.path.join(IMAGES_PATH, doc_id)
        os.makedirs(permanent_image_dir, exist_ok=True)
        
        # Track image paths for this document
        image_paths = []
        all_unified_images = []
        
        for document in docs:
            page_num = document.get('metadata', {}).get('page')
            Logger.info(f"Processing page {page_num}")

            # Extract Markdown image references from text
            markdown_images = list(re.finditer(r'!\[.*?\]\((.*?)\)', document["text"]))
            Logger.info(f"Found {len(markdown_images)} image references on page {page_num}")

            for i, match in enumerate(markdown_images):
                img_path = match.group(1).strip()
                temp_img_path = os.path.join(temp_image_dir, os.path.basename(img_path))
                
                if os.path.exists(temp_img_path):
                    # Copy image to permanent location
                    permanent_img_name = f"{doc_id}_page_{page_num}_img_{i}.png"
                    permanent_img_path = os.path.join(permanent_image_dir, permanent_img_name)
                    
                    try:
                        shutil.copy2(temp_img_path, permanent_img_path)
                        image_paths.append(permanent_img_path)
                        
                        # Extract caption from text after image
                        caption = RAGFlowDocumentManager._extract_simple_caption(document["text"], match)
                        
                        start_pos = max(0, match.start() - 200)
                        end_pos = min(len(document["text"]), match.end() + 200)
                        context_text = document["text"][start_pos:end_pos]
                        Logger.info(f"Context: '{context_text}'")
                        Logger.info(f"Image match: '{match.group()}'")
                        
                        # Create unified image entry
                        img_entry = {
                            'file_path': permanent_img_path,
                            'caption': caption,
                            'page': int(page_num) if page_num else 1,
                            'index': i
                        }
                        all_unified_images.append(img_entry)
                        
                        Logger.info(f"Copied image to permanent location: {permanent_img_path}")
                        Logger.info(f"Extracted caption: '{caption}'")
                        
                    except Exception as e:
                        Logger.error(f"Error copying image {temp_img_path}: {e}")
                else:
                    Logger.warning(f"Image file not found in temp directory: {temp_img_path}")
        
        # Store the image paths and metadata in session state
        StateManager.store_document_image_map(doc_id, image_paths)
        Logger.info(f"Stored {len(image_paths)} image paths for document {doc_id}")
        
        if all_unified_images:
            StateManager.store_document_unified_images(doc_id, all_unified_images)
            Logger.info(f"Stored {len(all_unified_images)} unified images with captions for document {doc_id}")
    
    @staticmethod
    def _extract_simple_caption(text: str, image_match) -> str:
        """Extract caption from text around an image reference using the same logic as LlamaIndex version.
        
        Args:
            text: Full text content
            image_match: Regex match object for the image reference
            
        Returns:
            str: Extracted caption or empty string
        """
        
        # Get text after image link
        after = text[image_match.end():]
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
            
            # Clean up markdown formatting
            clean_line = re.sub(r'\*\*([^*]+)\*\*', r'\1', line)  # Remove **bold** formatting
            clean_line = re.sub(r'\*([^*]+)\*', r'\1', clean_line)  # Remove *italic* formatting
            clean_line = clean_line.strip()
            
            # Heuristic: caption start if matches or is short
            if (re.match(r'^(Figure|Fig\.|Table|Diagram|Chart|Image|Photo)', clean_line, re.IGNORECASE)
                or (len(clean_line) > 0 and len(clean_line) < 200)):
                caption_lines.append(clean_line)
                caption_started = True
            elif caption_started:
                # After caption start, append more lines
                caption_lines.append(clean_line)
            
            # Stop if caption too long
            if sum(len(l) for l in caption_lines) > max_caption_length:
                break
        
        caption = ' '.join(caption_lines).strip()
        
        # If no caption found after image, check before image
        if not caption:
            before = text[:image_match.start()]
            before_lines = before.splitlines()
            
            # Check last few lines before image for captions
            for line in reversed(before_lines[-5:]):
                line = line.strip()
                if not line or line == '...' or re.match(r'^\d{1,4}$', line):
                    continue
                
                # Clean up markdown formatting
                clean_line = re.sub(r'\*\*([^*]+)\*\*', r'\1', line)
                clean_line = re.sub(r'\*([^*]+)\*', r'\1', clean_line)
                clean_line = clean_line.strip()
                
                # Look for caption patterns
                if re.match(r'^(Figure|Fig\.|Table|Diagram|Chart|Image|Photo)', clean_line, re.IGNORECASE):
                    caption = clean_line
                    break
        
        return caption