"""
Configuration settings and constants for the Chat with Docs application.
"""

import os

# Image paths and settings
IMAGES_PATH = os.path.join(os.getcwd(), "tmp_assets/tmp_images/")

# Prompt templates
CITATION_PROMPT = """
    CRITICAL INSTRUCTION: Your response MUST include numbered citations in square brackets [1], [2], etc.

    Follow these rules EXACTLY:
    1. Base your answer SOLELY on the provided sources.
    2. EVERY statement of fact MUST have a citation in square brackets [#].
    3. Format citations as [1], [2], [3], etc., corresponding to the source number.
    4. Citations must appear IMMEDIATELY after the information they support.
    5. Your answer MUST have AT LEAST ONE citation, even for simple queries.
    6. If sources don't contain relevant information, explicitly state this and explain why.
    7. DO NOT make up information or use your general knowledge.
    
    Example:
    Source 1: The sky is red in the evening and blue in the morning.
    Source 2: Water is wet when the sky is red.
    Query: When is water wet?
    Answer: According to the sources, water becomes wet when the sky is red [2], which occurs specifically in the evening [1].
    
    --------------
    
    Below are numbered sources of information:
    --------------
    
    {context_str}
    
    --------------
    
    Query: {query_str}
    
    Answer (YOU MUST INCLUDE NUMBERED CITATIONS IN FORMAT [1], [2], ETC.):
    """

DEFAULT_PROMPT = "Please provide an answer that considers both the provided sources and your general knowledge. \
    While you may use the sources as a basis, you are allowed to expand on the answer with additional details. \
    If sources don't address the query specifically, you can use your knowledge to provide a helpful response. \
    \n------\n \
    Sources: {context_str} \
    \n------\n \
    Query: {query_str}"

# For backward compatibility
CITATION_CHAT_PROMPT = CITATION_PROMPT
GENERAL_CHAT_PROMPT = DEFAULT_PROMPT

# Model settings
DEFAULT_MODEL = "gpt-4o-mini"
MODELS = {
    "gpt-4o-mini": {"temperature": 0.2},
    "gpt-4o": {"temperature": 0.2},
    "o3-mini": {"temperature": 0.2}
}

# Load summary model from environment variable, fallback to DEFAULT_MODEL
SUMMARY_MODEL = os.environ.get("SUMMARY_MODEL", DEFAULT_MODEL)

# Check for OpenAI API key
if not os.environ.get("OPENAI_API_KEY"):
    print("Warning: OPENAI_API_KEY environment variable not set")
