"""
UI layouts for the Chat with Docs application.
"""

import os
import streamlit as st
from streamlit_pdf_viewer import pdf_viewer
from streamlit_js_eval import streamlit_js_eval
from streamlit_dimensions import st_dimensions

from ..utils.logger import Logger
from ..utils.source import format_source_for_display
from ..utils.i18n import I18n
from ..utils.ragflow_common import get_available_ragflow_assistants, set_selected_ragflow_assistant, get_assistant_documents, get_assistant_dataset_names
from .components import (
    display_document_info, display_document_images,
)
from .handlers import handle_query_submission

def render_sidebar() -> None:
    """Render the sidebar with chat assistant selection and knowledge base documents."""
    with st.sidebar:
        # Chat Assistant selection
        st.header("Chat Assistant")
        try:
            available_assistants = get_available_ragflow_assistants()
            if available_assistants:
                assistant_names = [assistant.get('name', 'Unnamed Assistant') for assistant in available_assistants]
                assistant_ids = [assistant.get('id') for assistant in available_assistants]
                
                # Get current selection
                current_selection = st.session_state.get('selected_ragflow_assistant')
                current_index = 0
                if current_selection and current_selection in assistant_ids:
                    current_index = assistant_ids.index(current_selection)
                
                selected_name = st.selectbox(
                    "Select Chat Assistant",
                    assistant_names,
                    index=current_index,
                    key='ragflow_assistant_selector',
                    help="Choose from your configured RAGFlow chat assistants"
                )
                
                # Store the actual assistant ID
                if selected_name:
                    selected_index = assistant_names.index(selected_name)
                    selected_assistant_id = assistant_ids[selected_index]
                    set_selected_ragflow_assistant(selected_assistant_id)
                    
                    # Show assistant's knowledge base documents
                    st.subheader("Knowledge Base Documents")
                    
                    # Get documents from assistant's datasets
                    assistant_documents = get_assistant_documents()
                    dataset_names = get_assistant_dataset_names()
                    
                    if assistant_documents:
                        # Create a scrollable container for the document list
                        sidebar_screen_height = streamlit_js_eval(js_expressions='screen.height', key='sidebar_height')
                        sidebar_max_height = int(sidebar_screen_height * 0.4) if sidebar_screen_height else 400
                        container_height = min(sidebar_max_height, 60 * len(assistant_documents))
                        
                        doc_list_container = st.container(height=container_height)
                        st.caption(f"{len(assistant_documents)} documents available")
                        
                        with doc_list_container:
                            for doc in assistant_documents:
                                doc_name = doc.get('name', 'Unnamed Document')
                                dataset_id = doc.get('dataset_id', '')
                                dataset_name = dataset_names.get(dataset_id, f'Dataset {dataset_id}')
                                
                                # Create columns for document info
                                col1, col2 = st.columns([3, 1])
                                
                                # Check if this is the current document
                                is_current = doc_name == st.session_state.get('current_file', '')
                                
                                # Document selection button
                                button_label = f"📄 {doc_name}"
                                if is_current:
                                    button_label = f"📌 {doc_name}"
                                
                                if col1.button(button_label, key=f"ragflow_doc_{doc.get('id')}",
                                             use_container_width=True,
                                             help=f"From {dataset_name}"):
                                    st.session_state.current_file = doc_name
                                    st.session_state.current_ragflow_doc = doc
                                    st.rerun()
                                
                                # Show dataset info
                                col2.caption(f"📚 {dataset_name}")
                                
                                st.divider()
                    else:
                        st.info("No documents found in this assistant's knowledge base.")
            else:
                st.warning("⚠️ No chat assistants available. Please create chat assistants in your RAGFlow instance.")
        except Exception as e:
            st.error(f"❌ Error loading chat assistants: {str(e)}")
            st.info("Please check your RAGFlow connection and configuration.")
        
        # Settings section
        st.header(I18n.t('settings'))
        
        # Language selection
        I18n.render_language_selector()
                


