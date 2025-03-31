# Citation Button Page-Based Solution

## Problem Analysis

I've identified an important issue with the previous solution approach. After careful examination of the code, I now understand that:

1. **Annotations are Transient**: 
   - PDF annotations are created only for the most recent response
   - Each new query creates a new set of annotations, replacing previous ones
   - Lines 668-682 in app_modular.py show that annotations are created from the current document response only

2. **Button Target Issue**:
   - Citation buttons in older messages would point to annotations that no longer exist
   - This explains why buttons disappear or don't work after a new query

3. **Key Insight**:
   - We need to handle citation buttons differently for current vs. previous messages
   - The PDF viewer has two navigation options: `scroll_to_annotation` and `scroll_to_page`

## Solution Strategy: Hybrid Navigation

We should implement a hybrid navigation approach:

1. **Latest Message: Annotation-Based Navigation**
   - The most recent response has valid annotations
   - Citation buttons for the latest message should use `selected_annotation_index` (annotation-based navigation)

2. **Previous Messages: Page-Based Navigation**
   - Previous messages don't have valid annotations anymore
   - Citation buttons for previous messages should use `scroll_to_page` (page-based navigation)

## Implementation Details

### 1. Store Page Numbers with Citations

Modify the chat message structure to store page numbers along with citations:

```python
# Extract and store page numbers for each citation
citation_page_map = {}
for idx in st.session_state.current_response_citations:
    if idx <= len(response_data['sources']):
        source = response_data['sources'][idx-1]
        # Extract page number based on source type
        if hasattr(source, 'node'):
            page_num = source.node.metadata.get('page', 0)
        elif hasattr(source, 'metadata') and hasattr(source, 'text'):
            page_num = source.metadata.get('page', 0)
        else:
            page_num = 0
            
        # Convert to int if possible
        try:
            page_num = int(page_num)
        except (ValueError, TypeError):
            page_num = 0
            
        citation_page_map[idx] = page_num

# Store in chat message
chat_message = {
    "role": "assistant",
    "content": response_data['answer'],
    "sources": sources,
    "images": [...],
    "citations": st.session_state.current_response_citations,
    "citation_pages": citation_page_map,  # Add page information
    "response_id": len(st.session_state.chat_history[current_file])
}
```

### 2. Modify Chat History Display to Use Hybrid Navigation

```python
# Modify the chat history display loop
for i, msg in enumerate(st.session_state.chat_history[current_file]):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        
        # Display citation buttons for assistant messages that have citations
        if msg["role"] == "assistant" and msg.get("citations"):
            citation_numbers = msg.get("citations", [])
            response_id = msg.get("response_id", i)  # Fallback to index
            citation_pages = msg.get("citation_pages", {})  # Get page map
            
            # Check if this is the latest message
            is_latest_message = (i == len(st.session_state.chat_history[current_file]) - 1)
            
            if citation_numbers:
                st.markdown("**Jump to citation:** ", unsafe_allow_html=True)
                cols = st.columns(min(len(citation_numbers), 10))
                
                try:
                    for j, citation_num in enumerate(sorted(citation_numbers)):
                        col_index = j % len(cols)
                        with cols[col_index]:
                            btn_key = f"citation_btn_{response_id}_{j}_{citation_num}"
                            
                            if st.button(f"[{citation_num}]", key=btn_key):
                                if is_latest_message:
                                    # For latest message: use annotation-based navigation
                                    st.session_state.selected_annotation_index = citation_num - 1
                                else:
                                    # For previous messages: use page-based navigation
                                    page_num = citation_pages.get(citation_num, 0)
                                    # Store the page to scroll to
                                    st.session_state.scroll_to_page = page_num
                                # Rerun is handled by Streamlit after button click
                except Exception as e:
                    st.info(f"Error displaying citation buttons: {str(e)}")
```

### 3. Modify PDF Viewer to Support Both Navigation Methods

```python
# In the PDF viewer section (around line 685)
pdf_viewer(
    input=pdf_binary,
    annotations=annotations,
    annotation_outline_size=5,
    height=800,
    on_annotation_click=annotation_click_handler,
    # Use either annotation or page scrolling, never both
    scroll_to_annotation=None if st.session_state.get('scroll_to_page') is not None else st.session_state.get('selected_annotation_index'),
    scroll_to_page=st.session_state.get('scroll_to_page')
)

# Clear navigation parameters after rendering
if st.session_state.get('selected_annotation_index') is not None:
    st.session_state.selected_annotation_index = None
if st.session_state.get('scroll_to_page') is not None:
    st.session_state.scroll_to_page = None
```

### 4. Migration Strategy for Existing Chat History

```python
# Add migration for existing chat history
if 'chat_history_migrated_v2' not in st.session_state:
    print("Migrating chat history to include page information")
    for file_name, messages in st.session_state.get('chat_history', {}).items():
        for i, msg in enumerate(messages):
            if msg["role"] == "assistant":
                # Extract citation numbers if needed
                if "citations" not in msg:
                    all_citation_numbers = extract_citation_indices(msg["content"])
                    msg["citations"] = sorted(list(set(all_citation_numbers)))
                    msg["response_id"] = i
                
                # Add empty citation_pages dictionary if not present
                if "citation_pages" not in msg:
                    msg["citation_pages"] = {}
    
    st.session_state.chat_history_migrated_v2 = True
```

## Benefits of this Approach

1. **Backwards Compatibility**: Older messages still have functional citation buttons
2. **User Experience**: All citation buttons work as expected, even after new queries
3. **Implementation Simplicity**: Uses existing page information without major changes
4. **Performance**: No need to store/restore multiple sets of annotations

## Testing Strategy

1. Submit a query with citations and verify the buttons work
2. Submit a second query and verify:
   - First message's citation buttons navigate to the correct pages
   - Latest message's citation buttons navigate to the correct annotations
3. Test with different documents and multiple messages
4. Verify behavior after page refreshes and reruns

This solution ensures citation buttons remain functional for all messages in the chat history, while respecting the transient nature of PDF annotations.