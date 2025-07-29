# RAGFlow Migration Guide

This branch (`ragflow-migration`) contains the updated Chat with Docs application that uses RAGFlow instead of LlamaIndex for document processing and querying.

## What Changed

### Core Components Replaced
- `src/core/document_manager.py` → `src/core/ragflow_document_manager.py`
- `src/core/chat_engine.py` → `src/core/ragflow_chat_engine.py`
- `src/custom_retriever.py` → Replaced with RAGFlow's built-in retrieval
- `src/utils/common.py` → `src/utils/ragflow_common.py`

### New Files Added
- `src/ragflow_client.py` - RAGFlow API client
- `src/core/ragflow_document_manager.py` - Document processing with RAGFlow
- `src/core/ragflow_chat_engine.py` - Chat functionality with RAGFlow
- `src/utils/ragflow_common.py` - RAGFlow-compatible utilities

### Dependencies Updated
- Removed: `llama-index`, `llama_index.llms.*` packages
- Added: `requests`, `httpx` for RAGFlow API communication

## Setup Requirements

### 1. Environment Variables
Add these to your `.env` file:

```bash
# RAGFlow Configuration
RAGFLOW_API_KEY=your_ragflow_api_key_here
RAGFLOW_BASE_URL=http://localhost:9380
```

### 2. RAGFlow Server
Ensure your RAGFlow server is running and accessible at the configured URL.

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

## Key Benefits of RAGFlow

1. **Better Document Processing**: More advanced chunking and processing capabilities
2. **Improved Retrieval**: Enhanced semantic search and hybrid retrieval
3. **Multimodal Support**: Better handling of images and complex document layouts
4. **Scalability**: Server-based architecture for better performance
5. **Session Management**: Built-in chat session handling
6. **Knowledge Base Integration**: Uses existing RAGFlow datasets and documents
7. **No Duplicate Management**: Documents are managed once in RAGFlow
8. **Pre-configured Assistants**: Each assistant comes with optimized settings

## Knowledge Base Approach

### Major Differences from LlamaIndex Version:
- **No Document Upload**: Documents are managed in RAGFlow, not uploaded through the app
- **Assistant-Centric**: Select from existing chat assistants instead of configuring models
- **Dataset Organization**: Documents are organized by RAGFlow datasets
- **API-Based PDF Access**: PDFs are downloaded from RAGFlow when needed
- **Centralized Management**: All document processing happens in RAGFlow

### Benefits:
- **Consistency**: Same documents and processing across all RAGFlow applications
- **Optimization**: Leverage RAGFlow's advanced document processing
- **Collaboration**: Multiple users can access the same knowledge bases
- **Maintenance**: Update documents once in RAGFlow, available everywhere

## Chat Assistant Configuration

Unlike the previous LlamaIndex version, this RAGFlow implementation:
- **Uses existing chat assistants** from your RAGFlow instance
- **No model configuration needed** - models are pre-configured in each chat assistant
- **Assistant selection dropdown** shows available chat assistants from your RAGFlow instance
- **Each assistant has its own model and dataset configuration** managed in RAGFlow UI

### Setting Up Chat Assistants

1. **Create Chat Assistants in RAGFlow UI**:
   - Go to your RAGFlow web interface
   - Create chat assistants with your preferred models
   - Associate them with your datasets
   - Configure prompts and parameters

2. **Select Assistant in Application**:
   - The application will show available chat assistants in the sidebar
   - Select the assistant you want to use for document chat
   - Each assistant comes with its pre-configured model and settings

## Usage

The application interface has been updated to work with RAGFlow's knowledge base approach:

1. **Select Chat Assistant**: Choose from your configured RAGFlow chat assistants
2. **Browse Knowledge Base**: View documents from the assistant's datasets
3. **Select Document**: Pick a document to chat with from the knowledge base
4. **Chat with Context**: Use the assistant's pre-configured model and prompts
5. **View PDF**: The actual PDF is downloaded from RAGFlow and displayed

### No Upload Required
Unlike the previous version, you don't upload documents through the application. Instead:
- Documents are managed in RAGFlow's web interface
- The application shows documents from your assistant's knowledge bases
- PDFs are downloaded on-demand from RAGFlow's API

## Architecture

```
RAGFlow Setup → Assistant Selection → Document Selection → Chat → PDF Viewing
      ↓               ↓                    ↓              ↓         ↓
   Datasets +    Available Assistants  Knowledge Base   RAGFlow   Download
   Documents                           Documents        API       from API
```

### Data Flow
1. **RAGFlow Configuration** (done in RAGFlow UI):
   - Create datasets and upload documents
   - Create chat assistants with models
   - Associate assistants with datasets

2. **Application Workflow**:
   - Fetch available chat assistants via API
   - Get documents from selected assistant's datasets
   - Download selected PDF from RAGFlow
   - Chat using RAGFlow's completion API
   - Display responses with sources and citations

## Troubleshooting

### Common Issues
1. **Connection Error**: Check RAGFlow server is running
2. **API Key Error**: Verify RAGFLOW_API_KEY in .env
3. **Upload Fails**: Check RAGFlow dataset permissions
4. **No Responses**: Verify chat assistant creation

### Logs
Check application logs for detailed error information. Set `LOG_LEVEL=DEBUG` for verbose logging.

## Testing the Migration

1. Start the application: `streamlit run app.py`
2. Upload a test PDF document
3. Ask questions about the document
4. Verify responses include proper citations and sources
5. Check that images are displayed correctly (if present)

## Rollback

If you need to rollback to LlamaIndex:
1. Switch to the `main` branch
2. Restore original requirements.txt
3. Remove RAGFlow environment variables

## Latest Enhancements (January 2025)

### Document Info Tab Improvements
- **Enhanced Layout**: Two-column design with icons and better visual organization
- **PyMuPDF Integration**: Page counting directly from cached PDF data
- **Smart Date Formatting**: Human-readable dates (e.g., "July 28, 2025 at 11:43")
- **Citation Support**: Document summaries now show sources with expandable details
- **Cleaner UI**: Removed redundant headers and status fields

### Images Tab Complete Rewrite
- **PyMuPDF-Based Extraction**: Real-time image extraction from cached PDFs
- **Page-Based Organization**: Images grouped by page with clear headers
- **Proper Sizing**: Consistent 300px width for optimal viewing
- **All Format Support**: RGB, CMYK, and Grayscale image handling
- **Performance Optimized**: Efficient memory management and caching

### Code Quality Improvements
- **Import Organization**: All imports moved to file tops (no inline imports)
- **Type Safety**: Comprehensive type annotations for all new functions
- **Error Handling**: Graceful fallbacks and comprehensive logging
- **Deprecation Fixes**: Updated to current Streamlit API standards

### New Functions Added
- `display_ragflow_document_info()`: Enhanced document metadata display
- `display_ragflow_document_images()`: PyMuPDF-based image extraction
- `_get_page_count_from_cached_pdf()`: Page counting from PDF
- `_extract_images_from_pdf()`: Image extraction with PyMuPDF
- `_get_ragflow_document_details()`: API-based document details

## Performance Notes

- First document upload may take longer as RAGFlow processes and indexes
- Subsequent queries should be faster due to RAGFlow's optimized retrieval
- Large documents benefit significantly from RAGFlow's advanced chunking
- Image extraction is performed on-demand with smart caching
- Page counting uses multiple fallback methods for reliability