def render_main_content() -> None:
    """Render the main content area with chat interface and document viewer."""
    # Check if we have a selected assistant and current file
    selected_assistant = st.session_state.get('selected_ragflow_assistant')
    current_file = st.session_state.get('current_file')
    
    if not selected_assistant:
        st.info("👋 Please select a chat assistant from the sidebar to start chatting with documents.")
        return
    
    if not current_file:
        st.info("📄 Please select a document from the assistant's knowledge base to start chatting.")
        return
    
    # Get current RAGFlow document info
    current_ragflow_doc = st.session_state.get('current_ragflow_doc', {})
    
    # Display document information
    st.subheader(f"💬 Chatting with: {current_file}")
    
    # Show document metadata
    if current_ragflow_doc:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.caption(f"📄 **Document:** {current_ragflow_doc.get('name', 'Unknown')}")
        with col2:
            st.caption(f"📚 **Dataset:** {current_ragflow_doc.get('dataset_id', 'Unknown')}")
        with col3:
            chunk_count = current_ragflow_doc.get('chunk_count', 0)
            st.caption(f"🧩 **Chunks:** {chunk_count}")
    
    # Split the display into two columns - one for PDF and one for content tabs
    pdf_column, content_column = st.columns([50, 50], gap="medium")
    
    # Display PDF in the left column
    with pdf_column:
        # Try to get PDF data from RAGFlow
        pdf_data = None
        
        # Check if we have cached PDF data
        pdf_cache_key = f"ragflow_pdf_{current_file}"
        if pdf_cache_key in st.session_state:
            pdf_data = st.session_state[pdf_cache_key]
        elif current_ragflow_doc:
            # Download PDF from RAGFlow
            try:
                with st.spinner("Loading PDF from RAGFlow..."):
                    from ..ragflow_client import create_client
                    client = create_client()
                    
                    dataset_id = current_ragflow_doc.get('dataset_id')
                    doc_id = current_ragflow_doc.get('id')
                    
                    if dataset_id and doc_id:
                        response = client._make_request('GET', f'/api/v1/datasets/{dataset_id}/documents/{doc_id}')
                        if response.status_code == 200:
                            pdf_data = response.content
                            # Cache the PDF data
                            st.session_state[pdf_cache_key] = pdf_data
                            Logger.info(f"Successfully downloaded PDF for {current_file}")
                        else:
                            st.error(f"Failed to download PDF: {response.status_code}")
                    else:
                        st.error("Document ID or Dataset ID not available")
            except Exception as e:
                st.error(f"Error downloading PDF: {str(e)}")
        
        if pdf_data:
            # Get annotations for this document's chat history
            annotations = []
            
            # Check if we have a document-specific response with sources and answer
            if (current_file in st.session_state.get('document_responses', {}) and
                st.session_state.document_responses[current_file] and
                'sources' in st.session_state.document_responses[current_file] and
                'answer' in st.session_state.document_responses[current_file]):
                
                # Import the function to create annotations from sources
                from ..utils.source import create_annotations_from_sources
                
                # Create annotations based on the document-specific response
                doc_response = st.session_state.document_responses[current_file]
                citation_mapping = doc_response.get('citation_mapping', {})

                annotations = create_annotations_from_sources(
                    doc_response['answer'],
                    doc_response['sources'],
                    citation_mapping
                )
                Logger.info(f"Created {len(annotations)} annotations for document {current_file}")
            
            # Create PDF viewer component with responsive height
            screen_height = streamlit_js_eval(js_expressions='screen.height', key='pdf_screen_height')
            pdf_height = int(screen_height * 0.8) if screen_height else 900  # Increased height
            
            # Define a simple annotation click handler
            def annotation_click_handler(annotation):
                """Handle clicks on source annotations in the PDF viewer."""
                page = annotation.get('page', 'unknown')
                Logger.info(f"Annotation clicked on page {page}")
                # No further action required
            
            pdf_viewer(
                pdf_data,
                height=pdf_height,
                annotations=annotations,
                annotation_outline_size=5,  # Make outlines more visible
                on_annotation_click=annotation_click_handler
            )
        else:
            st.info("📄 PDF will be loaded when available from RAGFlow")
    
    # Create a scrollable container for the chat with dynamic height
    screen_height = streamlit_js_eval(js_expressions='screen.height', key='screen_height')
    main_container_dimensions = st_dimensions(key="main")
    
    # Reserve space for chat input and suggestions - reduce chat container height significantly
    # This ensures the chat input is always visible
    height_column_container = int(screen_height * 0.35) if main_container_dimensions else 300
    
    # Tabbed content in the right column
    with content_column:
        # Create tabs
        chat_tab, info_tab, images_tab = st.tabs([I18n.t('chat'), I18n.t('document_info'), I18n.t('images')])

        # Calculate images container height (0.6 * screen_height)
        images_container_height = int(screen_height * 0.4) if main_container_dimensions else 500

        # Chat tab - contains the chat interface
        with chat_tab:
            # Add clear chat button above the chat container
            current_file = st.session_state.get('current_file')
            has_chat_history = (current_file and
                               current_file in st.session_state.get('chat_history', {}) and
                               len(st.session_state.chat_history[current_file]) > 0)
            
            if has_chat_history:
                if st.button(I18n.t('clear_chat'), key="clear_chat_main", help=I18n.t('clear_chat_help')):
                    # Reset chat history for current file
                    st.session_state.chat_history[current_file] = []
                    st.rerun()
            
            # Create a scrollable container for chat with reduced height to ensure input visibility
            chat_container = st.container(height=height_column_container)

            # Display chat history
            with chat_container:
                if current_file in st.session_state.chat_history:
                    for msg in st.session_state.chat_history[current_file]:
                        with st.chat_message(msg["role"]):
                            st.markdown(msg["content"])

                            # Get citation numbers for this message
                            citation_numbers = msg.get("citations", [])
                            
                            # We only want to display the sources for the citations present in the answer.
                            if citation_numbers:
                                # Display sources if this is an assistant message with sources
                                if msg["role"] == "assistant" and msg.get("sources"):
                                    with st.expander(I18n.t('show_sources')):
                                        # Only display sources that are actually cited in the response
                                        displayed_sources = set()
                                        
                                        # Only proceed if we have a citation mapping
                                        if "citation_mapping" in msg:
                                            for citation_num in sorted(citation_numbers):
                                                # Get the original source index from the mapping
                                                if str(citation_num) in msg["citation_mapping"]:
                                                    original_source_index = msg["citation_mapping"][str(citation_num)]
                                                    
                                                    if original_source_index in displayed_sources:
                                                        continue  # Skip if already displayed this source
                                                    
                                                    if original_source_index < len(msg["sources"]):
                                                        # Get the source using the original index
                                                        source = msg["sources"][original_source_index]
                                                        
                                                        # DEBUG: Log full source text before formatting
                                                        try:
                                                            full_text = getattr(source, 'text', '')
                                                            Logger.info(f"Full source text (len={len(full_text)}): {full_text[:500].replace('\n', ' ')}")
                                                        except Exception as e:
                                                            Logger.warning(f"Error logging full source text: {e}")
                                                        
                                                        # Extract page number for prominent label
                                                        try:
                                                            if isinstance(source, dict):
                                                                # RAGFlow format: source is a dict with metadata dict
                                                                page_num = source.get('metadata', {}).get('page', 'N/A')
                                                            elif hasattr(source, 'node'):
                                                                # LlamaIndex format
                                                                page_num = source.node.metadata.get('page', 'N/A')
                                                            elif hasattr(source, 'metadata') and hasattr(source, 'text'):
                                                                # Alternative LlamaIndex format
                                                                page_num = source.metadata.get('page', 'N/A')
                                                            else:
                                                                page_num = 'Unknown'
                                                        except Exception:
                                                            page_num = 'Error'
                                                        
                                                        # Get raw source text
                                                        source_text = format_source_for_display(source)
                                                        
                                                        # Display prominent citation label
                                                        st.markdown(f"##### **{I18n.t('source_citation', citation=citation_num, page=page_num)}**")
                                                        # Display raw source content as plain text/code block
                                                        st.code(source_text)
                                                        displayed_sources.add(original_source_index)
                                                else:
                                                    Logger.warning(f"Citation number {citation_num} not found in mapping")
                                        else:
                                            st.warning(I18n.t('citation_mapping_not_available'))
                                        # Add separator between sources
                                        if len(displayed_sources) < len(citation_numbers):
                                            st.divider()
                                                
                                # Display images if present
                                if msg["role"] == "assistant" and msg.get("images") and len(msg["images"]) > 0:
                                    Logger.info(f"Displaying {len(msg['images'])} images in message")
                                    with st.expander(I18n.t('view_images'), expanded=False):
                                        # Create a grid layout for images (2 columns)
                                        cols = st.columns(2)
                                        for i, img_info in enumerate(msg["images"]):
                                            with cols[i % 2]:
                                                try:
                                                    # Check if image exists
                                                    if os.path.exists(img_info['file_path']):
                                                        # Read the image file as binary data
                                                        with open(img_info['file_path'], 'rb') as f:
                                                            img_bytes = f.read()
                                                        page_num = img_info.get('page', 'unknown')
                                                        meta_caption = img_info.get('caption', '')
                                                        if meta_caption:
                                                            caption = I18n.t('image_from_page_with_caption', page=page_num, caption=meta_caption)
                                                        else:
                                                            caption = I18n.t('image_from_page', page=page_num)
                                                        st.image(img_bytes, caption=caption)
                                                    else:
                                                        Logger.warning(f"Image file not found: {img_info['file_path']}")
                                                        st.warning(f"Image file not found: {os.path.basename(img_info['file_path'])}")
                                                except Exception as e:
                                                    Logger.error(f"Error displaying image {img_info['file_path']}: {e}")
                                                    st.warning(f"Error displaying image: {os.path.basename(img_info['file_path']) if 'file_path' in img_info else 'Unknown'}")
            
            # Display query suggestions as pills if available (but not for scanned documents)
            # In RAGFlow, we use the document ID from current_ragflow_doc
            current_ragflow_doc = st.session_state.get('current_ragflow_doc', {})
            current_doc_id = current_ragflow_doc.get('id', '')
            
            # Display query suggestions if available
            if (
                'document_query_suggestions' in st.session_state and
                current_doc_id in st.session_state.get('document_query_suggestions', {}) and
                st.session_state['document_query_suggestions'][current_doc_id]
            ):
                # Get suggestions for this document
                suggestions = st.session_state['document_query_suggestions'][current_doc_id]
                
                if suggestions:
                    # Display suggestions as pills
                    try:
                        # Use the help parameter to show the full suggestion text on hover
                        help_text = "Available suggestions:\n" + "\n".join([f"• {suggestion}" for suggestion in suggestions])
                        
                        selected_suggestion = st.pills(
                            label=I18n.t('query_suggestions'),
                            options=suggestions,
                            selection_mode="single",
                            help=help_text
                        )
                        
                        # If a suggestion is selected
                        if selected_suggestion:
                            # Use the selected suggestion as the prompt
                            prompt = selected_suggestion
                            
                            # Remove the selected suggestion from the list
                            suggestions.remove(selected_suggestion)
                            st.session_state['document_query_suggestions'][current_doc_id] = suggestions
                            
                            # Process the suggestion
                            # Call the query submission handler
                            handle_query_submission(prompt, current_file, chat_container)
                            st.rerun()
                    except Exception as e:
                        Logger.error(f"Error displaying suggestions: {e}")
                        
            # Chat input
            user_query = st.chat_input(I18n.t('type_question_here'))
            if user_query:
                handle_query_submission(user_query, current_file, chat_container)
                st.rerun()
        
        # Information tab
        with info_tab:
            display_document_info(current_file)
        
        # Images tab
        with images_tab:
            display_document_images(current_file, container_height=images_container_height)

