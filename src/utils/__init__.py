"""
Utility functions for the Chat with Docs application.
"""

# Re-export from state_manager for backward compatibility
from ..core.state_manager import StateManager

# Function aliases for backward compatibility
def initialize_session_state():
    """Wrapper for StateManager.initialize() for backward compatibility"""
    return StateManager.initialize()