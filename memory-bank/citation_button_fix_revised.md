# Citation Button Fix - Revised Approach

## Issue Identified

After implementing the initial solution from `citation_buttons_fix_plan.md`, we discovered that the citation buttons no longer appear in the UI. The root cause is that our key generation approach creates completely new unique keys on every Streamlit rerun, causing the buttons to be recreated rather than preserved.

Key Insight: In Streamlit, elements with new IDs replacing previous elements causes the previous elements to be erased after a rerun.

## Revised Solution

We need to modify the `generate_unique_component_key` function to create keys that are still unique between different citations, but consistent across reruns for the same citation in the same chat response.

### 1. Update the Key Generation Function in `src/utils.py`

```python
def generate_stable_component_key(prefix, component_type, identifier, context=None):
    """
    Generate a unique key for Streamlit UI components that remains stable across reruns.
    
    Args:
        prefix: A prefix for this key (e.g., 'resp', 'src')
        component_type: Type of component (e.g., 'btn', 'input')
        identifier: Specific identifier for this component (e.g., citation number)
        context: Optional context information (e.g., message index in chat history)
        
    Returns:
        A string key that is unique but stable for the same component
    """
    # Use a combination of:
    # 1. Session-specific random string (create if not exists)
    if 'component_key_random' not in st.session_state:
        import uuid
        st.session_state.component_key_random = str(uuid.uuid4())[:8]
    
    # 2. Context string if provided (e.g., response index in chat history)
    context_str = f"_{context}" if context is not None else ""
    
    # 3. Create a stable key without timestamps or incrementing counters
    return f"{prefix}_{st.session_state.component_key_random}{context_str}_{component_type}_{identifier}"
```

### 2. Update Citation Button Implementation in `app_modular.py`

Update how citation buttons are created in the chat response display:

```python
# For citation buttons below the response
for i, citation_num in enumerate(sorted(citation_numbers)):
    col_index = i % len(cols)
    with cols[col_index]:
        # Get a stable message index for context
        response_index = len(st.session_state.chat_history.get(current_file, [])) - 1
        
        # Use the stable key generator
        button_key = generate_stable_component_key(
            prefix="resp",
            component_type="btn",
            identifier=citation_num,
            context=response_index  # Only changes when new responses are added
        )
        
        if st.button(f"[{citation_num}]", key=button_key,
                   help=f"Jump to source {citation_num} in PDF"):
            # Store the annotation index (0-based) to scroll to
            st.session_state.selected_annotation_index = citation_num - 1
            # Force page rerun
            st.rerun()
```

### 3. Update Source Expander View Button Keys

Similarly update the source expander view buttons:

```python
# For view buttons in the source expander
button_key = generate_stable_component_key(
    prefix="src",
    component_type="view",
    identifier=citation_num,
    context=len(st.session_state.chat_history.get(current_file, [])) - 1
)

if st.button("👁️ View", key=button_key,
           help=f"Jump to source {citation_num} in PDF"):
    # Store the annotation index to scroll to
    st.session_state.selected_annotation_index = source_index
    # Force page rerun
    st.rerun()
```

### 4. Implementation Steps

1. Add the new `generate_stable_component_key` function to `src/utils.py`
2. Keep the existing `generate_unique_component_key` function for other uses (optional)
3. Update citation button implementation to use the stable key generator
4. Update source expander view button implementation to use the stable key generator
5. Test to ensure buttons persist across reruns while still avoiding key collisions

### 5. Testing Strategy

After implementation, test the following:
1. Generate multiple responses and verify citation buttons appear and persist
2. Click citation buttons to verify they navigate to the correct annotation
3. Generate responses with overlapping citation numbers and verify all buttons work
4. Verify source expander view buttons also work correctly
5. Check that no key collision errors occur during normal use

### 6. Expected Outcome

- Citation buttons appear and remain visible across reruns
- No key collision errors occur between different citation buttons
- UI remains stable without buttons disappearing or flickering
- Navigation between citations and PDF annotations works reliably