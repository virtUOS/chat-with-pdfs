"""
Document list component for the sidebar.
"""

import streamlit as st
from streamlit_js_eval import streamlit_js_eval

from ...utils.logger import Logger
from ...utils.i18n import I18n
from ...utils.ragflow_common import get_assistant_documents, get_assistant_dataset_names, generate_ragflow_query_suggestions


def render_document_list() -> None:
    """Render the document list for the selected assistant."""
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