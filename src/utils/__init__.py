"""
Utility functions for the Chat with Docs application.
"""

# Re-export functions from new modules to maintain backward compatibility
from .common import (
    generate_unique_component_key,
    generate_stable_component_key,
    initialize_llm_settings,
    create_empty_directories,
    format_chat_history
)

# Re-export from state_manager for backward compatibility
from ..core.state_manager import StateManager

# Function aliases for backward compatibility
def initialize_session_state():
    """Wrapper for StateManager.initialize() for backward compatibility"""
    return StateManager.initialize()