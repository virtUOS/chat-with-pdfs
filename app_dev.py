from llama_index.llms.openai import OpenAI
from llama_index.core import SimpleDirectoryReader, PromptTemplate, Document, StorageContext, SimpleKeywordTableIndex, get_response_synthesizer
from llama_index.core.indices import MultiModalVectorStoreIndex
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client.http.models import VectorParams, Distance
from llama_index.core.query_engine import RetrieverQueryEngine
import qdrant_client
from src.custom_retriever import CustomRetriever

import pymupdf4llm

import streamlit as st
from streamlit_pdf_viewer import pdf_viewer
from streamlit_dimensions import st_dimensions
from streamlit_js_eval import streamlit_js_eval

from dotenv import load_dotenv

import uuid
import time
import os
import re
import torch


load_dotenv()


st.set_page_config(
    page_title="Chat with Documents",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Hack to avoid torch/streamlit error
torch.classes.__path__ = [] # add this line to manually set it to empty. 

IMAGES_PATH = "tmp_assets/tmp_images/"

CITATION_CHAT_PROMPT = """
    CRITICAL INSTRUCTION: Your response MUST include numbered citations in square brackets [1], [2], etc.

    Follow these rules EXACTLY:
    1. Base your answer SOLELY on the provided sources.
    2. EVERY statement of fact MUST have a citation in square brackets [#].
    3. Format citations as [1], [2], [3], etc., corresponding to the source number.
    4. Citations must appear IMMEDIATELY after the information they support.
    5. Your answer MUST have AT LEAST ONE citation, even for simple queries.
    6. If sources don't contain relevant information, explicitly state this and explain why.
    7. DO NOT make up information or use your general knowledge.
    
    Example:
    Source 1: The sky is red in the evening and blue in the morning.
    Source 2: Water is wet when the sky is red.
    Query: When is water wet?
    Answer: According to the sources, water becomes wet when the sky is red [2], which occurs specifically in the evening [1].
    
    --------------
    
    Below are numbered sources of information:
    --------------
    
    {context_str}
    
    --------------
    
    Query: {query_str}
    
    Answer (YOU MUST INCLUDE NUMBERED CITATIONS IN FORMAT [1], [2], ETC.):
    """

GENERAL_CHAT_PROMPT = "Please provide an answer that considers both the provided sources and your general knowledge. \
    While you may use the sources as a basis, you are allowed to expand on the answer with additional details. \
    When referencing a source, cite it using its corresponding number, but you do not have to rely exclusively on them. \
    For example:\n \
    Source 1:\n \
    The sky is red in the evening and blue in the morning.\n \
    Query: When is water wet?\n \
    Answer: Based on source [1] the sky changes color in the evening, and in my general knowledge water tends to be wet under a variety of conditions.\n \
    Now it's your turn. Below are several numbered sources of information (if available):\n \
    \n------\n \
    {context_str} \
    \n------\n \
    Query: {query_str}\n \
    Answer: "


GENERAL_QA_TEMPLATE = PromptTemplate(
    "Please provide an answer that considers both the provided sources and your general knowledge. "
    "While you may use the sources as a basis, you are allowed to expand on the answer with additional details. "
    "When referencing a source, cite it using its corresponding number, but you do not have to rely exclusively on them. "
    "For example:\n"
    "Source 1:\n"
    "The sky is red in the evening and blue in the morning.\n"
    "Query: When is water wet?\n"
    "Answer: Based on source [1] the sky changes color in the evening, and in my general knowledge water tends to be wet under a variety of conditions.\n"
    "Now it's your turn. Below are several numbered sources of information (if available):"
    "\n------\n"
    "{context_str}"
    "\n------\n"
    "Query: {query_str}\n"
    "Answer: "
)


# Add this after load_dotenv()
if not os.getenv("OPENAI_API_KEY"):
    st.error("OPENAI_API_KEY is not set in the environment variables")
    upload_disabled = True
else:
    upload_disabled = False


if "id" not in st.session_state:
    st.session_state.id = uuid.uuid4()
    st.session_state.file_cache = {}


def change_chatbot_style():
    # Set style of chat input so that it shows up at the bottom of the column
    chat_input_style = f"""
    <style>
        .stChatInput {{
          position: fixed;
          bottom: 3rem;
        }}
    </style>
    """
    st.markdown(chat_input_style, unsafe_allow_html=True)

def initialize_variables():
    required_keys = {
        'doc_binary_data': {},
        'selected_file_name': None,
        'conversation_histories': {},
        'indexes': {},
        'previous_uploads': [],
        'response': None,
        'metadata_store': {},
        'last_prompt': None,
        'retriever': {},
        'query_engine': {}
    }

    for key, default_value in required_keys.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

    # Initialize LLM with default model
    if 'llm' not in st.session_state:
        default_model = get_available_models()[0]
        st.session_state['llm'] = OpenAI(temperature=1.0, model=default_model)
        st.session_state['current_model'] = default_model

def get_available_models():
    models_str = os.getenv('MODELS', 'o3-mini')  # Default to o3-mini if not set
    return models_str.split(',')


def find_document_images(document_id):
    """Find all images associated with a specific document ID."""
    image_paths = []
    
    if not document_id:
        return image_paths
    
    # Search in the images directory for files containing the document ID
    try:
        for file in os.listdir(IMAGES_PATH):
            if document_id in file and os.path.isfile(os.path.join(IMAGES_PATH, file)):
                image_path = os.path.join(IMAGES_PATH, file)
                if os.path.exists(image_path):
                    image_paths.append(image_path)
    except Exception as e:
        print(f"Error searching for document images: {str(e)}")
    
    return image_paths

def create_vector_database(llama_documents, current_pdf_id=None):
    """
    Create a vector database for the given documents.
    
    Args:
        llama_documents: List of documents to index
        current_pdf_id: Optional ID of the current PDF being processed
    """
    client = qdrant_client.QdrantClient(location=":memory:")

    # Create a collection for text data
    client.create_collection(
    collection_name="text_collection",
    vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
    )

    # Create a collection for image data
    client.create_collection(
    collection_name="image_collection",
    vectors_config=VectorParams(size=512, distance=Distance.COSINE)
    )

    # Initialize Collections
    text_store = QdrantVectorStore(
    client=client, collection_name="text_collection"
    )

    image_store = QdrantVectorStore(
    client=client, collection_name="image_collection"
    )

    # Create the MultiModal index
    storage_context = StorageContext.from_defaults(
    vector_store=text_store, image_store=image_store
    )

    # Load images for the current document only
    image_documents = []
    
    if current_pdf_id and 'document_image_map' in st.session_state:
        print(f"\nDEBUG - Checking document_image_map for document ID: {current_pdf_id}")
        # Load images from document_image_map
        if current_pdf_id in st.session_state['document_image_map']:
            paths = st.session_state['document_image_map'][current_pdf_id]
            print(f"DEBUG - Found {len(paths)} images in document_image_map")
            for img_path in paths:
                print(f"DEBUG - Checking image: {img_path}, exists: {os.path.exists(img_path)}")
                if os.path.exists(img_path):
                    try:
                        img_docs = SimpleDirectoryReader(input_files=[img_path]).load_data()
                        image_documents.extend(img_docs)
                        print(f"DEBUG - Successfully loaded image: {img_path}")
                    except Exception as e:
                        print(f"DEBUG - Error loading image {img_path}: {str(e)}")
        else:
            print(f"DEBUG - Document ID {current_pdf_id} not found in document_image_map")
    
    print(f"DEBUG - Total images loaded for vectorstore: {len(image_documents)}")
    
    index = MultiModalVectorStoreIndex.from_documents(
        llama_documents + image_documents,
        storage_context=storage_context
        )

    keyword_index = SimpleKeywordTableIndex.from_documents(
        llama_documents,
        storage_context=storage_context)
    
    return index, keyword_index

def create_index_from_pdf(pdf_data):
    # Generate a unique ID for this PDF
    pdf_id = str(uuid.uuid4())
    temp_file = f"tmp_assets/tmp_files/temp_{pdf_id}.pdf"
    with open(temp_file, "wb") as f:
        f.write(pdf_data)
    
    # Store images separately in session state
    if 'pdf_images' not in st.session_state:
        st.session_state['pdf_images'] = {}
    
    # Store the document ID for tracking purposes
    if 'document_image_map' not in st.session_state:
        st.session_state['document_image_map'] = {}

    # Create index with minimal metadata using the meta_filter function.
    docs = pymupdf4llm.to_markdown(doc=temp_file,
                                   write_images=True,
                                   image_path=IMAGES_PATH,
                                   image_format = "jpg",
                                   dpi = 200,
                                   page_chunks=True,
                                   extract_words=True)
    
    # Track image paths for this document
    image_paths = []

    llama_documents = []

    for i,document in enumerate(docs):
        # Track images associated with this document
        if document.get("images"):
            for image in document.get("images"):
                if "path" in image:
                    image_paths.append(image["path"])
                    
        # Extract metadata
        metadata = {
            "page": str(document["metadata"].get("page")),
            "images": str(document.get("images")),
            "toc_items": str(document.get("toc_items")),
            "title": str(document["metadata"].get("title")),
            "author": str(document["metadata"].get("author")),
            "keywords": str(document["metadata"].get("keywords")),
            "document_id": pdf_id,  # Add document ID to track which document this is from
        }

        # Create a Document object with just the text and the cleaned metadata
        llama_document = Document(
            text=document["text"],
            metadata=metadata,
            text_template="Metadata: {metadata_str}\n-----\nContent: {content}",
        )

        llama_documents.append(llama_document)
    
    # Store the image paths for this document
    st.session_state['document_image_map'][pdf_id] = image_paths
    
    # Get the indexes from create_vector_database, passing the current PDF ID
    multi_index, keyword_index = create_vector_database(llama_documents, pdf_id)
    
    # Return all three values: multi_index, keyword_index, and pdf_id
    return multi_index, keyword_index, pdf_id


def query_document(prompt, file_name):

    #if not st.session_state.chat_engine.get(file_name):
    #    st.session_state.chat_engine[file_name] = st.session_state['indexes'][file_name].as_chat_engine(system_prompt=GENERAL_CHAT_PROMPT,
    #                                                                                                    chat_mode="condense_plus_context")
        
    if not st.session_state.retriever.get(file_name):
        st.session_state.retriever[file_name] = {}
        # Increase image_similarity_top_k to retrieve more images
        st.session_state.retriever[file_name]['vector'] = st.session_state['indexes'][file_name]['multi'].as_retriever(
            similarity_top_k=3,
            image_similarity_top_k=3  # Retrieve more images
        )
        keyword_retriever = st.session_state['indexes'][file_name]['keywords'].as_retriever(retriever_mode="simple")
        
        # Get the document ID for the current file
        current_doc_id = st.session_state.get('file_document_id', {}).get(file_name)
        
        # Create custom hybrid retriever that combines vector and keyword retrieval
        st.session_state.retriever[file_name]['custom'] = CustomRetriever(
            vector_retriever=st.session_state.retriever[file_name]['vector'],
            keyword_retriever=keyword_retriever,
            mode="OR"  # Use OR mode to get union of both retrievers
        )

        # define response synthesizer with the appropriate prompt template
        # Use citation prompt or general knowledge prompt based on toggle
        if st.session_state.get('answer_mode', False):
            # Document-only mode with strict citations
            template = PromptTemplate(CITATION_CHAT_PROMPT)
            # Remove structured_answer_filtering as it's causing errors
            response_synthesizer = get_response_synthesizer(
                text_qa_template=template,
                verbose=True  # Show response generation details in logs
            )
        else:
            # General knowledge mode with optional citations
            template = PromptTemplate(GENERAL_CHAT_PROMPT)
            response_synthesizer = get_response_synthesizer(text_qa_template=template)

        # assemble query engine
        st.session_state.query_engine[file_name] = RetrieverQueryEngine(
            retriever=st.session_state.retriever[file_name]['custom'],  # Use the custom retriever
            response_synthesizer=response_synthesizer,
        )

    # Temporarily adjust LLM temperature when in citation mode for better citation generation
    original_temperature = st.session_state['llm'].temperature
    if st.session_state.get('answer_mode', False):
        # Temporarily increase temperature to encourage more diverse responses with citations
        st.session_state['llm'].temperature = 0.7
    
    # Get the synthesized response from the query engine
    response = st.session_state.query_engine[file_name].query(prompt)
    synthesized_answer = str(response)  # Convert response object to string
    
    # Restore original temperature
    st.session_state['llm'].temperature = original_temperature
    
    # The retriever returns a list of nodes
    source_nodes = st.session_state.retriever[file_name]['vector'].retrieve(prompt)
    
    # Check if the response contains citations when in citation mode
    if st.session_state.get('answer_mode', False):
        citations = extract_citation_indices(synthesized_answer)
        if not citations:
            print("WARNING: Response does not contain citations even though citation mode is enabled!")
            
            # Generate a citation for the response based on the first source
            if source_nodes and len(source_nodes) > 0:
                # Get original answer
                original_answer = synthesized_answer
                
                # Get the first retrieved source to use as a citation
                first_source = source_nodes[0]
                # Extract page number if available
                page_info = ""
                if hasattr(first_source, 'metadata') and 'page' in first_source.metadata:
                    page_info = f" (page {first_source.metadata['page']})"
                
                # Modify the answer to include a citation
                synthesized_answer = f"{original_answer} [1]{page_info}\n\n[Note: Added citation [1] to reference the source of this information]"

    # Get the document ID for the current file
    current_doc_id = st.session_state.get('file_document_id', {}).get(file_name)
    
    # Extract any images from the source nodes - ONLY from retriever results
    images = []
    print("\nDEBUG - Looking for images in source nodes")
    print(f"Current document ID: {current_doc_id}")
    
    # Look for images in the text chunks
    image_references = []
    print(f"\nDEBUG - Looking for image references in text nodes")
    print(f"Current document ID: {current_doc_id}")
    
    # Get all available image paths for this document
    available_images = st.session_state.get('document_image_map', {}).get(current_doc_id, [])
    print(f"Available images for this document: {len(available_images)}")
    for img in available_images:
        print(f"Image: {img}")
    
    # Process all text nodes to find image references in their metadata
    for source in source_nodes:
        if hasattr(source, 'metadata'):
            # Get the page number from the node metadata
            page_num = source.metadata.get('page', None)
            print(f"Processing node with page: {page_num}")
            
            # Check for image references in the metadata
            if 'images' in source.metadata and source.metadata['images']:
                images_data = source.metadata['images']
                print(f"Found images data on page {page_num}: {type(images_data)}")
                
                # Handle different formats of the images data
                image_list = []
                if isinstance(images_data, str):
                    # Try to clean and parse the string representation
                    try:
                        # Clean up the string representation to make it valid JSON
                        import json
                        import re
                        
                        # If it's a simple string, just use it as is
                        if re.match(r'^\[\s*\{.*\}\s*\]$', images_data, re.DOTALL):
                            try:
                                image_list = json.loads(images_data)
                                print(f"Successfully parsed image list from string")
                            except json.JSONDecodeError as e:
                                print(f"JSON parsing error: {e}")
                    except Exception as e:
                        print(f"Error processing image metadata: {e}")
                elif isinstance(images_data, list):
                    # It's already a list, use it directly
                    image_list = images_data
                
                print(f"Processed {len(image_list)} image metadata items")
                
                # Process each image metadata item in the list
                for img_meta in image_list:
                    # Skip if not a dictionary
                    if not isinstance(img_meta, dict):
                        print(f"Skipping non-dictionary image metadata: {img_meta}")
                        continue
                    
                    # Use both the number and bounding box for more precise matching
                    if 'number' in img_meta and 'bbox' in img_meta:
                        img_number = img_meta['number']
                        bbox = img_meta['bbox']
                        print(f"Image number: {img_number}, bbox: {bbox}")
                        
                        # Find images for the specific page number
                        if page_num:
                            # Format is usually: temp_{doc_id}.pdf-{page}-{index}.jpg
                            img_pattern = f"{current_doc_id}.pdf-{page_num}-"
                            print(f"Looking for images matching: {img_pattern}")
                            
                            # Find matching images in available_images
                            matches = [img for img in available_images if img_pattern in img]
                            
                            if matches:
                                # Look for the closest match by image index
                                # In PDF extraction, the image index often corresponds to the order it appears on the page
                                best_match = None
                                if len(matches) == 1:
                                    best_match = matches[0]
                                else:
                                    # Try to find by index at the end of filename (e.g., -0.jpg)
                                    for img_path in matches:
                                        # Extract the index from the filename
                                        try:
                                            # Format: temp_X.pdf-Y-Z.jpg - need to extract Z
                                            idx_part = img_path.split('-')[-1].split('.')[0]
                                            idx = int(idx_part)
                                            # If this index matches our image number or is close, use it
                                            if idx == img_number or abs(idx - img_number) <= 1:
                                                best_match = img_path
                                                break
                                        except:
                                            pass
                                    
                                    # If we couldn't find a match by index, just use the first one
                                    if not best_match and matches:
                                        best_match = matches[0]
                                
                                if best_match and os.path.exists(best_match):
                                    print(f"Best matching image: {best_match}")
                                    # Add this image to our list of images to display
                                    image_info = {
                                        'path': best_match,
                                        'caption': f"Image from page {page_num}"
                                    }
                                    # Avoid duplicates
                                    if not any(img['path'] == best_match for img in images):
                                        images.append(image_info)
                                        print(f"Added image to response: {best_match}")
                            else:
                                print(f"No images matched pattern: {img_pattern}")
    
    print(f"Total images for response: {len(images)}")
    
    return {
        'answer': synthesized_answer,  # Use the synthesized answer with citation warnings if needed
        'sources': source_nodes,
        'images': images  # Add images to the response
    }

def prepare_source_highlight(source):
    # Get ref_id from source metadata
    ref_id = source.node.metadata.get('ref_id')
    page = source.node.metadata.get('page', 0)
    source_text = source.node.text.strip()
    
    # Retrieve stored metadata using ref_id
    stored_meta = st.session_state['metadata_store'].get(ref_id, {})
    text_spans = stored_meta.get("text_spans", [])
    
    if not text_spans:
        return None

    # Find spans that contain parts of the source text
    relevant_spans = []
    words = set(source_text.split())
    min_word_match = 3  # Minimum words that must match to consider span relevant
    
    for span in text_spans:
        span_words = set(span["text"].strip().split())
        # Check for significant word overlap
        if len(words.intersection(span_words)) >= min_word_match:
            relevant_spans.append(span)
    
    if not relevant_spans:
        return None

    # Create bounding box for relevant spans
    x0 = min(span["bbox"][0] for span in relevant_spans)
    y0 = min(span["bbox"][1] for span in relevant_spans)
    x1 = max(span["bbox"][2] for span in relevant_spans)
    y1 = max(span["bbox"][3] for span in relevant_spans)
    
    return {
        'page': page,
        'x': x0,
        'y': y0,
        'width': x1 - x0,
        'height': y1 - y0,
        'color': "red",
    }

def create_annotations_from_sources(answer_text, sources):
    citations = extract_citation_indices(answer_text)
    annotations = []
    for idx in citations:
        if idx <= len(sources):
            source = sources[idx-1]  # Convert 1-based citation to 0-based index
            annotation = prepare_source_highlight(source)
            if annotation:
                annotations.append(annotation)
    return annotations

def extract_citation_indices(answer_text: str):
    # This regex returns a list of citation numbers found in the answer (as strings)
    return [int(x) for x in re.findall(r'\[(\d+)\]', answer_text)]


def display_pdf(annotations):
    """
    Displays a selected PDF file with annotated sections.

    Parameters:
    - annotations: A list of annotations to apply to the displayed PDF.
    """
    with st.session_state['column_pdf']:
        pdf_viewer(input=st.session_state['doc_binary_data'][st.session_state['selected_file_name'][-1]],
                    annotations=annotations,
                    annotation_outline_size=2,
                    height=1000)
        
def process_uploaded_files():
    """
    Processes and stores the content of uploaded PDF files into a session state.
    Updates the session state with metadata, binary data, chunk data, and text data for each uploaded PDF.
    """
    placeholder_info_1 = st.empty()
    placeholder_info_2 = st.empty()
    placeholder_info_1.info("Processing uploaded files...")
    st.session_state['doc_binary_data'] = {}
    st.session_state['selected_file_name'] = []
    for file in st.session_state['uploaded_pdf_files']:
        # Store binary data of the file
        st.session_state['retriever'][file.name] = None # We want a separate retriever for each file
        st.session_state['selected_file_name'].append(file.name) # For now we will use only one file
        st.session_state['conversation_histories'][file.name] = [] # Start new conversation for this file
        st.session_state['doc_binary_data'][st.session_state['selected_file_name'][-1]] = file.getvalue()
        pdf_data = st.session_state['doc_binary_data'][st.session_state['selected_file_name'][-1]]
        placeholder_info_2.info(f"Creating index for {file.name}...")
        st.session_state['indexes'][file.name] = {}
        st.session_state['indexes'][file.name]['multi'], st.session_state['indexes'][file.name]['keywords'], doc_id = create_index_from_pdf(pdf_data)
        
        # Store the document ID for this file
        if 'file_document_id' not in st.session_state:
            st.session_state['file_document_id'] = {}
        st.session_state['file_document_id'][file.name] = doc_id
        
        # Explicitly search for images after document processing
        placeholder_info_2.info(f"Finding images for document...")
        
        # Direct search for images based on document ID pattern
        image_paths = find_document_images(doc_id)
        if image_paths:
            # Register images in document_image_map
            if 'document_image_map' not in st.session_state:
                st.session_state['document_image_map'] = {}
            st.session_state['document_image_map'][doc_id] = image_paths
            
            # Try to load these images into SimpleDirectoryReader for better indexing
            try:
                image_docs = []
                for img_path in image_paths:
                    try:
                        docs = SimpleDirectoryReader(input_files=[img_path]).load_data()
                        image_docs.extend(docs)
                    except Exception:
                        pass
                
                if image_docs:
                    # Create a separate image index and add it to the document's indexes
                    image_index = MultiModalVectorStoreIndex.from_documents(image_docs)
                    st.session_state['indexes'][file.name]['images'] = image_index
            except Exception:
                pass
        
        placeholder_info_2.empty()
    placeholder_info_1.success("Files processed successfully.")
    time.sleep(1)
    placeholder_info_1.empty()

def display_chat():
    if not st.session_state['selected_file_name']: return
    current_file = st.session_state['selected_file_name'][-1]
    with st.session_state["column_chat"]:
        if not st.session_state['conversation_histories'].get(current_file):
            st.session_state['conversation_histories'][current_file] = []
        
        # Create a scrollable container for the chat history
        screen_height = streamlit_js_eval(js_expressions='screen.height', key='SCR')
        main_container_dimensions = st_dimensions(key="main")
        height_column_container = int(screen_height * 0.6) if main_container_dimensions else 400
        chat_container = st.container(height=height_column_container)

        current_file = st.session_state['selected_file_name'][-1]
        
        # Display chat messages
        for message in st.session_state['conversation_histories'][current_file]:
            with chat_container:
                with st.chat_message(message["role"]):
                    st.write(message["content"])
                    
                    # Display images if available in history
                    if message.get("images"):
                        with st.expander("Images from Document"):
                            for img_info in message["images"]:
                                try:
                                    image_path = img_info['path']
                                    if os.path.exists(image_path):
                                        st.image(image_path, caption=img_info['caption'])
                                    else:
                                        st.warning(f"Image not found at path: {image_path}")
                                except Exception as e:
                                    st.error(f"Error displaying image: {str(e)}")
                                    st.code(f"Image path: {img_info['path']}\nException: {str(e)}")
                    
                    if message.get("sources"):
                        with st.expander("Source Information"):
                            for source in message["sources"]:
                                st.text(source)
        
        # Chat input
        if prompt := st.chat_input(f"Ask something about your Documents ({st.session_state['current_model']})"):
            try:
                st.session_state['last_prompt'] = prompt
                with chat_container:
                    with st.chat_message("user"):
                        st.markdown(prompt)
    
                # Add user message to history
                st.session_state['conversation_histories'][current_file].append(
                    {"role": "user", "content": prompt}
                )
                with chat_container:
                    with st.spinner("Processing your question..."):
                        # Get response from LLM
                        st.session_state['response'] = query_document(prompt, current_file)

                        with st.chat_message("assistant"):
                            answer = st.session_state['response']['answer']
                            st.markdown(answer)
                            sources = []
                            
                            # Display images if any are available
                            if 'images' in st.session_state['response'] and st.session_state['response']['images']:
                                print(f"DEBUG - Chat display: Found {len(st.session_state['response']['images'])} images to display")
                                with st.expander("Images from Document"):
                                    for img_info in st.session_state['response']['images']:
                                        try:
                                            # Check if image exists and display it
                                            image_path = img_info['path']
                                            print(f"DEBUG - Displaying image: {image_path}, exists: {os.path.exists(image_path)}")
                                            if os.path.exists(image_path):
                                                st.image(image_path, caption=img_info['caption'])
                                                # Add image info to sources for chat history
                                                sources.append(f"Image: {img_info['caption']}")
                                            else:
                                                st.warning(f"Image not found at path: {image_path}")
                                                sources.append(f"Image (not found): {img_info['caption']}")
                                        except Exception as e:
                                            st.error(f"Error displaying image: {str(e)}")
                                            st.code(f"Image path: {img_info['path']}\nException: {str(e)}")
                            else:
                                print("DEBUG - No images to display in chat")
                            
                            with st.expander("Source Information"):
                                # Extract citation markers from the answer (e.g. "[2]" will give [2])
                                citation_numbers = extract_citation_indices(answer)
                                
                                if citation_numbers:
                                    # Display only the sources that are actually cited in the response
                                    displayed_sources = set()
                                    
                                    for citation_num in sorted(citation_numbers):
                                        source_index = citation_num - 1  # Convert 1-based citation to 0-based index
                                        
                                        try:
                                            if source_index in displayed_sources:
                                                continue  # Skip if already displayed this source
                                                
                                            if source_index < len(st.session_state['response']['sources']):
                                                source = st.session_state['response']['sources'][source_index]
                                                
                                                # Get metadata - handle different source object structures gracefully
                                                try:
                                                    # Handle the normal source object structure (with node attribute)
                                                    if hasattr(source, 'node'):
                                                        page_num = source.node.metadata.get('page', 'N/A')
                                                        text = source.node.text.strip()
                                                    # Handle direct node objects
                                                    elif hasattr(source, 'metadata') and hasattr(source, 'text'):
                                                        page_num = source.metadata.get('page', 'N/A')
                                                        text = source.text.strip()
                                                    # Handle unexpected source types
                                                    else:
                                                        page_num = 'Unknown'
                                                        text = str(source) if source is not None else 'No text available'
                                                except Exception as e:
                                                    st.error(f"Error processing source: {str(e)}")
                                                    page_num = 'Error'
                                                    text = f"Could not extract source text: {str(e)}"
                                                
                                                # Format the source elegantly with markdown
                                                st.markdown(f"### Source [{citation_num}]")
                                                st.markdown(f"**Page:** {page_num}")
                                                
                                                # Format the text in a code block for better readability
                                                st.markdown("**Text:**")
                                                st.markdown(f"```\n{text}\n```")
                                                
                                                # Add horizontal rule between sources
                                                if citation_num != sorted(citation_numbers)[-1]:
                                                    st.markdown("---")
                                                    
                                                # Add to tracking set and sources list for history
                                                displayed_sources.add(source_index)
                                                sources.append(f"Source [{citation_num}] (Page {page_num}):\n{text}")
                                                
                                        except IndexError:
                                            st.warning(f"Citation [{citation_num}] does not match any available source.")
                                else:
                                    st.info("No source citations were found in this response.")
                            
                        
                        # Add assistant response to history
                        history_entry = {
                            "role": "assistant",
                            "content": st.session_state['response']['answer'],
                            "sources": sources
                        }
                        
                        # Add image paths to history if available
                        if 'images' in st.session_state['response'] and st.session_state['response']['images']:
                            history_entry["images"] = st.session_state['response']['images']
                            
                        st.session_state['conversation_histories'][current_file].append(history_entry)
            except Exception as e:
                st.error(f"Error processing request: {str(e)}")
    

initialize_variables()
change_chatbot_style()

with st.sidebar:
    col1, col2, col3 = st.columns([1, 2, 1])

    # Use the middle column to display the logo
    with col2:
        st.image("assets/img/logo.svg", width=100)
    st.markdown("""---""")


    uploaded_files = st.file_uploader("**Upload PDF file(s)**",
                        type=['pdf'],
                        accept_multiple_files=True,
                        key='uploaded_pdf_files',
                        disabled=upload_disabled
                        )
    
if st.session_state.get("uploaded_pdf_files"):
    current_files = set(f.name for f in uploaded_files)
    previous_files = set(st.session_state.get('previous_uploads', []))
    
    if current_files != previous_files:
        process_uploaded_files()
        # Store current upload names for comparison
        st.session_state['previous_uploads'] = list(current_files)

# Add model selection
available_models = get_available_models()

with st.sidebar:
    selected_model = st.selectbox(
        "Select Model",
        options=available_models,
        index=0,
        key='selected_model'
    )

    # Update LLM when model changes
    if 'current_model' not in st.session_state or st.session_state['current_model'] != selected_model:
        st.session_state['llm'] = OpenAI(temperature=1.0, model=selected_model)
        st.session_state['current_model'] = selected_model

    answer_mode = st.toggle("Strict citation mode (requires [#] citations)", key='answer_mode', help="Toggle ON to force responses to include numbered citations to source documents. Toggle OFF to allow general knowledge with optional citations.")


st.session_state["column_pdf"], st.session_state["column_chat"] = st.columns([50, 50], gap="medium")

with st.session_state["column_pdf"]:
    if st.session_state.get("selected_file_name"):
        if st.session_state.get('response'):
            annotations = create_annotations_from_sources(
                st.session_state['response']['answer'],
                st.session_state['response']['sources']
                )
        else: annotations = []
        display_pdf(annotations)
    else:
        st.header("Please upload your documents on the sidebar.")

display_chat()