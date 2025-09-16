"""
UI layouts for the Chat with Docs application.
"""

import os
import tempfile
import fitz
import streamlit as st
from streamlit_pdf_viewer import pdf_viewer
from streamlit_js_eval import streamlit_js_eval
from streamlit_dimensions import st_dimensions


from ..core.state_manager import StateManager
from ..utils.logger import Logger
from ..utils.source_formatting import format_source_for_display, get_source_page_numbers_for_display, format_page_numbers_for_display
from ..utils.annotations import create_annotations_from_sources
from ..utils.i18n import I18n
from ..utils.ragflow_common import get_available_ragflow_assistants, set_selected_ragflow_assistant, get_assistant_documents, get_assistant_dataset_names, generate_ragflow_query_suggestions, retry_query_suggestions
from ..ragflow_client import create_client
from .components import (
    display_ragflow_document_info, display_ragflow_document_images,
)
from .handlers import handle_query_submission

def render_sidebar() -> None:
    """Render the sidebar with chat assistant selection and knowledge base documents."""
    with st.sidebar:
        # Chat Assistant selection
        st.header(I18n.t('chat_assistant'))
        
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
                    I18n.t('select_chat_assistant'),
                    assistant_names,
                    index=current_index,
                    key='ragflow_assistant_selector',
                    help=I18n.t('chat_assistant_help')
                )
                
                # Store the actual assistant ID
                if selected_name:
                    selected_index = assistant_names.index(selected_name)
                    selected_assistant_id = assistant_ids[selected_index]
                    set_selected_ragflow_assistant(selected_assistant_id)
                    
                    # Show assistant's knowledge base documents
                    st.subheader(I18n.t('knowledge_base_documents'))
                    
                    # Get documents from assistant's datasets
                    assistant_documents = get_assistant_documents()
                    dataset_names = get_assistant_dataset_names()
                    
                    if assistant_documents:
                        # Create a scrollable container for the document list
                        sidebar_screen_height = streamlit_js_eval(js_expressions='screen.height', key='sidebar_height')
                        sidebar_max_height = int(sidebar_screen_height * 0.4) if sidebar_screen_height else 400
                        container_height = min(sidebar_max_height, 60 * len(assistant_documents))
                        
                        doc_list_container = st.container(height=container_height)
                        st.caption(I18n.t('documents_available', count=len(assistant_documents)))
                        
                        with doc_list_container:
                            for i, doc in enumerate(assistant_documents):
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
                                    
                                    # Create the document mapping for annotations
                                    if 'ragflow_document_mapping' not in st.session_state:
                                        st.session_state.ragflow_document_mapping = {}
                                    st.session_state.ragflow_document_mapping[doc.get('id')] = doc_name
                                    Logger.info(f"Created mapping: {doc.get('id')} -> {doc_name}")
                                    
                                    # Generate query suggestions for the selected document (same as LlamaIndex version)
                                    try:
                                        generate_ragflow_query_suggestions(doc)
                                    except Exception as e:
                                        Logger.error(f"Error generating query suggestions: {str(e)}")
                                    
                                    st.rerun()
                                
                                # Show dataset info
                                col2.caption(f"📚 {dataset_name}")
                                
                                # Only add divider if not the last document
                                if i < len(assistant_documents) - 1:
                                    st.divider()
                    else:
                        st.info(I18n.t('no_documents_in_kb'))
            else:
                st.warning(I18n.t('no_chat_assistants'))
                
        except Exception as e:
            error_str = str(e)
            Logger.error(f"Error fetching RAGFlow assistants: {error_str}")
            
            # Check if it's an authentication error
            if 'authentication' in error_str.lower() or 'api key' in error_str.lower() or 'invalid' in error_str.lower():
                st.error(I18n.t('api_authentication_failed'))
            else:
                st.error(I18n.t('error_loading_assistants', error=error_str))
            
            st.info(I18n.t('check_ragflow_connection'))
        
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
        st.info(I18n.t('select_assistant_to_start'))
        return
    
    if not current_file:
        st.info(I18n.t('select_document_to_start'))
        return
    
    # Get current RAGFlow document info
    current_ragflow_doc = st.session_state.get('current_ragflow_doc', {})
    
    # Display document information
    st.subheader(I18n.t('chatting_with', filename=current_file))
    
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
            # Download PDF from RAGFlow using SDK
            try:
                with st.spinner(I18n.t('loading_pdf_from_ragflow')):
                    client = create_client()
                    
                    dataset_id = current_ragflow_doc.get('dataset_id')
                    doc_id = current_ragflow_doc.get('id')
                    
                    if dataset_id and doc_id:
                        # Use RAGFlow SDK to get the document object and download content
                        datasets = client.ragflow.list_datasets()
                        target_dataset = None
                        for dataset in datasets:
                            if dataset.id == dataset_id:
                                target_dataset = dataset
                                break
                        
                        if target_dataset:
                            documents = target_dataset.list_documents()
                            target_doc = None
                            for doc in documents:
                                if doc.id == doc_id:
                                    target_doc = doc
                                    break
                            
                            if target_doc:
                                # Download the document content using SDK
                                pdf_data = target_doc.download()
                                
                                # Validate that we actually got PDF data
                                if pdf_data and isinstance(pdf_data, bytes) and pdf_data.startswith(b'%PDF'):
                                    # Cache the PDF data
                                    st.session_state[pdf_cache_key] = pdf_data
                                    Logger.info(f"Successfully downloaded PDF for {current_file} using SDK (size: {len(pdf_data)} bytes)")
                                    
                                    # Extract page dimensions immediately for annotations
                                    _extract_page_dimensions_immediately(pdf_data, current_ragflow_doc)
                                else:
                                    Logger.error(f"Downloaded data is not a valid PDF (type: {type(pdf_data)}, starts with: {pdf_data[:20] if pdf_data else 'None'})")
                                    st.error("Downloaded file is not a valid PDF document")
                            else:
                                st.error(f"Document {doc_id} not found in dataset")
                        else:
                            st.error(f"Dataset {dataset_id} not found")
                    else:
                        st.error(I18n.t('document_dataset_id_not_available'))
            except Exception as e:
                Logger.error(f"Error downloading PDF using SDK: {str(e)}")
                st.error(I18n.t('error_downloading_pdf', error=str(e)))
        
        if pdf_data:
            # Get annotations for this document's chat history
            annotations = []
            
            # Check if we have a document-specific response with sources and answer
            if (current_file in st.session_state.get('document_responses', {}) and
                st.session_state.document_responses[current_file] and
                'sources' in st.session_state.document_responses[current_file] and
                'answer' in st.session_state.document_responses[current_file]):
                                
                # Create annotations based on the document-specific response
                doc_response = st.session_state.document_responses[current_file]
                citation_mapping = doc_response.get('citation_mapping', {})

                # Get annotation mode from settings (default to "smart")
                annotation_mode = st.session_state.get('annotation_mode', 'smart')
                
                annotations, citation_to_annotation_mapping = create_annotations_from_sources(
                    doc_response['answer'],
                    doc_response['sources'],
                    citation_mapping,
                    current_file,  # Pass current document name to filter sources
                    annotation_mode  # Pass annotation mode
                )
                Logger.info(f"Created {len(annotations)} annotations for document {current_file}")
                
                # Store the mapping for scroll functionality
                st.session_state['citation_to_annotation_mapping'] = citation_to_annotation_mapping
            
            # Create PDF viewer component with responsive height
            screen_height = streamlit_js_eval(js_expressions='screen.height', key='pdf_screen_height')
            pdf_height = int(screen_height * 0.8) if screen_height else 900  # Increased height

            # Define a simple annotation click handler
            def annotation_click_handler(annotation):
                """Handle clicks on source annotations in the PDF viewer."""
                page = annotation.get('page', 'unknown')
                Logger.info(f"Annotation clicked on page {page}")
                # No further action required
            
            # Get scroll to annotation from session state
            scroll_to_annotation = st.session_state.get('scroll_to_annotation', None)
            
            pdf_viewer(
                pdf_data,
                height=pdf_height,
                annotations=annotations,
                annotation_outline_size=5,  # Make outlines more visible
                on_annotation_click=annotation_click_handler,
                scroll_to_annotation=scroll_to_annotation
            )
            
            # Debug logging
            if scroll_to_annotation is not None:
                Logger.info(f"PDF viewer rendered with scroll_to_annotation={scroll_to_annotation}")
        else:
            st.info(I18n.t('pdf_loading'))
    
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
                                            sorted_citations = sorted(citation_numbers)
                                            # Color mapping that matches annotation colors
                                            color_options = ["lightcoral", "lightblue", "lightgreen", "lightsalmon", "plum"]
                                            
                                            # Use the real citation-to-annotation mapping from annotation creation
                                            citation_to_annotation_pos = st.session_state.get('citation_to_annotation_mapping', {})
                                            
                                            for idx, citation_num in enumerate(sorted_citations):
                                                # Use the original citation number from RAGFlow (ID:0 -> 0, ID:1 -> 1, etc.)
                                                display_num = citation_num
                                                
                                                # Debug: Log the mapping
                                                Logger.info(f"Citation mapping: original_id={citation_num}, display_num={display_num}, annotation_pos={citation_to_annotation_pos.get(citation_num)}")
                                                # Get the original source index from the mapping
                                                if str(citation_num) in msg["citation_mapping"]:
                                                    original_source_index = msg["citation_mapping"][str(citation_num)]
                                                    
                                                    if original_source_index in displayed_sources:
                                                        continue  # Skip if already displayed this source
                                                    
                                                    if original_source_index < len(msg["sources"]):
                                                        # Get the source using the original index
                                                        source = msg["sources"][original_source_index]
                                                        
                                                        try:
                                                            full_text = getattr(source, 'text', '')
                                                            Logger.info(f"Full source text (len={len(full_text)}): {full_text[:500].replace('\n', ' ')}")
                                                        except Exception as e:
                                                            Logger.warning(f"Error logging full source text: {e}")
                                                        
                                                        # Extract all page numbers that this source spans
                                                        try:
                                                            page_numbers = get_source_page_numbers_for_display(source)
                                                            page_display = format_page_numbers_for_display(page_numbers)
                                                        except Exception:
                                                            page_display = 'Error'
                                                        
                                                        # Get document name and similarity for nice display
                                                        if isinstance(source, dict):
                                                            doc_name = source.get('metadata', {}).get('document_name', 'Unknown Document')
                                                            similarity = source.get('metadata', {}).get('similarity', 0.0)
                                                        else:
                                                            doc_name = 'Unknown Document'
                                                            similarity = 0.0
                                                        
                                                        # Get the color that matches the annotation (use citation_num for consistency)
                                                        source_color = color_options[citation_num % len(color_options)]
                                                        
                                                        # Create header with citation info and scroll button
                                                        header_col1, header_col2 = st.columns([4, 1])
                                                        
                                                        with header_col1:
                                                            # Create a colored container for the source
                                                            st.markdown(f"""
                                                            <div style="border-left: 4px solid {source_color}; padding-left: 12px; margin: 8px 0;">
                                                                <strong>{display_num}. {doc_name}</strong> (similarity: {similarity:.3f})
                                                            </div>
                                                            """, unsafe_allow_html=True)
                                                        
                                                        with header_col2:
                                                            # Add button to scroll to this annotation
                                                            # Get the stored mapping from session state (created during annotation generation)
                                                            stored_mapping = st.session_state.get('citation_to_annotation_mapping', {})
                                                            annotation_positions = stored_mapping.get(citation_num, [])
                                                            annotation_position = annotation_positions[0] if annotation_positions else None
                                                            
                                                            if annotation_position and st.button("📍", key=f"scroll_to_{citation_num}_{original_source_index}",
                                                                        help=I18n.t('scroll_to_annotation', citation=display_num)):
                                                                # Set the annotation position to scroll to (1-indexed)
                                                                Logger.info(f"Button clicked: citation_num={citation_num}, display_num={display_num}, annotation_position={annotation_position}")
                                                                Logger.info(f"Citation has {len(annotation_positions)} annotations at positions: {annotation_positions}")
                                                                Logger.info(f"Using stored mapping: {stored_mapping}")
                                                                Logger.info(f"Total annotations available: {len(annotations) if 'annotations' in locals() else 'unknown'}")
                                                                st.session_state.scroll_to_annotation = annotation_position
                                                                st.rerun()
                                                        
                                                        if page_display not in ['N/A', 'Error']:
                                                            st.caption(f"📄 {page_display}")
                                                        
                                                        # Always display unified source text
                                                        source_text = format_source_for_display(source)
                                                        st.markdown(f"   {source_text}")
                                                        
                                                        # Add separator between sources, but not after the last one
                                                        if idx < len(sorted_citations) - 1:
                                                            st.markdown("---")  # Add separator between sources
                                                        displayed_sources.add(original_source_index)
                                                else:
                                                    Logger.warning(f"Citation number {citation_num} not found in mapping")
                                        else:
                                            st.warning(I18n.t('citation_mapping_not_available'))
                                                
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
            
            # Display query suggestions as pills if available
            # In RAGFlow, we use the document ID from current_ragflow_doc
            current_ragflow_doc = st.session_state.get('current_ragflow_doc', {})
            current_doc_id = current_ragflow_doc.get('id', '')
            
            # Check if query generation failed for this document
            query_failed = current_doc_id in st.session_state.get('query_suggestion_failures', set())
            
            if query_failed:
                # Show failure message and retry button
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.warning("⚠️ Query suggestions failed to generate properly")
                with col2:
                    if st.button("🔄 Retry", key=f"retry_suggestions_{current_doc_id}", help="Try generating suggestions again"):
                        retry_query_suggestions(current_doc_id, current_ragflow_doc)
                        st.rerun()
            
            # Display query suggestions if available
            elif (
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
                        help_text = I18n.t('available_suggestions') + ":\n" + "\n".join([f"• {suggestion}" for suggestion in suggestions])
                        
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
                            if current_file:
                                handle_query_submission(prompt, current_file, chat_container)
                            st.rerun()
                    except Exception as e:
                        Logger.error(f"Error displaying suggestions: {e}")
                        
            # Chat input
            user_query = st.chat_input(I18n.t('type_question_here'))
            if user_query and current_file:
                handle_query_submission(user_query, current_file, chat_container)
                st.rerun()
        
        # Information tab
        with info_tab:
            if current_ragflow_doc:
                display_ragflow_document_info(current_ragflow_doc)
            else:
                st.info(I18n.t('no_document_selected'))
        
        # Images tab
        with images_tab:
            if current_ragflow_doc:
                display_ragflow_document_images(current_ragflow_doc, container_height=images_container_height)
            else:
                st.info(I18n.t('no_document_selected'))



def _extract_page_dimensions_immediately(pdf_data: bytes, ragflow_doc: dict):
    """Extract page dimensions immediately after PDF download."""
    
    if not ragflow_doc:
        return
    
    try:
        # Save PDF to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(pdf_data)
            temp_pdf_path = temp_file.name
        
        try:
            # Extract page dimensions immediately
            pdf_doc = fitz.open(temp_pdf_path)
            page_dimensions = {}
            
            for page_num in range(len(pdf_doc)):
                page = pdf_doc[page_num]
                rect = page.rect
                page_dimensions[page_num + 1] = {  # 1-based page numbering
                    'width': float(rect.width),
                    'height': float(rect.height)
                }
            pdf_doc.close()
            
            # Store immediately with correct document ID format
            doc_id = f"ragflow_{ragflow_doc.get('id', '')}"
            StateManager.store_document_page_dimensions(doc_id, page_dimensions)
            Logger.info(f"IMMEDIATE: Stored page dimensions for {len(page_dimensions)} pages for {doc_id}")
            
        finally:
            # Clean up temp file
            import os
            try:
                os.unlink(temp_pdf_path)
            except Exception as e:
                Logger.warning(f"Failed to cleanup temp file: {e}")
                
    except Exception as e:
        Logger.error(f"Error extracting page dimensions: {e}")