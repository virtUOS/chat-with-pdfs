"""
Image extraction and processing for the Chat with Docs application.
"""

import os
import json
import streamlit as st


def process_source_for_images(source, current_doc_id, available_images):
    """
    Process a source node for image references using the metadata already stored during PDF processing.
    
    Args:
        source: The source node to process
        current_doc_id: The ID of the current document
        available_images: List of available image paths
        
    Returns:
        A list of image information dictionaries (path, caption)
    """
    images = []
    
    # Get metadata from the source
    if hasattr(source, 'node'):
        metadata = source.node.metadata
    elif hasattr(source, 'metadata'):
        metadata = source.metadata
    else:
        return images
    
    # Get the page number from metadata
    page_num = metadata.get('page')
    
    # Extract image information from metadata if available
    if 'images' in metadata and metadata['images']:
        try:
            # Parse the JSON string to get image data
            image_list = json.loads(metadata['images'])
            
            if isinstance(image_list, list) and image_list:
                for img_meta in image_list:
                    # Skip if not a dictionary
                    if not isinstance(img_meta, dict):
                        continue
                    
                    # Use the file path from the metadata if available
                    if 'file_path' in img_meta:
                        img_path = img_meta['file_path']
                        abs_path = os.path.abspath(img_path)
                        
                        # Check if image exists
                        if os.path.exists(abs_path):
                            image_info = {
                                'path': abs_path,
                                'caption': f"Image from page {page_num}"
                            }
                            # Avoid duplicates
                            if not any(img['path'] == abs_path for img in images):
                                images.append(image_info)
                        elif os.path.exists(img_path):
                            # Try with the original relative path
                            image_info = {
                                'path': img_path,
                                'caption': f"Image from page {page_num}"
                            }
                            if not any(img['path'] == img_path for img in images):
                                images.append(image_info)
        except json.JSONDecodeError:
            pass
    
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
        print(f"Found {len(images)} images for document {doc_id} in session state")
        
        # Verify image paths exist
        valid_images = []
        for img_path in images:
            # Convert to absolute path
            abs_path = os.path.abspath(img_path)
            
            # Check if the image still exists
            if os.path.exists(abs_path):
                valid_images.append(abs_path)
                print(f"Verified image exists: {abs_path}")
            elif os.path.exists(img_path):
                valid_images.append(img_path)
                print(f"Verified image exists (relative path): {img_path}")
        
        return valid_images
    
    return []
