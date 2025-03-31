# System Patterns

This file documents recurring patterns and standards used in the project.
It is optional, but recommended to be updated as the project evolves.
2025-03-21 13:34:28 - Log of updates made.

## Coding Patterns

* **Streamlit Session State Management**: The application uses Streamlit's session state dictionary extensively for maintaining state across page reloads and user interactions.
* **Component Separation**: Functionality is separated into clear modules (document.py, chat_engine.py, image.py, etc.) with well-defined responsibilities.
* **Error Handling**: Try-except blocks with specific error handling for file processing and API calls.
* **Library Version Handling**: Implement multiple fallback mechanisms for interacting with external libraries to handle API changes across versions.

* **Configuration Management**: Central configuration in config.py for constants, prompt templates, and model settings.

## Architectural Patterns

* **Document Processing Pipeline**:
  1. Upload PDF
  2. Save to temp location
  3. Process with pymupdf4llm
  4. Extract and store images
  5. Generate document summary using LLM
  6. Create vector and keyword indices
  7. Initialize query engine

* **Dual-Retrieval System**:
  - Vector retrieval for semantic similarity
  - Keyword retrieval for exact matching
  - Combined with "OR" logic for comprehensive results

* **Response Synthesis**:
  - Source nodes retrieved from indices
  - Prompt templates (with or without citation requirements)
  - LLM response generation
  - Post-processing for image inclusion


* **UI Patterns**:
  - **Tabbed Interface**: Organize related content in tabs for better user experience and cleaner organization
  - **Responsive Grid Layout**: Use Streamlit's column system for responsive grid layouts (e.g., image gallery)
  - **Split Screen Layout**: Split content into logical sections (e.g., PDF viewer and interaction panel)
  - **Expandable Sections**: Use expanders for detailed content that doesn't need to be visible at all times


## Testing Patterns

* No formal testing patterns were identified in the current codebase.
* Opportunity exists to implement unit tests for core functions and integration tests for the document processing pipeline.