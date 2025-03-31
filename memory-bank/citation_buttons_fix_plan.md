# Citation Buttons Fix Plan

## Issue Identified

The application is experiencing a key collision error in the Streamlit UI components:

```
Error processing your query: There are multiple elements with the same key='resp_new_1742570781_citation_btn_2'. To fix this, please make sure that the key argument is unique for each element.
```

The error occurs immediately when chat responses are generated, suggesting that duplicate keys are created during the rendering process.

## Root Cause Analysis

After reviewing the code in `app_modular.py`, the issue appears in these sections:

1. Around line 846-852 (citation buttons below the response):
```python
# Create a unique key prefix for this response using timestamp
key_prefix = f"resp_new_{int(time.time())}"

for i, citation_num in enumerate(sorted(citation_numbers)):
    # ...
    if st.button(f"[{citation_num}]", key=f"{key_prefix}_citation_btn_{citation_num}",
                help=f"Jump to source {citation_num} in PDF"):
        # ...
```

2. Around line 900 (view buttons in the source expander):
```python
source_key_prefix = f"src_new_{int(time.time())}"
if st.button("👁️ View", key=f"{source_key_prefix}_view_btn_{citation_num}",
            help=f"Jump to source {citation_num} in PDF"):
    # ...
```

The root cause is likely:
1. Multiple Streamlit reruns occurring close together with the same timestamp
2. Multiple citation buttons with the same number being rendered
3. The key generation mechanism not being unique enough for Streamlit's component rendering

## Solution Strategy

We need to implement a more robust key generation system that ensures uniqueness even during rapid reruns.

### 1. Create a Key Generator Utility Function

Add a function to `src/utils.py` that creates guaranteed unique keys:

```python
def generate_unique_component_key(prefix, component_type, identifier, context=None):
    """
    Generate a guaranteed unique key for Streamlit UI components.
    
    Args:
        prefix: A prefix for this key (e.g., 'resp', 'src')
        component_type: Type of component (e.g., 'btn', 'input')
        identifier: Specific identifier for this component (e.g., citation number)
        context: Optional context information (e.g., message index in chat history)
        
    Returns:
        A string key guaranteed to be unique across reruns
    """
    # Use a combination of:
    # 1. Session-specific random string (create if not exists)
    if 'component_key_random' not in st.session_state:
        import uuid
        st.session_state.component_key_random = str(uuid.uuid4())[:8]
    
    # 2. Component counter that increments with use
    if 'component_key_counter' not in st.session_state:
        st.session_state.component_key_counter = 0
    st.session_state.component_key_counter += 1
    
    # 3. Timestamp (milliseconds)
    import time
    timestamp = int(time.time() * 1000)
    
    # 4. Context string if provided
    context_str = f"_{context}" if context else ""
    
    # Combine all parts
    return f"{prefix}_{st.session_state.component_key_random}_{st.session_state.component_key_counter}_{timestamp}{context_str}_{component_type}_{identifier}"
```

### 2. Update Citation Button Keys in `app_modular.py`

Replace the current key generation approach (around line 846):

```python
# Import the key generator
from src.utils import generate_unique_component_key

# For citation buttons below the response
for i, citation_num in enumerate(sorted(citation_numbers)):
    col_index = i % len(cols)
    with cols[col_index]:
        button_key = generate_unique_component_key(
            prefix="resp",
            component_type="btn",
            identifier=citation_num,
            context=len(st.session_state.chat_history.get(current_file, []))
        )
        if st.button(f"[{citation_num}]", key=button_key,
                   help=f"Jump to source {citation_num} in PDF"):
            # Store the annotation index (0-based) to scroll to
            st.session_state.selected_annotation_index = citation_num - 1
            # Force page rerun
            st.rerun()
```

### 3. Update Source Expander View Button Keys

Replace the current key generation (around line 900):

```python
# For view buttons in the source expander
button_key = generate_unique_component_key(
    prefix="src",
    component_type="view",
    identifier=citation_num,
    context=len(st.session_state.chat_history.get(current_file, []))
)
if st.button("👁️ View", key=button_key,
           help=f"Jump to source {citation_num} in PDF"):
    # Store the annotation index to scroll to
    st.session_state.selected_annotation_index = source_index
    # Force page rerun
    st.rerun()
```

### 4. Add Fallback Error Handling

Improve error handling to avoid the app crashing if key collisions still occur:

```python
# In the chat response display section
try:
    # Create citation buttons with new key generation
    # ...
except Exception as e:
    import traceback
    error_msg = str(e)
    st.error(f"Error displaying citation buttons: {error_msg}")
    st.info("You can still view sources in the Source Information expander below.")
    # Log the full error for debugging
    print(f"Citation button error: {error_msg}")
    print(traceback.format_exc())
```

## Implementation Steps

1. Add the `generate_unique_component_key` function to `src/utils.py`
2. Update citation button key generation in `app_modular.py`
3. Update source expander view button key generation
4. Add error handling around UI component generation
5. Test the solution with various citation patterns and rapid interactions

## Testing Scenarios

After implementation, test the following:
1. Generate multiple responses in quick succession
2. Generate responses with overlapping citation numbers
3. Click citation buttons and check they work correctly
4. Verify that source expander view buttons work properly
5. Verify that no key collision errors occur during normal use

## Expected Outcome

- No more key collision errors when generating responses
- Citation buttons work reliably without page reloads
- Source navigation maintains consistent functionality
- User experience is improved with more stable interface