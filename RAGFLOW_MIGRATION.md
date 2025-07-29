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

## Usage

The application interface remains the same. Users can:
1. Upload PDF documents (processed via RAGFlow)
2. Chat with documents (powered by RAGFlow chat assistants)
3. View sources and images (retrieved from RAGFlow datasets)

## Architecture

```
User Upload → RAGFlow Dataset → RAGFlow Chat Assistant → Response
     ↓              ↓                    ↓               ↓
  File Save    Document Index      Query Processing   Answer + Sources
```

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

## Performance Notes

- First document upload may take longer as RAGFlow processes and indexes
- Subsequent queries should be faster due to RAGFlow's optimized retrieval
- Large documents benefit significantly from RAGFlow's advanced chunking