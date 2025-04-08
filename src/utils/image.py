"""
Image extraction and processing for the Chat with Docs application.
"""

import os
import json
import streamlit as st
from .logger import Logger
from ..config import IMAGES_PATH


def process_source_for_images(source, current_doc_id, available_images):
    """
    Process a source node for image references using Markdown-style image patterns found in the text.
    The pattern is: ![](/path/to/image.jpg)
    
    Args:
        source: The source node to process
        current_doc_id: The ID of the current document
        available_images: List of available image paths
        
    Returns:
        A list of image information dictionaries (path, caption)
    """
    images = []

    Logger.info(f"Source: {source}")

    
    # Get metadata and text from the source
    if hasattr(source, 'metadata') and hasattr(source, 'text'):
        metadata = source.metadata
        text = source.text
    else:
        return images
    
    # Get the page number from metadata
    page_num = metadata.get('page')
    
    # Debug current source information
    Logger.info(f"Processing source for images - doc_id: {current_doc_id}, page: {page_num}")
    Logger.info(f"Available images count: {len(available_images)}")
    

    # DEBUG: Log page number and Markdown image references
    Logger.info(f"Source page: {page_num}")
    if text:
        import re
        image_matches = re.findall(r'!\[\]\(([^)]+)\)', text)
        Logger.info(f"Found {len(image_matches)} Markdown image references in source text")
        for img_path in image_matches:
            Logger.info(f"Markdown image path: {img_path}")

    # Look for the Markdown image syntax: ![](image_path)
    if text:
        import re
        # Match pattern ![](image_path)
        image_matches = re.findall(r'!\[\]\(([^)]+)\)', text)
        
        if image_matches:
            Logger.info(f"Found {len(image_matches)} Markdown image references in text")
            
            for img_path in image_matches:
                # Clean up the path (remove any whitespace)
                img_path = img_path.strip()
                
                # Check if this path exists in available images
                if img_path in available_images:
                    # Direct match - use it as is
                    # Extract actual page number from the image path
                    import re
                    # Always use the page number from the source metadata, which is the correct context
                    # When the image appears in a source, it should be associated with that source's page
                    page_display = page_num if isinstance(page_num, int) else 1
                    Logger.info(f"Using page {page_display} from source metadata for image: {img_path}")
                    
                    image_info = {
                        'file_path': img_path,  # Use file_path consistently across the application
                        'caption': f"Image from page {page_display}"
                    }
                    images.append(image_info)
                    Logger.info(f"Added image from direct Markdown reference: {img_path}")
    
    return images
    
    # No need for duplicated code - it was removed
    
    return images


def get_document_images(doc_id):
    """
    Get all images associated with a document from session state.
    
    Args:
        doc_id: The document ID
        
    Returns:
        A list of image paths
    """
    if doc_id in st.session_state.get('document_image_map', {}):
        images = st.session_state['document_image_map'][doc_id]
        Logger.info(f"Found {len(images)} images for document {doc_id} in session state")
        
        # Verify image paths exist
        valid_images = []
        invalid_images = 0
        
        for img_path in images:
            try:
                # Convert to absolute path
                abs_path = os.path.abspath(img_path)
                
                # Check if the image still exists
                if os.path.exists(abs_path):
                    valid_images.append(abs_path)
                    Logger.debug(f"Verified image exists: {abs_path}")
                elif os.path.exists(img_path):
                    valid_images.append(img_path)
                    Logger.debug(f"Verified image exists (relative path): {img_path}")
                else:
                    # Find the correct document directory
                    doc_dir = os.path.join(IMAGES_PATH, doc_id)
                    Logger.debug(f"Looking for images in document directory: {doc_dir}")
                    
                    if os.path.exists(doc_dir):
                        # Get images matching the filename pattern
                        import glob
                        
                        # Get just the filename from the path (without directories)
                        img_filename = os.path.basename(img_path)
                        
                        # Look for exact filename match first
                        exact_path = os.path.join(doc_dir, img_filename)
                        if os.path.exists(exact_path):
                            valid_images.append(exact_path)
                            Logger.info(f"Found exact image match: {exact_path}")
                        else:
                            # Try to find a file with the same name pattern
                            # For example, if img_path is "P19-1044.pdf-3-0.jpg" but the actual
                            # file has a timestamp like "P19-1044_1743486037.pdf-3-0.jpg"
                            file_name = os.path.basename(img_filename)
                            pattern = os.path.join(doc_dir, f"*{os.path.splitext(file_name)[0]}*.jpg")
                            Logger.debug(f"Searching with pattern: {pattern}")
                            
                            matching_files = glob.glob(pattern)
                            if matching_files:
                                valid_images.append(matching_files[0])
                                Logger.info(f"Found matching image: {matching_files[0]}")
                            else:
                                # No fallback - only use pattern matches
                                Logger.warning(f"No matching images found for pattern: {pattern}")
                                invalid_images += 1
                    else:
                        Logger.warning(f"Document directory not found: {doc_dir}")
                        invalid_images += 1
            except Exception as e:
                Logger.error(f"Error processing image path {img_path}: {e}")
                invalid_images += 1
        
        if invalid_images > 0:
            Logger.warning(f"Could not find {invalid_images} images for document {doc_id}")
        
        Logger.info(f"Returning {len(valid_images)} valid images for document {doc_id}")
        return valid_images
    
    Logger.info(f"No images found for document {doc_id} in session state")
    return []