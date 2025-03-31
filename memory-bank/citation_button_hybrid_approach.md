# Citation Button Hybrid Approach

## Key Insight

After analyzing the code and previous solutions, we've identified the key issue:

**Annotations are message-specific and do not persist in the PDF viewer across different messages**. This means:
- Current/latest message: Citation buttons can use annotation indices
- Historical messages: Citation buttons must use page numbers since annotations are gone

## Hybrid Navigation Approach

The solution requires a hybrid approach that uses different navigation methods depending on whether the button is in the latest response or a historical one:

1. **Latest response buttons**: Use `scroll_to_annotation_index` to jump to specific annotations
2. **Historical message buttons**: Use `scroll_to_page` to jump to the page where the source was found

## Implementation Strategy

### 1. Store Citation Page Information

Ensure complete page information is stored with each assistant message:

```python
# Extract and store page numbers for each citation
citation_page_map = {}
for idx in sorted(list(unique_citation_numbers)):
    if idx <= len(response_data['sources']):
        source = response_data['sources'][idx-1]
        # Extract page number based on source type
        page_num = 0
        if hasattr(source, 'node'):
            page_num = source.node.metadata.get('page', 0)
        elif hasattr(source, 'metadata') and hasattr(source, 'text'):
            page_num = source.metadata.get('page', 0)
        
        # Convert to int if possible
        try:
            page_num = int(page_num)
        except (ValueError, TypeError):
            page_num = 0
        
        citation_page_map[str(idx)] = page_num  # Use string keys for JSON compatibility

# Store in session state for the current response
st.session_state.current_citation_pages = citation_page_map

# Also store in the chat history entry for future reference
st.session_state.chat_history[current_file].append({
    "role": "assistant",
    "content": response_data['answer'],
    "citations": sorted(list(unique_citation_numbers)),
    "citation_pages": citation_page_map,
    "response_id": len(st.session_state.chat_history.get(current_file, []))
})
```

### 2. Implement Hybrid Button Callbacks

#### For Current Response Buttons (Annotation-based)

```python
# Define callback for citation buttons in current response
def current_citation_clicked(citation_num):
    """Callback for citation buttons in current response - uses annotation index"""
    # Clear any existing page scroll to prioritize annotation
    if 'scroll_to_page' in st.session_state:
        st.session_state.scroll_to_page = None
    # Set the annotation index to scroll to
    st.session_state.selected_annotation_index = citation_num - 1

# Create buttons for current response
for i, citation_num in enumerate(sorted(unique_citation_numbers)):
    col_index = i % len(cols)
    with cols[col_index]:
        st.button(
            f"[{citation_num}]",
            on_click=current_citation_clicked,
            kwargs={"citation_num": citation_num},
            help=f"Jump to source {citation_num} in PDF"
        )
```

#### For Historical Message Buttons (Page-based)

```python
# When displaying the chat history:
if current_file in st.session_state.chat_history:
    for msg_idx, msg in enumerate(st.session_state.chat_history[current_file]):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
            # Display citation buttons for assistant messages
            if msg["role"] == "assistant":
                # Current message was already handled with annotation-based navigation
                if msg_idx == len(st.session_state.chat_history[current_file]) - 1:
                    continue
                    
                # Check if there are citations in this message
                citation_numbers = msg.get("citations", [])
                citation_pages = msg.get("citation_pages", {})
                
                if citation_numbers:
                    st.markdown("**Jump to citation:** ", unsafe_allow_html=True)
                    
                    # Create a row of citation buttons
                    cols = st.columns(min(len(citation_numbers), 10))
                    
                    # Define callback function for historical citation clicks - uses page number
                    def historical_citation_clicked(citation_num, page_num):
                        """Callback for citation buttons in historical messages - uses page number"""
                        # Clear any existing annotation scroll
                        if 'selected_annotation_index' in st.session_state:
                            st.session_state.selected_annotation_index = None
                        # Set the page to scroll to
                        st.session_state.scroll_to_page = page_num
                    
                    # Create buttons with callbacks
                    for i, citation_num in enumerate(sorted(citation_numbers)):
                        col_index = i % len(cols)
                        
                        # Get page number for this citation
                        page_num = citation_pages.get(str(citation_num), 0)
                        
                        with cols[col_index]:
                            # Only create the button if we have a valid page number
                            if page_num > 0:
                                st.button(
                                    f"[{citation_num}]",
                                    on_click=historical_citation_clicked,
                                    kwargs={"citation_num": citation_num, "page_num": page_num},
                                    help=f"Jump to page {page_num} in PDF"
                                )
                            else:
                                # Display a disabled placeholder if no page info
                                st.markdown(f"<span style='color:gray'>[{citation_num}]</span>", unsafe_allow_html=True)
```

