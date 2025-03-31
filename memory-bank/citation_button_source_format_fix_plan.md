# Citation Button and Source Format Fix Plan

## Problem Analysis

Based on the code review, I've identified two distinct issues:

### Issue 1: Citation Buttons Not Working Properly
When clicking citation buttons, the PDF always refreshes to the first page instead of jumping to the specific annotation or page.

**Root Cause:**
- The PDF viewer receives the correct navigation parameters (`scroll_to_annotation` or `scroll_to_page`)
- However, the state is being cleared too early after rendering:
  ```python
  # Clear navigation parameters after rendering
  if st.session_state.get('selected_annotation_index') is not None:
      st.session_state.selected_annotation_index = None
  if st.session_state.get('scroll_to_page') is not None:
      st.session_state.scroll_to_page = None
  ```
- This prevents the PDF viewer from properly navigating to the target location

### Issue 2: Poor Source Formatting in Expander
The sources display in the expander has formatting issues (as shown in the screenshot):
- Source and page numbers aren't prominently displayed
- Content has excessive formatting with code blocks
- Overall readability is poor

**Root Cause:**
- Current formatting in `format_source_for_display()` uses code blocks:
  ```python
  markdown = f"{header}\n**Page:** {page_num}\n\n**Text:**\n```\n{text}\n```"
  ```
- This creates a technical/code-like appearance that isn't user-friendly

## Implementation Plan

### Part 1: Fix PDF Navigation with Citation Buttons

1. **Modify Navigation State Management**:
   - Preserve navigation state throughout the page rendering cycle
   - Use a completed flag to prevent premature clearing

   ```python
   # In the PDF viewer section, change the state clearing logic:
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
        
   # Instead of clearing immediately, set a flag that navigation was attempted
   if st.session_state.get('selected_annotation_index') is not None or st.session_state.get('scroll_to_page') is not None:
       st.session_state.navigation_attempted = True
   
   # Only clear the navigation state if we've successfully rendered the PDF AND navigation was attempted before
   if st.session_state.get('navigation_attempted'):
       # Clear for next run, but not during the current rendering
       st.session_state.navigation_attempted = False
       # We'll handle this in callback functions instead of here
   ```

2. **Improve Callback Functions**:
   - Update callback functions to set state more explicitly
   - Eliminate redundant rerun calls
   - Ensure clean state transitions

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

3. **Add Navigation Completion Check**:
   - Initialize the navigation state variables at the start of the app
   - Add navigation completion check during PDF initialization

   ```python
   # In initialize_session_state function, add:
   if 'navigation_requested' not in st.session_state:
       st.session_state.navigation_requested = False
   if 'navigation_attempted' not in st.session_state:
       st.session_state.navigation_attempted = False
   ```

### Part 2: Improve Source Formatting

1. **Update `format_source_for_display` in `source.py`**:
   - Remove code blocks
   - Improve visual hierarchy
   - Make source and page prominently displayed

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
       
       # Create a cleaner, more readable format
       markdown = f"**{source_id} (Page {page_num}):**\n\n{text}"
       source_text = f"{source_id} (Page {page_num}):\n{text}"
       
       return markdown, source_text
   ```

2. **Update Source Display in App (if needed)**:
   - Make sure the source expander rendering honors the improved formatting

## Testing Strategy

1. **For Citation Button Navigation**:
   - Click on citation buttons in the chat interface
   - Verify that the PDF viewer jumps to the correct page or annotation
   - Test with both recent and historical chat messages
   - Ensure navigation works repeatedly without refreshing the page

2. **For Source Formatting**:
   - Check the appearance of sources in the expandable section
   - Verify that source and page numbers are prominently displayed
   - Confirm the text is formatted in a readable way
   - Test with various source lengths and content types

## Next Steps

1. Implement the PDF navigation changes first
2. Test citation button functionality
3. Implement source formatting improvements
4. Test the visual appearance of source display
5. Document any additional issues or edge cases discovered during testing