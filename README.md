# Chat with Docs

A Streamlit application that allows users to upload PDF documents and chat with them using LLM technology.

## Overview

Chat with Docs processes PDF documents with LlamaIndex and generates responses using various language models. The application features a user-friendly interface for document management, chat history, and document visualization.

## Features

- **Document Processing**: Upload and process single or multiple PDF documents
- **Chat Interface**: Natural language interaction with document content
- **Citation Support**: Responses include citations to specific parts of the document
- **PDF Viewer**: View documents with highlighted citations
- **Image Extraction**: Automatically extracts and displays images from documents
- **Multi-Document Support**: Switch between multiple uploaded documents
- **Model Selection**: Choose from different language models

## Project Structure

The application follows a modular architecture for better maintainability and extensibility:

```
chat-with-docs/
├── app.py                    # Main application (new modular version)
├── app_modular.py            # Original application (to be deprecated)
├── src/
│   ├── core/                 # Business logic
│   │   ├── __init__.py
│   │   ├── document_manager.py
│   │   ├── chat_engine.py
│   │   ├── state_manager.py
│   │   └── file_processor.py
│   ├── ui/                   # UI-related components
│   │   ├── __init__.py
│   │   ├── components.py
│   │   ├── layouts.py
│   │   └── handlers.py
│   ├── utils/                # Utility functions
│   │   ├── __init__.py
│   │   ├── common.py
│   │   ├── source.py
│   │   ├── image.py
│   │   └── logger.py
│   ├── config.py             # Configuration settings
│   ├── custom_retriever.py   # Custom retrieval logic
│   └── __init__.py
```

## Components

### Core Components

- **DocumentManager**: Handles document processing and storage
- **ChatEngine**: Manages query processing and response generation
- **StateManager**: Manages application state and session data
- **FileProcessor**: Processes and extracts content from files

### UI Components

- **Components**: Reusable UI elements (document info, chat messages, etc.)
- **Layouts**: Page layouts (sidebar, main content area)
- **Handlers**: Event handlers for user interactions

### Utilities

- **Logger**: Centralized logging functionality
- **Common**: Shared utility functions
- **Source**: Citation and source formatting utilities
- **Image**: Image processing utilities

## Getting Started

### Prerequisites

- Python 3.9+
- OpenAI API key or other LLM provider credentials

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/chat-with-docs.git
cd chat-with-docs
```

2. Install the required packages:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your API keys:
```
OPENAI_API_KEY=your_api_key_here
```

### Running the Application

Run the application with Streamlit:

```bash
streamlit run app.py
```

For the original version (to be deprecated):

```bash
streamlit run app_modular.py
```

## Usage

1. Upload a PDF document using the sidebar upload button
2. Wait for the document to be processed
3. Ask questions about the document in the chat input
4. View responses with citations to the source material
5. Click on citations to highlight relevant sections in the PDF

## Testing

Run the integration tests to verify the application functionality:

```bash
python -m unittest test_phase5.py
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.