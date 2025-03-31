# Product Context
      
This file provides a high-level overview of the project and the expected product that will be created. Initially it is based upon projectBrief.md (if provided) and all other available project-related information in the working directory. This file is intended to be updated as the project evolves, and should be used to inform all other modes of the project's goals and context.
2025-03-21 13:33:03 - Log of updates made will be appended as footnotes to the end of this file.

## Project Goal

* The Chat-with-Docs application allows users to upload PDF documents and have interactive conversations with them using LLM technology.
* The application extracts text and images from PDFs, creates searchable indexes, and provides a chat interface for querying document content.

## Key Features

* PDF document upload and processing
* Text extraction and vectorization using LlamaIndex
* Image extraction from documents
* Dual-retrieval approach (vector + keyword search)
* Citation mode with numbered references
* Image inclusion in responses
* Streamlit-based UI with side-by-side PDF viewer and tabbed interface
* Document information display with metadata extraction and automatic summarization
* Document image gallery with grid layout

* Streamlit-based UI with side-by-side PDF viewer and chat

## Overall Architecture

* Frontend: Streamlit web application
* Document Processing: pymupdf4llm for PDF extraction
* Vector Database: LlamaIndex for document indexing and retrieval
* LLM Integration: OpenAI models (gpt-4o-mini, gpt-4o, o3-mini)


## UI Components

* **Document Upload**: File uploader with multi-file support and processing status
* **PDF Viewer**: Integrated PDF display with annotation capabilities
* **Tabbed Interface**:
  - Chat Tab: Conversation history and query input
  - Document Info Tab: Display of document metadata (title, author, keywords, page count, TOC)
  - Images Tab: Grid display of all images extracted from the document
* **Document Navigation**: Sidebar with document list and selection capabilities
* **Settings Panel**: Model selection and citation mode options

---
[2025-03-21 14:43:58] - Added tabbed interface components and UI details
[2025-03-21 14:58:41] - Added automatic document summarization feature to key features
* Storage: Local file system for documents and extracted images