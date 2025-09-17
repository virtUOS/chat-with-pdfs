"""
Upload status definitions and configurations.
"""

from enum import Enum


class UploadStatus(Enum):
    """Upload operation status enumeration."""
    PENDING = "pending"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    PAUSED = "paused"


class ProcessingStage(Enum):
    """Document processing stage enumeration."""
    UPLOAD = "upload"
    PARSING = "parsing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    ASSISTANT_CREATION = "assistant_creation"
    COMPLETED = "completed"


class RetryConfig:
    """Configuration for retry mechanisms."""
    MAX_RETRIES = 3
    RETRY_DELAYS = [2, 5, 10]  # seconds
    NETWORK_TIMEOUT = 30  # seconds