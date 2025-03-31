# Citation Button Further Fix

## New Issue Identified

After implementing the stable key generation approach, we're still experiencing a key collision error:

```
Citation button error: There are multiple elements with the same `key='resp_ea1b15e6_0_btn_1'`. To fix this, please make sure that the `key` argument is unique for each element you create.
```

## Root Cause Analysis

Our revised key generation approach improved stability, but introduced a new issue:
1. The key format `resp_ea1b15e6_0_btn_1` shows we have:
   - Prefix: "resp"
   - Random session ID: "ea1b15e6"
   - Context (response index): "0"
   - Component type: "btn"
   - Identifier (citation number): "1"

2. The issue appears to be that multiple buttons with the same citation number (1) are being generated within the same response. This can happen if:
   - The same citation number appears multiple times in a response
   - The citation processing logic is duplicating entries for the same citation

## Revised Solution Strategy

We need to add another uniqueness factor to our key generation strategy:

1. Add button position (index) to the key generation to differentiate between multiple buttons with the same citation number

2. Modify the `generate_stable_component_key` function in `src/utils.py`:
```python
def generate_stable_component_key(prefix, component_type, identifier, position=None, context=None):
    """
    Generate a unique key for Streamlit UI components that remains stable across reruns.
    
    Args:
        prefix: A prefix for this key (e.g., 'resp', 'src')
        component_type: Type of component (e.g., 'btn', 'input')
        identifier: Specific identifier for this component (e.g., citation number)
        position: Position of the component in a sequence (e.g., button index)
        context: Optional context information (e.g., message index in chat history)
        
    Returns:
        A string key that is unique but stable for the same component
    """
    # Use a combination of:
    # 1. Session-specific random string (create if not exists)
    if 'component_key_random' not in st.session_state:
        st.session_state.component_key_random = str(uuid.uuid4())[:8]
    
    # 2. Context string if provided (e.g., response index in chat history)
    context_str = f"_{context}" if context is not None else ""
    
    # 3. Position string if provided (e.g., button index in sequence)
    position_str = f"_{position}" if position is not None else ""
    
    # 4. Create a stable key that includes position for further uniqueness
    return f"{prefix}_{st.session_state.component_key_random}{context_str}{position_str}_{component_type}_{identifier}"
```

3. Update the citation button implementation in `app_modular.py`:
```python
# Add error handling around button creation
try:
    for i, citation_num in enumerate(sorted(citation_numbers)):
        col_index = i % len(cols)
        with cols[col_index]:
            # Get response index for stable context
            response_index = len(st.session_state.chat_history.get(current_file, [])) - 1
            
            # Generate a stable key for this button, including button position
            button_key = generate_stable_component_key(
                prefix="resp",
                component_type="btn",
                identifier=citation_num,
                position=i,  # Add button position for uniqueness
                context=response_index
            )
            
            if st.button(f"[{citation_num}]", key=button_key,
                       help=f"Jump to source {citation_num} in PDF"):
                # Store the annotation index (0-based) to scroll to
                st.session_state.selected_annotation_index = citation_num - 1
                # Force page rerun
                st.rerun()
```

4. Similarly update the source view button implementation.

## Expected Outcome

1. Citation buttons will appear and remain visible
2. No key collision errors will occur, even with duplicate citation numbers
3. Navigation between citations and PDF annotations will work reliably