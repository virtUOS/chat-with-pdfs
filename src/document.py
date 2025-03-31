"""
Document loading and processing functions for the Chat with Docs application.
"""

import os
import json
import uuid
import re
import streamlit as st

from llama_index.core import Document as LlamaDocument
from llama_index.core import VectorStoreIndex, SimpleKeywordTableIndex
from llama_index.core.storage.docstore import SimpleDocumentStore

import pymupdf4llm

from .config import IMAGES_PATH, SUMMARY_MODEL


def ensure_dir_exists(path):
    """Create directory if it doesn't exist."""
    os.makedirs(path, exist_ok=True)


def save_uploaded_file(uploaded_file):
    """Save an uploaded file to a temporary location."""
    # Get absolute path for temp directory
    temp_dir = os.path.join(os.getcwd(), "temp_files")
    
    # Create directory if it doesn't exist
    ensure_dir_exists(temp_dir)
    
    # Clean the filename to ensure it's valid
    clean_filename = os.path.basename(uploaded_file.name)
    
    # Create an absolute file path
    temp_file_path = os.path.join(temp_dir, clean_filename)
    
    # Check if file already exists and add timestamp if needed
    import time
    if os.path.exists(temp_file_path):
        base, ext = os.path.splitext(clean_filename)
        timestamp = int(time.time())
        clean_filename = f"{base}_{timestamp}{ext}"
        temp_file_path = os.path.join(temp_dir, clean_filename)
    
    # Write the file
    with open(temp_file_path, "wb") as f:
        f.write(uploaded_file.getvalue())
    
    # Verify file was saved correctly
    if not os.path.exists(temp_file_path):
        raise FileNotFoundError(f"Failed to save file to {temp_file_path}")
    
    return temp_file_path


