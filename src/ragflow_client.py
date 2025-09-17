"""
RAGFlow API Client

Official RAGFlow SDK wrapper with environment-based configuration.
"""

import os
import time
from typing import Dict, Any, Optional, List, Union
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
        try:
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
            return {
                'code': 0,
                'data': result,
                'message': 'Datasets retrieved successfully'
            }
        except Exception as e:
            return {
                'code': 1,
                'data': [],
                'message': f'Error retrieving datasets: {str(e)}'
            }
    
    def create_dataset(self, name: str, description: str = "", **kwargs) -> Dict[str, Any]:
        """Create a new dataset using official SDK."""
        dataset = self.ragflow.create_dataset(name=name, description=description, **kwargs)
        return {
            'code': 0,
            'data': {
                'id': dataset.id,
                'name': dataset.name,
                'description': getattr(dataset, 'description', ''),
                'status': getattr(dataset, 'status', 'created')
            }
        }
    
    def upload_document(self, dataset_id: str, file_path: str) -> Dict[str, Any]:
        """Upload a document using official SDK."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = self.ragflow.post(f'/api/v1/datasets/{dataset_id}/documents', files=files)
        return response.json()
    
    def retrieve_chunks(self, dataset_ids: list, question: str, **kwargs) -> List[Dict[str, Any]]:
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
        assistant = self.ragflow.create_chat(name=name, dataset_ids=dataset_ids, **kwargs)
        return {
            'code': 0,
            'data': {
                'id': assistant.id,
                'name': assistant.name,
                'dataset_ids': dataset_ids,
                'status': getattr(assistant, 'status', 'created')
            }
        }
    
    def get_chat_assistants(self, **kwargs) -> List[Dict[str, Any]]:
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
    
    def upload_document_with_progress(self, dataset_id: str, file_path: str, file_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Upload a document with enhanced error handling and status tracking.
        
        Args:
            dataset_id: ID of the dataset to upload to
            file_path: Path to the file to upload
            file_name: Optional custom name for the document
            
        Returns:
            Dict containing upload response with document ID and status
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            # Get dataset object
            datasets = self.ragflow.list_datasets()
            target_dataset = None
            for dataset in datasets:
                if dataset.id == dataset_id:
                    target_dataset = dataset
                    break
            
            if not target_dataset:
                raise ValueError(f"Dataset {dataset_id} not found")
            
            # Use SDK's upload method with correct format for RAGFlow
            # The SDK expects 'display_name' and 'blob' (file content as bytes)
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            document = target_dataset.upload_documents([{
                "display_name": file_name or os.path.basename(file_path),
                "blob": file_content
            }])
            
            if document and len(document) > 0:
                doc = document[0]
                return {
                    'code': 0,
                    'data': {
                        'id': doc.id,
                        'name': doc.name,
                        'status': getattr(doc, 'status', 'uploading'),
                        'dataset_id': dataset_id
                    },
                    'message': 'Document uploaded successfully'
                }
            else:
                return {
                    'code': 1,
                    'message': 'Upload failed - no document returned',
                    'data': None
                }
                
        except Exception as e:
            return {
                'code': 1,
                'message': f'Upload failed: {str(e)}',
                'data': None
            }
    
    def check_document_processing_status(self, dataset_id: str, document_id: str) -> Dict[str, Any]:
        """
        Check the processing status of a specific document.
        
        Args:
            dataset_id: ID of the dataset containing the document
            document_id: ID of the document to check
            
        Returns:
            Dict containing document status information
        """
        try:
            response = self.get_documents(dataset_id)
            if response.get('code') == 0:
                docs = response.get('data', {}).get('docs', [])
                for doc in docs:
                    if doc.get('id') == document_id:
                        return {
                            'code': 0,
                            'data': {
                                'id': doc.get('id'),
                                'name': doc.get('name'),
                                'status': doc.get('status', 'unknown'),
                                'chunk_count': doc.get('chunk_count', 0),
                                'token_count': doc.get('token_count', 0)
                            }
                        }
                
                return {
                    'code': 1,
                    'message': f'Document {document_id} not found',
                    'data': None
                }
            else:
                return response
                
        except Exception as e:
            return {
                'code': 1,
                'message': f'Error checking document status: {str(e)}',
                'data': None
            }
    
    def create_dataset_with_validation(self, name: str, description: str = "", **kwargs) -> Dict[str, Any]:
        """
        Create a new dataset with validation and enhanced error handling.
        
        Args:
            name: Name for the new dataset
            description: Optional description for the dataset
            **kwargs: Additional parameters for dataset creation
            
        Returns:
            Dict containing created dataset information
        """
        try:
            # Check if dataset with same name already exists
            datasets_response = self.get_datasets()
            if datasets_response.get('code') == 0:
                existing_datasets = datasets_response.get('data', [])
                for dataset in existing_datasets:
                    if dataset.get('name') == name:
                        return {
                            'code': 1,
                            'message': f'Dataset with name "{name}" already exists',
                            'data': None
                        }
            
            # Set default parameters for better compatibility
            # Let RAGFlow use its default embedding model if none specified
            dataset_params = {
                'name': name,
                'description': description,
                **kwargs  # Include any additional parameters provided
            }
            
            # Only set chunk_method if not provided and if it's a supported parameter
            if 'chunk_method' not in kwargs:
                dataset_params['chunk_method'] = 'naive'
            
            dataset = self.ragflow.create_dataset(**dataset_params)
            
            return {
                'code': 0,
                'data': {
                    'id': dataset.id,
                    'name': dataset.name,
                    'description': getattr(dataset, 'description', ''),
                    'status': getattr(dataset, 'status', 'created')
                },
                'message': 'Dataset created successfully'
            }
            
        except Exception as e:
            return {
                'code': 1,
                'message': f'Dataset creation failed: {str(e)}',
                'data': None
            }
    
    def auto_create_assistant(self, dataset_id: str, dataset_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Automatically create a chat assistant for a dataset.
        
        Args:
            dataset_id: ID of the dataset to create assistant for
            dataset_name: Optional name of the dataset for assistant naming
            
        Returns:
            Dict containing created assistant information
        """
        try:
            # Generate assistant name
            if not dataset_name:
                # Get dataset info to use name
                datasets_response = self.get_datasets()
                if datasets_response.get('code') == 0:
                    datasets = datasets_response.get('data', [])
                    for dataset in datasets:
                        if dataset.get('id') == dataset_id:
                            dataset_name = dataset.get('name', 'Unknown Dataset')
                            break
                    else:
                        dataset_name = 'Unknown Dataset'
                else:
                    dataset_name = 'Unknown Dataset'
            
            assistant_name = f"{dataset_name} Assistant"
            
            # Check if assistant with same name already exists
            existing_assistants = self.get_chat_assistants()
            for assistant in existing_assistants:
                if assistant.get('name') == assistant_name:
                    return {
                        'code': 1,
                        'message': f'Assistant with name "{assistant_name}" already exists',
                        'data': assistant
                    }
            
            # Create assistant using SDK
            assistant = self.ragflow.create_chat(
                name=assistant_name,
                dataset_ids=[dataset_id]
            )
            
            return {
                'code': 0,
                'data': {
                    'id': assistant.id,
                    'name': assistant.name,
                    'dataset_ids': [dataset_id],
                    'status': getattr(assistant, 'status', 'created')
                },
                'message': 'Assistant created successfully'
            }
            
        except Exception as e:
            return {
                'code': 1,
                'message': f'Assistant creation failed: {str(e)}',
                'data': None
            }
    
    def get_dataset_by_id(self, dataset_id: str) -> Dict[str, Any]:
        """
        Get specific dataset information by ID.
        
        Args:
            dataset_id: ID of the dataset to retrieve
            
        Returns:
            Dict containing dataset information
        """
        try:
            datasets_response = self.get_datasets()
            if datasets_response.get('code') == 0:
                datasets = datasets_response.get('data', [])
                for dataset in datasets:
                    if dataset.get('id') == dataset_id:
                        return {
                            'code': 0,
                            'data': dataset
                        }
            
            return {
                'code': 1,
                'message': f'Dataset {dataset_id} not found',
                'data': None
            }
            
        except Exception as e:
            return {
                'code': 1,
                'message': f'Error retrieving dataset: {str(e)}',
                'data': None
            }
    
    def trigger_document_parsing(self, dataset_id: str) -> Dict[str, Any]:
        """
        Trigger parsing for all documents in a dataset.
        
        Args:
            dataset_id: ID of the dataset to parse documents for
            
        Returns:
            Dict containing parse operation result
        """
        try:
            # Get dataset object
            datasets = self.ragflow.list_datasets()
            target_dataset = None
            for dataset in datasets:
                if dataset.id == dataset_id:
                    target_dataset = dataset
                    break
            
            if not target_dataset:
                return {
                    'code': 1,
                    'message': f'Dataset {dataset_id} not found',
                    'data': None
                }
            
            # Get all documents in this dataset to get their IDs for parsing
            docs_response = self.get_documents(dataset_id)
            if docs_response.get('code') != 0:
                return {
                    'code': 1,
                    'message': f'Could not get documents for parsing: {docs_response.get("message")}',
                    'data': None
                }
            
            docs = docs_response.get('data', {}).get('docs', [])
            document_ids = [doc.get('id') for doc in docs if doc.get('id')]
            
            if not document_ids:
                return {
                    'code': 1,
                    'message': 'No documents found to parse',
                    'data': None
                }
            
            # Trigger parsing using async_parse_documents with document IDs
            parse_result = target_dataset.async_parse_documents(document_ids)
            
            return {
                'code': 0,
                'data': parse_result,
                'message': 'Document parsing triggered successfully'
            }
            
        except Exception as e:
            return {
                'code': 1,
                'message': f'Error triggering document parsing: {str(e)}',
                'data': None
            }
    
    def check_dataset_processing_status(self, dataset_id: str) -> Dict[str, Any]:
        """
        Check if all documents in a dataset have finished processing.
        
        Args:
            dataset_id: ID of the dataset to check
            
        Returns:
            Dict containing processing status summary
        """
        try:
            response = self.get_documents(dataset_id)
            if response.get('code') != 0:
                return response
            
            docs = response.get('data', {}).get('docs', [])
            if not docs:
                return {
                    'code': 0,
                    'data': {
                        'total_docs': 0,
                        'processed_docs': 0,
                        'failed_docs': 0,
                        'processing_docs': 0,
                        'all_processed': True,
                        'documents': []
                    }
                }
            
            processed_count = 0
            failed_count = 0
            processing_count = 0
            
            for doc in docs:
                status = str(doc.get('status', ''))
                chunk_count = doc.get('chunk_count', 0)
                
                # RAGFlow document status codes (based on API docs):
                # "1" = processing/uploading
                # "2" = completed/ready
                # "-1" = failed
                # "0" = not started/pending
                
                if status == "2" or chunk_count > 0:
                    # Document completed successfully
                    processed_count += 1
                elif status == "-1":
                    # Document failed
                    failed_count += 1
                else:
                    # Document still processing (status "1" or "0")
                    processing_count += 1
            
            all_processed = processing_count == 0
            
            return {
                'code': 0,
                'data': {
                    'total_docs': len(docs),
                    'processed_docs': processed_count,
                    'failed_docs': failed_count,
                    'processing_docs': processing_count,
                    'all_processed': all_processed,
                    'documents': docs
                }
            }
            
        except Exception as e:
            return {
                'code': 1,
                'message': f'Error checking dataset processing status: {str(e)}',
                'data': None
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