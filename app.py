"""
Chat with Docs - Main Application

This application allows users to upload PDF documents and chat with them using LLM technology.
Documents are processed with LlamaIndex and responses are generated using the specified model.
"""

import streamlit as st
from dotenv import load_dotenv

from src.core.state_manager import StateManager
from src.utils.logger import Logger
from src.utils.ragflow_common import create_empty_directories, initialize_ragflow_settings, validate_ragflow_environment, initialize_ragflow_session
from src.ui.layouts import render_sidebar, render_main_content

# Load environment variables
load_dotenv()

def main():
    """Main application function."""
    # Set page configuration
    st.set_page_config(
        page_title="Chat with your PDFs",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize logger
    Logger.initialize()
    Logger.info("Starting Chat with PDFs application (RAGFlow version)")
    
    # Validate RAGFlow environment
    if not validate_ragflow_environment():
        st.error("❌ RAGFlow environment not properly configured. Please check your .env file for RAGFLOW_API_KEY and RAGFLOW_BASE_URL.")
        st.stop()
    
    # Initialize session state and create directories
    StateManager.initialize()
    initialize_ragflow_session()
    create_empty_directories()
    
    # Initialize RAGFlow settings with the configured model
    initialize_ragflow_settings()
    
    # Application header
    st.title("Chat with your PDFs")
    
    # Render the sidebar (document upload and settings)
    render_sidebar()
    
    # Render the main content area (chat interface and document view)
    render_main_content()

if __name__ == "__main__":
    main()