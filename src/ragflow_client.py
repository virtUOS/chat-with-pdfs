"""
RAGFlow API Client

A Python client for connecting to the RAGFlow API with environment-based configuration.
"""

import os
import requests
from typing import Dict, Any, Optional
from dotenv import load_dotenv


class RAGFlowClient:
    """Client for interacting with the RAGFlow API."""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize the RAGFlow client.
        
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
        
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'RAGFlow-Python-Client/1.0.0'
        })
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        Make a request to the RAGFlow API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (without base URL)
            **kwargs: Additional arguments to pass to requests
            
        Returns:
            Response object
            
        Raises:
            requests.RequestException: If the request fails
        """
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            print(f"Request failed: {e}")
            raise
    
    def get_datasets(self) -> Dict[str, Any]:
        """
        Get list of datasets (knowledge bases).
        
        Returns:
            Dictionary containing datasets data
        """
        response = self._make_request('GET', '/api/v1/datasets')
        return response.json()
    
    def create_dataset(self, name: str, description: str = "", **kwargs) -> Dict[str, Any]:
        """
        Create a new dataset (knowledge base).
        
        Args:
            name: Name of the dataset
            description: Description of the dataset
            **kwargs: Additional parameters like embedding_model, chunk_method, etc.
            
        Returns:
            Dictionary containing created dataset data
        """
        data = {
            'name': name,
            'description': description,
            **kwargs
        }
        response = self._make_request('POST', '/api/v1/datasets', json=data)
        return response.json()
    
    def upload_document(self, dataset_id: str, file_path: str) -> Dict[str, Any]:
        """
        Upload a document to a dataset.
        
        Args:
            dataset_id: ID of the dataset
            file_path: Path to the file to upload
            
        Returns:
            Dictionary containing upload result
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(file_path, 'rb') as file:
            files = {'file': file}
            
            # Remove Content-Type header for file uploads
            headers = dict(self.session.headers)
            headers.pop('Content-Type', None)
            
            response = self._make_request(
                'POST',
                f'/api/v1/datasets/{dataset_id}/documents',
                files=files,
                headers=headers
            )
            return response.json()
    
    def retrieve_chunks(self, dataset_ids: list, question: str, **kwargs) -> Dict[str, Any]:
        """
        Retrieve chunks from datasets.
        
        Args:
            dataset_ids: List of dataset IDs to search
            question: Question to ask
            **kwargs: Additional parameters like top_k, similarity_threshold, etc.
            
        Returns:
            Dictionary containing retrieval results
        """
        data = {
            'dataset_ids': dataset_ids,
            'question': question,
            **kwargs
        }
        response = self._make_request('POST', '/api/v1/retrieval', json=data)
        return response.json()
    
    def get_documents(self, dataset_id: str, **kwargs) -> Dict[str, Any]:
        """
        Get documents in a dataset.
        
        Args:
            dataset_id: ID of the dataset
            **kwargs: Additional query parameters like page, page_size, etc.
            
        Returns:
            Dictionary containing documents data
        """
        params = kwargs
        response = self._make_request('GET', f'/api/v1/datasets/{dataset_id}/documents', params=params)
        return response.json()
    
    def delete_documents(self, dataset_id: str, document_ids: Optional[list] = None) -> Dict[str, Any]:
        """
        Delete documents from a dataset.
        
        Args:
            dataset_id: ID of the dataset
            document_ids: List of document IDs to delete (if None, deletes all)
            
        Returns:
            Dictionary containing deletion result
        """
        data = {'ids': document_ids} if document_ids else {}
        response = self._make_request('DELETE', f'/api/v1/datasets/{dataset_id}/documents', json=data)
        return response.json()
    
    def create_chat_assistant(self, name: str, dataset_ids: list, **kwargs) -> Dict[str, Any]:
        """
        Create a chat assistant.
        
        Args:
            name: Name of the chat assistant
            dataset_ids: List of dataset IDs to associate
            **kwargs: Additional parameters like llm, prompt, etc.
            
        Returns:
            Dictionary containing created chat assistant data
        """
        data = {
            'name': name,
            'dataset_ids': dataset_ids,
            **kwargs
        }
        response = self._make_request('POST', '/api/v1/chats', json=data)
        return response.json()
    
    def get_chat_assistants(self, **kwargs) -> Dict[str, Any]:
        """
        Get list of chat assistants.
        
        Args:
            **kwargs: Query parameters like page, page_size, etc.
            
        Returns:
            Dictionary containing chat assistants data
        """
        response = self._make_request('GET', '/api/v1/chats', params=kwargs)
        return response.json()
    
    def chat_completion(self, chat_id: str, question: str, stream: bool = True, **kwargs) -> Dict[str, Any]:
        """
        Chat with an assistant.
        
        Args:
            chat_id: ID of the chat assistant
            question: Question to ask
            stream: Whether to stream the response
            **kwargs: Additional parameters like session_id
            
        Returns:
            Dictionary containing chat response
        """
        data = {
            'question': question,
            'stream': stream,
            **kwargs
        }
        response = self._make_request('POST', f'/api/v1/chats/{chat_id}/completions', json=data)
        return response.json()
    
    def get_chunk_image(self, image_id: str) -> bytes:
        """
        Attempt to retrieve an image for a chunk by image ID.
        
        Args:
            image_id: The image ID from chunk reference
            
        Returns:
            Image data as bytes
        """
        # Try common image endpoint patterns
        possible_endpoints = [
            f'/api/v1/images/{image_id}',
            f'/api/v1/chunks/images/{image_id}',
            f'/api/v1/documents/images/{image_id}',
            f'/images/{image_id}',
            f'/static/images/{image_id}',
        ]
        
        for endpoint in possible_endpoints:
            try:
                response = self._make_request('GET', endpoint)
                if response.status_code == 200:
                    return response.content
            except:
                continue
        
        raise ValueError(f"Could not retrieve image for ID: {image_id}")


def create_client() -> RAGFlowClient:
    """
    Create a RAGFlow client using environment variables.
    
    Returns:
        Configured RAGFlowClient instance
    """
    return RAGFlowClient()