# Citation Button and Source Format Implementation Details

## Implementation Instructions

Based on our analysis, we need to make changes to fix two issues:
1. Citation buttons not jumping to the specific annotation/page
2. Poor source formatting in the expander

Here are the detailed implementation steps:

### Part 1: Fix Citation Button Navigation

#### 1. Modify the Navigation State Management

**File:** `app_modular.py`

**Changes:**

1. First, ensure navigation state variables are initialized in the `initialize_session_state` function. Look for this function in `utils.py` or at the beginning of `app_modular.py` and add:

```python
def initialize_session_state():
    # Existing initialization code...
    
    # Add these lines:
    if 'navigation_requested' not in st.session_state:
        st.session_state.navigation_requested = False
    if 'navigation_attempted' not in st.session_state:
        st.session_state.navigation_attempted = False
```

2. Update the PDF viewer rendering code. Look for both instances of `pdf_viewer()` calls and modify the code after each to properly handle navigation state:

```python
# Find this code block (appears twice in app_modular.py)
pdf_viewer(
    input=pdf_binary,
    annotations=annotations,
    annotation_outline_size=5,
    height=800,
    on_annotation_click=annotation_click_handler,
    # Use either annotation or page scrolling, but not both
    scroll_to_annotation=(
        None if st.session_state.get('scroll_to_page') is not None
        else st.session_state.get('selected_annotation_index')
    ),
    scroll_to_page=st.session_state.get('scroll_to_page')
)

# Replace the code that follows (which clears navigation state too early) with:
# Track that we've attempted navigation if requested
if (st.session_state.get('selected_annotation_index') is not None or 
    st.session_state.get('scroll_to_page') is not None):
    st.session_state.navigation_attempted = True

# Do NOT clear navigation state here - we'll handle it after navigation is completed
```

3. Add a separate section at the very end of the main function to clear navigation state only after the entire page has rendered:

```python
# Add this at the end of the main() function, just before the if __name__ == "__main__" block
    # Clear navigation state only AFTER the entire page has rendered
    # This allows the PDF viewer to properly use the navigation parameters
    if st.session_state.get('navigation_attempted') and st.session_state.get('navigation_requested'):
        # Clear for next run, now that navigation has been processed
        st.session_state.navigation_requested = False
        st.session_state.navigation_attempted = False
        # Only now clear the actual navigation parameters
        if 'selected_annotation_index' in st.session_state:
            st.session_state.selected_annotation_index = None
        if 'scroll_to_page' in st.session_state:
            st.session_state.scroll_to_page = None
```

#### 2. Update Citation Button Callback Functions

**File:** `app_modular.py`

**Changes:**

Look for the `citation_page_clicked` and `citation_annotation_clicked` functions and update them:

```python
def citation_page_clicked(citation_num, page_num):
    """Callback for citation buttons with page numbers"""
    # Clear any conflicting navigation state
    st.session_state.selected_annotation_index = None
    # Set the page to scroll to
    st.session_state.scroll_to_page = page_num
    # Set a flag to track this navigation request
    st.session_state.navigation_requested = True
    print(f"Citation {citation_num} clicked: scrolling to page {page_num}")
    # No explicit rerun needed - Streamlit will rerun after callback

def citation_annotation_clicked(citation_num):
    """Callback for citation buttons without page numbers"""
    # Clear any conflicting navigation state
    st.session_state.scroll_to_page = None
    # Set the annotation index to scroll to
    st.session_state.selected_annotation_index = citation_num - 1
    # Set a flag to track this navigation request
    st.session_state.navigation_requested = True
    print(f"Citation {citation_num} clicked: setting annotation index {citation_num - 1}")
    # No explicit rerun needed - Streamlit will rerun after callback
```

### Part 2: Improve Source Formatting

#### 1. Update the Source Display Format

**File:** `src/source.py`

**Changes:**

Modify the `format_source_for_display` function:

```python
def format_source_for_display(source, citation_num=None):
    """
    Format a source for display in the UI with improved styling.
    
    Args:
        source: The source node
        citation_num: Optional citation number
        
    Returns:
        A tuple of (formatted_markdown, source_text)
    """
    try:
        # Extract metadata and text based on source type
        if hasattr(source, 'node'):
            page_num = source.node.metadata.get('page', 'N/A')
            text = source.node.text.strip()
        elif hasattr(source, 'metadata') and hasattr(source, 'text'):
            page_num = source.metadata.get('page', 'N/A')
            text = source.text.strip()
        else:
            page_num = 'Unknown'
            text = str(source) if source is not None else 'No text available'
    except Exception as e:
        page_num = 'Error'
        text = f"Could not extract source text: {str(e)}"
    
    # Format with citation number if provided
    if citation_num:
        source_id = f"Source [{citation_num}]"
    else:
        source_id = "Source"
    
    # Create a cleaner, more readable format without code blocks
    markdown = f"**{source_id} (Page {page_num}):**\n\n{text}"
    source_text = f"{source_id} (Page {page_num}):\n{text}"
    
    return markdown, source_text
```

## Testing Procedure

After implementing these changes, follow this testing procedure:

1. **Citation Button Navigation Test:**
   - Upload a PDF document
   - Chat with the document to generate citations
   - Click on citation buttons in the response
   - Verify that the PDF viewer jumps to the correct page or annotation
   - Test repeatedly to ensure navigation works consistently

2. **Source Format Test:**
   - Examine the source format in the expandable section
   - Verify that source and page numbers are bold and prominent
   - Confirm text is displayed in a readable format without code blocks
   - Check with different length sources to ensure consistent formatting

## Troubleshooting

If navigation issues persist:
1. Check browser console for any errors
2. Add additional debug print statements to track state changes
3. Verify that the navigation state flags are being properly set and cleared

If source format issues persist:
1. Inspect the HTML output to see if Markdown is being properly rendered
2. Try different formatting approaches for complex text