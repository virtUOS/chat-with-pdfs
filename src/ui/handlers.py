"""
Event handlers for the Chat with Docs application UI.
"""

import streamlit as st

from ..utils.logger import Logger
from ..utils.citations import extract_citation_indices
from ..core.ragflow_chat_engine import RAGFlowChatEngine


def handle_query_submission(query_text: str, current_file: str, chat_container) -> None:
    """Handle query submission event.
    
    Args:
        query_text: The query text to process
        current_file: The current file to query against
    """
    if not query_text.strip() or not current_file:
        return
    
    # Add the current file to the chat history if it doesn't exist yet
    if current_file not in st.session_state.chat_history:
        st.session_state.chat_history[current_file] = []
    
    # Add user message to the chat history
    st.session_state.chat_history[current_file].append({
        "role": "user",
        "content": query_text
    })

    with chat_container:
        with st.chat_message('user'):
            st.markdown(query_text)
    
        with st.spinner('Thinking...'):
            try:
                # Process the query using the RAGFlow chat engine
                response = RAGFlowChatEngine.process_query(query_text, current_file)
                
                # Extract information from the response
                answer = response.get('answer', "Sorry, I couldn't process your query.")
                sources = response.get('sources', [])
                images = response.get('images', [])
                citation_mapping = response.get('citation_mapping', {})  # Get the citation mapping
                
                # Extract citation numbers from the response
                citations = extract_citation_indices(answer)
                
                # Create citation page mapping
                citation_pages = {}
                if citations:
                    for i, source in enumerate(sources):
                        citation_num = i + 1
                        # Extract page number from the source
                        page_num = None
                        if hasattr(source, 'node'):
                            page_num = source.node.metadata.get('page', 0)
                        elif hasattr(source, 'metadata'):
                            page_num = source.metadata.get('page', 0)
                        
                        # Store page number if available
                        if page_num is not None:
                            try:
                                page_num = int(page_num)
                                if page_num > 0:
                                    citation_pages[str(citation_num)] = page_num
                            except (ValueError, TypeError):
                                pass
                
                # Add assistant message to the chat history
                st.session_state.chat_history[current_file].append({
                    "role": "assistant",
                    "content": answer,
                    "sources": sources,
                    "images": images,
                    "citations": citations,
                    "citation_pages": citation_pages,
                    "citation_mapping": citation_mapping,  # Use the one already extracted
                    "document": current_file,
                    "response_id": len(st.session_state.chat_history[current_file]) - 1
                })
                
                # Clear the query input for next question
                st.session_state.query_text = ""
                
            except Exception as e:
                # Log the error
                Logger.error(f"Error processing query: {str(e)}")
                
                # Add error message to chat history
                st.session_state.chat_history[current_file].append({
                    "role": "assistant",
                    "content": f"Error processing your query: {str(e)}",
                    "document": current_file
                })


