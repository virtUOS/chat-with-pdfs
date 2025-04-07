"""
Chat with Docs - Main Application

This application allows users to upload PDF documents and chat with them using LLM technology.
Documents are processed with LlamaIndex and responses are generated using the specified model.
"""

import streamlit as st
from dotenv import load_dotenv

from src.core.state_manager import StateManager
from src.utils.logger import Logger
from src.utils.common import create_empty_directories
from src.ui.layouts import render_sidebar, render_main_content

# Load environment variables
load_dotenv()

def main():
    """Main application function."""
    # Set page configuration
    st.set_page_config(
        page_title="Chat with your PDF",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize logger
    Logger.initialize()
    Logger.info("Starting Chat with Docs application")
    
    # Initialize session state and create directories
    StateManager.initialize()
    create_empty_directories()
    
    # Application header
    st.title("Chat with your PDF")
    
    # Render the sidebar (document upload and settings)
    render_sidebar()
    
    # Render the main content area (chat interface and document view)
    render_main_content()

if __name__ == "__main__":
    main()