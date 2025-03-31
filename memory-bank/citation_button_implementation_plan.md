# Citation Button Hybrid Navigation Implementation Plan

## Overview

This plan details the implementation steps for the hybrid citation button navigation solution. We'll modify the application to handle citation buttons differently based on whether they're in the most recent message (annotation-based navigation) or previous messages (page-based navigation).

## Implementation Steps

### 1. Add Page Number Storage for Citations

First, we need to modify how we store citation information to include page numbers:

```python
# Around line 835-841 in app_modular.py (after extracting citation numbers)
# Extract and store page numbers for each citation
citation_page_map = {}
for idx in sorted(list(unique_citation_numbers)):
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
            
        citation_page_map[str(idx)] = page_num  # Use string keys for JSON compatibility

# Now store page map in session state
st.session_state.current_citation_pages = citation_page_map
```

### 2. Update Chat Message Storage

Modify the chat message structure to include citation page information:

```python
# Around line 978-988 in app_modular.py
chat_message = {
    "role": "assistant",
    "content": response_data['answer'],
    "sources": sources,
    "images": [{
        "path": img['path'],
        "caption": img.get('caption', "Document Image")
    } for img in images],
    # Add citation numbers and page info
    "citations": st.session_state.current_response_citations,
    "citation_pages": st.session_state.current_citation_pages,
    "response_id": len(st.session_state.chat_history[current_file])
}
```

### 3. Enhance Chat History Display

Modify the chat history display to handle both types of navigation:

```python
# Replace the chat history display code around line 759-770
if current_file in st.session_state.chat_history:
    # Get the index of the latest message to detect current vs previous
    messages = st.session_state.chat_history[current_file]
    latest_message_index = len(messages) - 1
    
    for i, msg in enumerate(messages):
        is_latest = (i == latest_message_index)
        
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
            # Display citation buttons for assistant messages that have citations
            if msg["role"] == "assistant" and msg.get("citations"):
                citation_numbers = msg.get("citations", [])
                response_id = msg.get("response_id", i)  # Fallback to index
                citation_pages = msg.get("citation_pages", {})  # Get page map
                
                if citation_numbers:
                    st.markdown("**Jump to citation:** ", unsafe_allow_html=True)
                    cols = st.columns(min(len(citation_numbers), 10))
                    
                    try:
                        for j, citation_num in enumerate(sorted(citation_numbers)):
                            col_index = j % len(cols)
                            with cols[col_index]:
                                # Create button with explicit unique key
                                btn_key = f"citation_btn_{response_id}_{j}_{citation_num}"
                                if st.button(
                                    f"[{citation_num}]",
                                    key=btn_key,
                                    help=f"Jump to source {citation_num} in PDF"
                                ):
                                    if is_latest:
                                        # For latest message: use annotation navigation
                                        st.session_state.selected_annotation_index = citation_num - 1
                                        # Clear page navigation
                                        st.session_state.scroll_to_page = None
                                    else:
                                        # For previous messages: use page navigation
                                        # Convert citation_num to string for dict lookup if needed
                                        page_key = str(citation_num) if isinstance(citation_pages, dict) and str(citation_num) in citation_pages else citation_num
                                        page_num = citation_pages.get(page_key, 0)
                                        # Store the page to scroll to
                                        st.session_state.scroll_to_page = page_num
                                        # Clear annotation navigation
                                        st.session_state.selected_annotation_index = None
                                    # No explicit rerun needed - Streamlit will rerun after button action
                    except Exception as e:
                        import traceback
                        st.info(f"Error displaying citation buttons: {str(e)}")
                        print(f"Citation button error: {str(e)}")
                        print(traceback.format_exc())
                
                # Display sources and images as before
                if msg.get("sources"):
                    with st.expander("Sources"):
                        for source_text in msg["sources"]:
                            st.markdown(source_text)
                
                if msg.get("images"):
                    with st.expander("📊 **Related Images:**"):
                        # Existing image display code
```

### 4. Update PDF Viewer to Support Both Navigation Methods

Modify the PDF viewer initialization to support both navigation methods:

```python
# Around line 685 in app_modular.py
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

# Clear navigation parameters after rendering
if st.session_state.get('selected_annotation_index') is not None:
    st.session_state.selected_annotation_index = None
if st.session_state.get('scroll_to_page') is not None:
    st.session_state.scroll_to_page = None
```

### 5. Add Migration for Existing Chat History

Add a migration process to handle existing chat history:

```python
# Add near the beginning of the main function, after initialize_session_state()
# Migrate existing chat history to include page information
if 'chat_history_migrated_v2' not in st.session_state:
    print("Migrating chat history to add citation page information")
    for file_name, messages in st.session_state.get('chat_history', {}).items():
        for i, msg in enumerate(messages):
            if msg["role"] == "assistant":
                # Extract citation numbers if needed
                if "citations" not in msg:
                    all_citation_numbers = extract_citation_indices(msg["content"])
                    msg["citations"] = sorted(list(set(all_citation_numbers)))
                
                # Add response_id if needed
                if "response_id" not in msg:
                    msg["response_id"] = i
                
                # Add empty citation_pages dictionary if not present
                if "citation_pages" not in msg:
                    msg["citation_pages"] = {}
    
    st.session_state.chat_history_migrated_v2 = True
```

### 6. Cleanup: Remove Redundant Button Creation

Remove or comment out the redundant button creation code since it's now handled in the chat history display:

```python
# Remove or comment out sections around lines 849-871
# This citation button creation is now handled in the chat history display
```

## Testing Procedure

1. **Basic Navigation Test**:
   - Submit a query with citations 
   - Verify citation buttons appear in the response
   - Click each button to check it navigates to the correct annotation

2. **Multi-Message Navigation Test**:
   - Submit multiple queries with citations
   - Verify all messages show citation buttons
   - Test buttons in the latest message - should use annotation navigation
   - Test buttons in previous messages - should use page navigation

3. **Rerun Test**:
   - Submit a query with citations
   - Click on a PDF annotation to trigger a rerun
   - Verify all citation buttons are still visible and functional after rerun

4. **Migration Test**:
   - Use an existing session with chat history (if available)
   - Verify existing messages are properly migrated
   - Test citation buttons in migrated messages

5. **Edge Cases**:
   - Test with responses that have no citations
   - Test with a large number of citations
   - Test with page numbers that don't exist in the document

## Fallback Strategies

1. **Session State Issues**:
   - If session state variables are being overwritten, add more descriptive names
   - Use prefixes like `citation_` for all related session state variables

2. **PDF Viewer Parameter Conflicts**:
   - If there are conflicts with navigation parameters, ensure we're clearing them properly
   - Implement a priority system if both navigation parameters are set

3. **Button Key Conflicts**:
   - If button key conflicts occur, add more uniqueness like timestamp or random suffix
   - Monitor Streamlit logs for key-related warnings

4. **Page Number Extraction Failures**:
   - Add more robust fallbacks for page extraction
   - Log warnings but continue with a default page (0)

5. **Complete Fallback**:
   - If the hybrid approach has critical issues, fall back to the simpler solution:
     - Only show citation buttons on the latest message
     - Add a warning that citation navigation is only available for the most recent response

## Next Steps After Implementation

1. Update all relevant documentation
2. Add clear console logs for debugging
3. Consider adding a visual indicator to differentiate between annotation-based and page-based navigation buttons

This implementation will ensure citation buttons work for all messages in the chat history while accounting for the transient nature of PDF annotations.