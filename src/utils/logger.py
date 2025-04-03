"""
Structured logging system for the Chat with Docs application.
"""

import logging
import streamlit as st
from datetime import datetime
from typing import Optional

class Logger:
    """Centralized logging system for the application."""
    
    _logger: Optional[logging.Logger] = None
    _log_to_ui: bool = True
    
    @classmethod
    def initialize(cls, log_level=logging.INFO, log_file=None):
        """Initialize the logger.
        
        Args:
            log_level: The logging level (default: INFO)
            log_file: Path to log file (if None, logs to console only)
        """
        # Create logger if it doesn't exist
        if cls._logger is None:
            cls._logger = logging.getLogger("chat_with_docs")
            cls._logger.setLevel(log_level)
            
            # Create console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(log_level)
            
            # Create formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(formatter)
            
            # Add console handler to logger
            cls._logger.addHandler(console_handler)
            
            # Add file handler if specified
            if log_file:
                try:
                    file_handler = logging.FileHandler(log_file)
                    file_handler.setLevel(log_level)
                    file_handler.setFormatter(formatter)
                    cls._logger.addHandler(file_handler)
                except Exception as e:
                    cls._logger.error(f"Could not create log file: {str(e)}")
    
    @classmethod
    def debug(cls, message: str):
        """Log a debug message."""
        if cls._logger is None:
            cls.initialize()
        cls._logger.debug(message)
    
    @classmethod
    def info(cls, message: str):
        """Log an info message."""
        if cls._logger is None:
            cls.initialize()
        cls._logger.info(message)
    
    @classmethod
    def warning(cls, message: str):
        """Log a warning message."""
        if cls._logger is None:
            cls.initialize()
        cls._logger.warning(message)
        
        # Also show in UI if enabled
        if cls._log_to_ui and 'logger_messages' not in st.session_state:
            st.session_state.logger_messages = []
        
        if cls._log_to_ui:
            st.session_state.logger_messages.append({
                'level': 'warning',
                'message': message,
                'time': datetime.now().strftime('%H:%M:%S')
            })
    
    @classmethod
    def error(cls, message: str):
        """Log an error message."""
        if cls._logger is None:
            cls.initialize()
        cls._logger.error(message)
        
        # Also show in UI if enabled
        if cls._log_to_ui and 'logger_messages' not in st.session_state:
            st.session_state.logger_messages = []
        
        if cls._log_to_ui:
            st.session_state.logger_messages.append({
                'level': 'error',
                'message': message,
                'time': datetime.now().strftime('%H:%M:%S')
            })