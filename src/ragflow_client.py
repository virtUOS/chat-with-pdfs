"""
RAGFlow API Client

Official RAGFlow SDK wrapper with environment-based configuration.
"""

import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from ragflow_sdk import RAGFlow


class RAGFlowClient:
    """Wrapper for the official RAGFlow SDK with environment configuration."""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize the RAGFlow client using the official SDK.
        
        Args:
            api_key: RAGFlow API key. If not provided, will load from environment.
            base_url: Base URL for RAGFlow API. If not provided, will load from environment.
        """
        # Load environment variables from .env file
        load_dotenv()
        
        self.api_key = api_key or os.getenv('RAGFLOW_API_KEY')
        self.base_url = base_url or os.getenv('RAGFLOW_BASE_URL')
        
        if not self.api_key:
            raise ValueError("RAGFlow API key is required. Set RAGFLOW_API_KEY in .env file or pass as parameter.")
        
        if not self.base_url:
            raise ValueError("RAGFlow base URL is required. Set RAGFLOW_BASE_URL in .env file or pass as parameter.")
        
        # Initialize official RAGFlow SDK
        self.ragflow = RAGFlow(api_key=self.api_key, base_url=self.base_url)
    
    def get_datasets(self) -> Dict[str, Any]:
        """Get list of datasets using official SDK."""
        dataset_objects = self.ragflow.list_datasets()
        # Convert DataSet objects to dictionaries
        result = []
        for dataset in dataset_objects:
            result.append({
                'id': dataset.id,
                'name': dataset.name,
                'description': getattr(dataset, 'description', ''),
                'status': getattr(dataset, 'status', ''),
                'create_time': getattr(dataset, 'create_time', ''),
                'update_time': getattr(dataset, 'update_time', '')
            })
        return result
    
    def create_dataset(self, name: str, description: str = "", **kwargs) -> Dict[str, Any]:
        """Create a new dataset using official SDK."""
        response = self.ragflow.create_dataset(name=name, description=description, **kwargs)
        return response
    
    def upload_document(self, dataset_id: str, file_path: str) -> Dict[str, Any]:
        """Upload a document using official SDK."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = self.ragflow.post(f'/api/v1/datasets/{dataset_id}/documents', files=files)
        return response.json()
    
    def retrieve_chunks(self, dataset_ids: list, question: str, **kwargs) -> Dict[str, Any]:
        """Retrieve chunks using official SDK."""
        response = self.ragflow.retrieve(dataset_ids=dataset_ids, question=question, **kwargs)
        return response
    
    def get_documents(self, dataset_id: str, **kwargs) -> Dict[str, Any]:
        """Get documents using official SDK."""
        # Find the dataset by ID and use its list_documents method
        datasets = self.ragflow.list_datasets()
        for dataset in datasets:
            if dataset.id == dataset_id:
                document_objects = dataset.list_documents()
                # Convert Document objects to dictionaries
                result = []
                for doc in document_objects:
                    result.append({
                        'id': doc.id,
                        'name': doc.name,
                        'dataset_id': doc.dataset_id,
                        'type': getattr(doc, 'type', ''),
                        'size': getattr(doc, 'size', 0),
                        'status': getattr(doc, 'status', ''),
                        'chunk_count': getattr(doc, 'chunk_count', 0),
                        'token_count': getattr(doc, 'token_count', 0),
                    })
                return {'code': 0, 'data': {'docs': result}}
        
        # Dataset not found
        return {'code': 100, 'data': None, 'message': f'Dataset {dataset_id} not found'}
    
    def delete_documents(self, dataset_id: str, document_ids: Optional[list] = None) -> Dict[str, Any]:
        """Delete documents using official SDK."""
        data = {'ids': document_ids} if document_ids else {}
        response = self.ragflow.delete(f'/api/v1/datasets/{dataset_id}/documents', json=data)
        return response.json()
    
    def create_chat_assistant(self, name: str, dataset_ids: list, **kwargs) -> Dict[str, Any]:
        """Create a chat assistant using official SDK."""
        response = self.ragflow.create_chat(name=name, dataset_ids=dataset_ids, **kwargs)
        return response
    
    def get_chat_assistants(self, **kwargs) -> Dict[str, Any]:
        """Get list of chat assistants using official SDK."""
        chat_objects = self.ragflow.list_chats(**kwargs)
        # Convert Chat objects to dictionaries
        result = []
        for chat in chat_objects:
            result.append({
                'id': chat.id,
                'name': chat.name,
                'description': getattr(chat, 'description', ''),
                'datasets': getattr(chat, 'datasets', []),
                'dataset_ids': getattr(chat, 'dataset_ids', []),
                'status': getattr(chat, 'status', ''),
                'create_time': getattr(chat, 'create_time', ''),
                'update_time': getattr(chat, 'update_time', '')
            })
        return result
    
    def chat_completion(self, chat_id: str, question: str, stream: bool = True, **kwargs) -> Dict[str, Any]:
        """Chat with an assistant using official SDK."""
        # Find the chat object by ID
        chat_objects = self.ragflow.list_chats()
        target_chat = None
        for chat in chat_objects:
            if chat.id == chat_id:
                target_chat = chat
                break
        
        if not target_chat:
            raise ValueError(f"Chat {chat_id} not found")
        
        # Always create new session but track it properly
        # This ensures each query gets a fresh context without session pollution
        session_obj = target_chat.create_session()
        actual_session_id = session_obj.id
        
        # Use session.ask method with stream=True to avoid SDK bugs
        # Use session.ask with stream=True (works and provides references)
        response_gen = session_obj.ask(question, stream=True)
        
        # Consume all responses to get the final complete one
        final_response = None
        for message in response_gen:
            final_response = message  # Keep updating to get the final complete response
            final_response = message
        if final_response:
            return {
                "code": 0,
                "data": {
                    "answer": final_response.content,
                    "session_id": actual_session_id,
                    "reference": {
                        "chunks": final_response.reference
                    }
                }
            }
        else:
            return {
                "code": 1,
                "message": "No response received",
                "data": None
            }
    
    def _make_request(self, method: str, endpoint: str, **kwargs):
        """
        Backward compatibility method for direct API access.
        Use this only when the official SDK doesn't provide the required functionality.
        """
        # HTTP methods always return Response objects
        if method.upper() == 'GET':
            return self.ragflow.get(endpoint, **kwargs)
        elif method.upper() == 'POST':
            return self.ragflow.post(endpoint, **kwargs)
        elif method.upper() == 'PUT':
            return self.ragflow.put(endpoint, **kwargs)
        elif method.upper() == 'DELETE':
            return self.ragflow.delete(endpoint, **kwargs)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
    

def create_client() -> RAGFlowClient:
    """
    Create a RAGFlow client using environment variables.
    
    Returns:
        Configured RAGFlowClient instance
    """
    return RAGFlowClient()