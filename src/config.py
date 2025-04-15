"""
Configuration settings and constants for the Chat with Docs application.
"""


try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import os

# Image paths and settings
IMAGES_PATH = os.environ.get("TMP_ASSETS_PATH", "/tmp/chat-with-pdfs/tmp_assets/tmp_images")

# Prompt template
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

# For backward compatibility
CITATION_CHAT_PROMPT = CITATION_PROMPT

# Model settings
import warnings

# Suffixes
OPENAI_SUFFIX = os.environ.get("OPENAI_SUFFIX", "(OpenAI)")
CUSTOM_SUFFIX = os.environ.get("CUSTOM_SUFFIX", "(Custom)")
OLLAMA_SUFFIX = os.environ.get("OLLAMA_SUFFIX", "(Ollama)")

# Model lists from env
custom_models_env = os.environ.get("CUSTOM_MODELS", "")
CUSTOM_MODELS = [m.strip() for m in custom_models_env.split(",") if m.strip()]
ollama_models_env = os.environ.get("OLLAMA_MODELS", "")
OLLAMA_MODELS = [m.strip() for m in ollama_models_env.split(",") if m.strip()]

# Start with empty MODELS dict and add in desired order
MODELS = {}

# 1. Add custom models first
for model_name in CUSTOM_MODELS:
    MODELS[model_name] = {"temperature": 0.2}

# 2. Add ollama models next (if not already present)
for model_name in OLLAMA_MODELS:
    if model_name not in MODELS:
        MODELS[model_name] = {"temperature": 0.2}

# 3. Add OpenAI models from MODELS env var
models_env = os.environ.get("MODELS", "")
openai_models_list = [m.strip() for m in models_env.split(",") if m.strip()]

# Add models from MODELS env var
for model_name in openai_models_list:
    if model_name not in MODELS:
        MODELS[model_name] = {"temperature": 0.2}

# Custom OpenAI-compatible provider config
CUSTOM_API_ENDPOINT = os.environ.get("CUSTOM_API_ENDPOINT", "")
CUSTOM_API_KEY = os.environ.get("CUSTOM_API_KEY", "")

# Ollama configuration
OLLAMA_ENDPOINT = os.environ.get("OLLAMA_ENDPOINT", "http://localhost:11434")
OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY", "")

# Now allow DEFAULT_MODEL to be set in .env, fallback to "gpt-4o-mini"
DEFAULT_MODEL_ENV = os.environ.get("DEFAULT_MODEL", "").strip()
DEFAULT_MODEL = DEFAULT_MODEL_ENV if DEFAULT_MODEL_ENV else "gpt-4o-mini"
# If the default model is not in MODELS, fallback and warn
if DEFAULT_MODEL not in MODELS:
    warnings.warn(f"DEFAULT_MODEL '{DEFAULT_MODEL}' not found in MODELS. Falling back to 'gpt-4o-mini'.")
    DEFAULT_MODEL = "gpt-4o-mini"

# Load summary model from environment variable, fallback to DEFAULT_MODEL
SUMMARY_MODEL = os.environ.get("SUMMARY_MODEL", DEFAULT_MODEL)

# Check for OpenAI API key
if not os.environ.get("OPENAI_API_KEY"):
    print("Warning: OPENAI_API_KEY environment variable not set")

# Debug information
print(f"[DEBUG] MODELS loaded: {list(MODELS.keys())}")
print(f"[DEBUG] OLLAMA_MODELS: {OLLAMA_MODELS}")



