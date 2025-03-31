# Citation Button Callback Solution

## Alternative Approach: Using Callbacks Instead of Keys

Rather than trying to create unique keys for each button, we can use Streamlit's callback functionality to handle button clicks without explicitly specifying keys. This approach completely avoids key collision issues.

## Example Pattern

The following pattern demonstrates how to create multiple buttons without specifying keys:

```python
import streamlit as st

def on_button_click(citation_num):
    st.session_state.selected_annotation_index = citation_num - 1
    # Rerun will happen after the callback completes

# Create a row of citation buttons
cols = st.columns(min(len(citation_numbers), 10))  # Limit to 10 columns max

for i, citation_num in enumerate(sorted(citation_numbers)):
    col_index = i % len(cols)
    with cols[col_index]:
        st.button(
            f"[{citation_num}]", 
            on_click=on_button_click, 
            kwargs={"citation_num": citation_num},
            help=f"Jump to source {citation_num} in PDF"
        )
```

## Implementation Plan

1. **Refactor Citation Buttons in `app_modular.py`**:

```python
# Define the callback function above the button creation
def citation_button_clicked(citation_num):
    """Callback function for citation button clicks"""
    # Store the annotation index (0-based) to scroll to
    st.session_state.selected_annotation_index = citation_num - 1
    # The page will rerun after the callback completes

# Add error handling around button creation
try:
    for i, citation_num in enumerate(sorted(citation_numbers)):
        col_index = i % len(cols)
        with cols[col_index]:
            # Create button with callback instead of key
            st.button(
                f"[{citation_num}]", 
                on_click=citation_button_clicked, 
                kwargs={"citation_num": citation_num},
                help=f"Jump to source {citation_num} in PDF"
            )
except Exception as e:
    import traceback
    error_msg = str(e)
    st.error(f"Error displaying citation buttons: {error_msg}")
    st.info("You can still view sources in the Source Information expander below.")
    # Log the full error for debugging
    print(f"Citation button error: {error_msg}")
    print(traceback.format_exc())
```

2. **Refactor Source View Buttons**:

```python
# Define the callback function
def view_button_clicked(source_index):
    """Callback function for view button clicks"""
    # Store the annotation index to scroll to
    st.session_state.selected_annotation_index = source_index
    # The page will rerun after the callback completes

# In the source expander
st.button(
    "👁️ View", 
    on_click=view_button_clicked, 
    kwargs={"source_index": source_index},
    help=f"Jump to source {citation_num} in PDF"
)
```

3. **Remove the Explicit st.rerun() Calls**:
   - Streamlit will automatically rerun the page after the callback completes
   - No need for explicit `st.rerun()` calls

## Advantages of This Approach

1. **No Key Collisions**: Since we're not specifying keys, Streamlit will auto-generate unique keys internally
2. **Cleaner Code**: Separates the button display from the action logic
3. **More Reliable**: Less prone to errors due to key management
4. **Streamlit Best Practice**: Uses the recommended callback pattern for UI components

## Considerations

1. **Callback Scope**: Ensure the callback functions are defined at the appropriate scope level
2. **Session State**: This approach still uses session state to store the selected annotation index
3. **Error Handling**: Maintain error handling around button creation for robustness