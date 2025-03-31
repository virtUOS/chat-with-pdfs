# Chat-with-Docs

An interactive application that allows users to upload PDF documents and have natural language conversations with them using LLM technology.

![Chat-with-Docs Logo](assets/img/logo.svg)

## Features

- **PDF Document Processing**: Upload and process PDF documents with text and image extraction
- **Interactive Chat Interface**: Ask questions about your documents in natural language
- **Citation Mode**: Responses include numbered references to source locations in the document
- **Document Viewer**: Integrated PDF viewer with annotation capabilities showing source locations
- **Document Information**: Automatic extraction of metadata and document summarization
- **Image Gallery**: Grid display of all images extracted from documents
- **Query Suggestions**: Interactive suggestion pills to help explore document content
- **Multiple LLM Support**: Compatible with various OpenAI models (gpt-4o-mini, gpt-4o, o3-mini)

## Requirements

- Python 3.8+
- OpenAI API key
- Required Python packages (see `requirements.txt`)

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/chat-with-docs.git
   cd chat-with-docs
   ```

2. Install required packages:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your OpenAI API key and model preferences:
   ```
   OPENAI_API_KEY=your_api_key_here
   CHAT_MODEL=gpt-4o
   SUMMARY_MODEL=gpt-4o-mini
   ```

## Usage

1. Run the application:
   ```
   streamlit run app_modular.py
   ```

2. Access the web interface at http://localhost:8501

3. Upload PDF documents using the file uploader

4. Start chatting with your documents in the chat tab

5. View document information and extracted images in their respective tabs

## Project Structure

- `app_modular.py`: Main Streamlit application with modular structure
- `src/`: Core application components
  - `config.py`: Application configuration and settings
  - `document.py`: Document handling and processing
  - `chat_engine.py`: LLM integration and query processing
  - `source.py`: Source citation handling
  - `image.py`: Image extraction and processing
  - `utils.py`: Utility functions
- `assets/`: Application assets
- `temp_files/`: Temporary storage for uploaded documents
- `tmp_assets/`: Temporary storage for extracted images
- `VectorStore/`: Vector database for document indexing

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.