### 3. Update PDF Viewer Parameters

Ensure the PDF viewer can handle both navigation methods:

```python
# In the PDF viewer component
pdf_viewer(
    input=pdf_binary,
    annotations=annotations,
    annotation_outline_size=5,  # Make outlines more visible
    height=800,
    on_annotation_click=annotation_click_handler,
    # Use either annotation or page scrolling, but not both
    scroll_to_annotation=(
        None if st.session_state.get('scroll_to_page') is not None
        else st.session_state.get('selected_annotation_index')
    ),
    scroll_to_page=st.session_state.get('scroll_to_page')
)

# Clear navigation parameters after rendering
if st.session_state.get('selected_annotation_index') is not None:
    st.session_state.selected_annotation_index = None
if st.session_state.get('scroll_to_page') is not None:
    st.session_state.scroll_to_page = None
```

## Migration of Existing Data

To ensure this works with existing chat history, we need to check if citation page information exists and add it for older messages if missing:

```python
# At app startup, check if chat history needs to be migrated
if 'chat_history_migrated_v3' not in st.session_state:
    print("Migrating chat history to add citation page information")
    for file_name, messages in st.session_state.get('chat_history', {}).items():
        for msg in messages:
            if msg["role"] == "assistant":
                # Add empty citation_pages dictionary if not present
                if "citation_pages" not in msg:
                    msg["citation_pages"] = {}
                    
                # Extract citations if not already present
                if "citations" not in msg:
                    all_citation_numbers = extract_citation_indices(msg["content"])
                    msg["citations"] = sorted(list(set(all_citation_numbers)))
    
    st.session_state.chat_history_migrated_v3 = True
```

## Handling Edge Cases

### 1. Different Documents

If the user switches documents, we need to ensure citation buttons are only shown when appropriate:

```python
# Only display citation buttons for the current document's messages
if msg.get("document") != current_file:
    # Either hide buttons or display them with a note
    st.info("Citations refer to another document")
```

### 2. Missing Page Information

For older messages that don't have page information, we can either:
- Display disabled citation indicators (not clickable)
- Attempt to recreate the page information if the document is still available

### 3. Large Number of Citations

For messages with many citations, implement a scrollable or paginated citation button display:

```python
# If more than 10 citations, create a scrollable area
if len(citation_numbers) > 10:
    with st.container(height=100, border=True):
        cols = st.columns(5)  # Use 5 columns in the scrollable area
        # Rest of the button creation code...
```

## Implementation Plan

1. Update the code to store citation page information with each message
2. Implement the hybrid navigation approach:
   - Annotation-based for current/latest message
   - Page-based for historical messages
3. Add migration code for existing chat history
4. Add error handling and fallbacks for edge cases
5. Test thoroughly with different documents and message patterns

## Testing Strategy

1. Latest response: Citation buttons should scroll to highlighted annotations
2. Historical messages: Citation buttons should scroll to the correct page
3. Multiple documents: Switching between documents should maintain proper citation navigation
4. Migration: Older chat history should work with the new system

## Implementation Instructions

Now that we have a comprehensive plan, let's implement this solution. The following files need to be modified:

### 1. app_modular.py

This is the main file to be updated. We need to:
- Update the response generation code to store page information
- Implement the hybrid navigation approach with different callbacks
- Update the PDF viewer parameters
- Add migration code for existing chat history

### 2. src/utils.py

Potentially add helper functions if needed.

## Implementation Steps

1. First, implement the citation page information storage in the response generation section
2. Add the dual-callback system for navigation
3. Modify the PDF viewer component to handle both navigation methods
4. Add migration code for existing chat history at app startup
5. Test all the components together

Let's proceed with implementation by switching to Code mode.
5. Edge cases: Test behavior with missing data, many citations, etc.