def process_pdf(pdf_path, pdf_name):
    """Process a PDF file and create indexes using pymupdf4llm."""
    # Generate a unique ID for this document
    pdf_id = str(uuid.uuid4())
    
    # Update file to document ID mapping
    st.session_state['file_document_id'][pdf_name] = pdf_id

    # Create directory if it doesn't exist
    ensure_dir_exists(IMAGES_PATH)

    # Create a unique directory for this document's images
    doc_image_path = os.path.join(IMAGES_PATH, pdf_id)
    ensure_dir_exists(doc_image_path)
    
    # Extract documents with pymupdf4llm
    docs = pymupdf4llm.to_markdown(
        doc=pdf_path,
        write_images=True,
        image_path=doc_image_path,
        image_format="jpg",
        dpi=200,
        page_chunks=True,
        extract_words=True
    )
    
    # Track image paths for this document
    image_paths = []
    
    # Convert to Llama Index documents
    llama_documents = []
    for i, document in enumerate(docs):
        print(document)
        
        # Extract metadata
        # Extract Markdown image references from text
        markdown_images = re.findall(r'!\[(.*?)\]\((.*?)\)', document["text"])
        image_paths_dict = {}
        for _, img_path in markdown_images:
            # Assuming the image references follow a pattern like img_1, img_2, etc.
            if os.path.exists(img_path) or os.path.exists(os.path.join(os.getcwd(), img_path)):
                # Add to image_paths
                if img_path not in image_paths:
                    image_paths.append(img_path)
                    print(f"Found image path in text: {img_path}")
                
                # Try to extract the image number from the filename
                try:
                    # Pattern is usually: filename-page-index.jpg
                    # We want to extract the index
                    idx_part = img_path.split('-')[-1].split('.')[0]
                    img_index = int(idx_part)
                    image_paths_dict[img_index] = img_path
                    print(f"Mapped image index {img_index} to path {img_path}")
                except Exception as e:
                    print(f"Error extracting image index from {img_path}: {e}")
                    # If we can't extract the index, just store by position
                    image_paths_dict[len(image_paths_dict)] = img_path
        
        # Process images to make them JSON serializable and add paths
        images_json = "[]"
        if document.get("images"):
            # Convert non-serializable objects (like Rect) to serializable format
            serializable_images = []
            for i, img in enumerate(document.get("images")):
                serializable_img = {}
                for key, value in img.items():
                    # Convert Rect objects to a list
                    if key == 'bbox' and hasattr(value, '__class__') and value.__class__.__name__ == 'Rect':
                        # Convert Rect to a list of coordinates [x0, y0, x1, y1]
                        serializable_img[key] = [value.x0, value.y0, value.x1, value.y1]
                    else:
                        serializable_img[key] = value
                
                # Add the file path if available
                if img.get('number') and img.get('number') - 1 in image_paths_dict:
                    # Using number - 1 because image numbers often start at 1
                    serializable_img['file_path'] = image_paths_dict[img.get('number') - 1]
                    print(f"Added file_path to image {img.get('number')}: {image_paths_dict[img.get('number') - 1]}")
                elif i in image_paths_dict:
                    # Fallback to position-based mapping
                    serializable_img['file_path'] = image_paths_dict[i]
                    print(f"Added file_path to image at position {i}: {image_paths_dict[i]}")
                
                serializable_images.append(serializable_img)
            try:
                images_json = json.dumps(serializable_images)
            except Exception as e:
                print(f"Warning: Could not serialize images: {e}")
                images_json = "[]"

        print(images_json)
        
        metadata = {
            "page": str(document["metadata"].get("page")),
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
    
    # Store the image paths for this document
    st.session_state['document_image_map'][pdf_id] = image_paths
    print(f"Stored {len(image_paths)} image paths for document {pdf_id}")
    
    # Create vector and keyword indexes
    multi_index, keyword_index = create_vector_database(llama_documents, pdf_id)
    
    # Generate document summary using the specified model
    try:
        print(f"Generating document summary using {SUMMARY_MODEL} model...")
        summary = generate_document_summary(llama_documents, SUMMARY_MODEL)
        # Store the summary in session state
        st.session_state['document_summaries'][pdf_id] = summary
        print(f"Generated summary for document {pdf_id}")
    except Exception as e:
        print(f"Failed to generate summary: {e}")
        
    # Generate query suggestions using the specified model
    try:
        print(f"Generating query suggestions using {SUMMARY_MODEL} model...")
        suggestions = generate_query_suggestions(llama_documents, SUMMARY_MODEL)
        
        # Initialize suggestions dict if not exists
        if 'document_query_suggestions' not in st.session_state:
            st.session_state['document_query_suggestions'] = {}
        
        # Store the suggestions in session state
        st.session_state['document_query_suggestions'][pdf_id] = suggestions
        print(f"Generated query suggestions for document {pdf_id}: {suggestions}")
    except Exception as e:
        print(f"Failed to generate query suggestions: {e}")
    
    return multi_index, keyword_index, pdf_id


def generate_query_suggestions(documents, model_name):
    """
    Generate query suggestions for a document using the specified model.
    
    Args:
        documents: List of Llama Document objects
        model_name: Name of the model to use for query suggestion generation
        
    Returns:
        A list of 3 query suggestions
    """
    # Extract text from documents (limit to first few docs for efficiency)
    sample_docs = documents[:min(3, len(documents))]
    sample_text = "\n\n".join([doc.text for doc in sample_docs])
    
    # Limit text length to avoid token limits
    max_chars = 5000
    if len(sample_text) > max_chars:
        sample_text = sample_text[:max_chars] + "..."
    
    from llama_index.llms.openai import OpenAI
    
    try:
        # Initialize the LLM with the specified model
        llm = OpenAI(model=model_name)
        
        # Create a prompt for generating queries
        prompt = f"""
        Please generate 3 interesting and diverse questions that someone might want to ask about the following document.
        Make the questions specific to the content and insightful.
        Format your response as a simple Python list with exactly 3 questions, each enclosed in quotes.
        Example format: ["Question 1?", "Question 2?", "Question 3?"]
        
        DOCUMENT:
        {sample_text}
        
        QUESTIONS:
        """
        
        # Generate the suggestions
        response = llm.complete(prompt)
        
        # Parse the response to get a list of questions
        import ast
        suggestions = ast.literal_eval(response.text.strip())
        
        # Ensure we have exactly 3 questions
        if len(suggestions) > 3:
            suggestions = suggestions[:3]
        elif len(suggestions) < 3:
            suggestions = suggestions + ["Tell me more about this document"] * (3 - len(suggestions))
            
        return suggestions
    except Exception as e:
        print(f"Error generating query suggestions: {e}")
        # Fallback suggestions
        return [
            "What is the main topic of this document?",
            "What are the key findings in this document?",
            "Summarize this document briefly."
        ]


def generate_document_summary(documents, model_name):
    """
    Generate a summary of the document using the specified model.
    
    Args:
        documents: List of Llama Document objects
        model_name: Name of the model to use for summarization
        
    Returns:
        A string containing the document summary
    """
    # Extract text from documents (limit to first few docs for efficiency)
    sample_docs = documents[:min(3, len(documents))]
    sample_text = "\n\n".join([doc.text for doc in sample_docs])
    
    # Limit text length to avoid token limits
    max_chars = 5000
    if len(sample_text) > max_chars:
        sample_text = sample_text[:max_chars] + "..."
    
    from llama_index.llms.openai import OpenAI
    
    try:
        # Initialize the LLM with the summary model
        llm = OpenAI(model=model_name)
        
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
        return response.text.strip()
    except Exception as e:
        print(f"Error generating document summary: {e}")
        return "Summary generation failed. Please try again later."


def create_vector_database(documents, pdf_id):
    """Create vector and keyword indexes from documents."""
    # Create the vector index
    multi_index = VectorStoreIndex.from_documents(
        documents,
        docstore=SimpleDocumentStore(),
        show_progress=True
    )
    
    # Create a keyword index
    keyword_index = SimpleKeywordTableIndex.from_documents(documents)
    
    return multi_index, keyword_index
