# Citation Button Persistence Solution

## Problem Analysis

After implementing deduplication for citation numbers, the duplicate ID error is resolved, but now we have a new issue: the citation buttons are not showing up in the UI.

### Key Findings:

1. The buttons are created correctly in the code but don't appear in the UI
2. The app uses `st.rerun()` multiple times in the annotation click handler:
   ```python
   # Force a page rerun to highlight the corresponding source
   st.rerun()
   st.rerun()
   ```
3. Streamlit recreates dynamic UI elements on each rerun, and the buttons are being lost during this process

## Root Cause

When a user interacts with annotations in the PDF, the application calls `st.rerun()` to refresh the UI. During this rerun, the dynamic citation buttons are recreated but might not be properly persisted because:

1. The buttons are created during the chat flow but aren't directly tied to the session state
2. Multiple reruns might be clearing or replacing UI elements
3. The citation information might not be properly stored between reruns

## Solution Strategy

To resolve this issue, we need a solution that:
1. Persists citation information in session state for reliability
2. Creates buttons in a way that survives reruns
3. Addresses the multiple st.rerun() issue

### Implementation Plan

1. **Store Citation Information in Session State**
   ```python
   # After extracting unique citation numbers, store them in session state
   st.session_state.current_response_citations = sorted(list(unique_citation_numbers))
   ```

2. **Fix the Redundant Rerun Calls in Annotation Handler**
   ```python
   # Replace multiple rerun calls with a single call
   # st.rerun()
   # st.rerun()
   st.rerun()  # Single rerun is sufficient
   ```

3. **Use Session State to Recreate Buttons on Each Render**
   ```python
   # Create buttons from session state rather than from scratch
   if 'current_response_citations' in st.session_state:
       # Display citation navigation
       st.markdown("**Jump to citation:** ", unsafe_allow_html=True)
       cols = st.columns(min(len(st.session_state.current_response_citations), 10))
       
       for i, citation_num in enumerate(st.session_state.current_response_citations):
           col_index = i % len(cols)
           with cols[col_index]:
               btn_key = f"citation_btn_{i}_{citation_num}"
               if st.button(f"[{citation_num}]", key=btn_key, 
                           help=f"Jump to source {citation_num} in PDF"):
                   st.session_state.selected_annotation_index = citation_num - 1
                   st.rerun()
   ```

4. **Add Extra Debugging to Track Button Creation and Visibility**
   ```python
   # Add log statements to verify button creation
   print(f"Creating {len(st.session_state.current_response_citations)} citation buttons")
   # Log when buttons are created
   print(f"Created button for citation {citation_num} with key {btn_key}")
   ```

## Additional Recommendations

1. **Avoid Multiple Reruns**: Remove the double `st.rerun()` call from the annotation click handler.

2. **Use Explicit Keys**: Always provide explicit unique keys for all Streamlit UI components to avoid collisions.

3. **Persistent UI Pattern**: Move critical UI elements to a separate function that's always called during page rendering and relies on session state, not transient variables.

4. **Consider Container Isolation**: Use containers to isolate different parts of the UI and prevent unwanted interactions.

## Testing Strategy

After implementing the changes:

1. Submit a chat query and verify citation buttons appear in the response
2. Click on citation buttons to navigate to PDF annotations
3. Click on annotations in the PDF to verify they highlight correctly
4. Check console logs to ensure buttons are being created without errors
5. Verify that all buttons are visible and functional after multiple interactions

## Expected Outcome

- Citation buttons will be visible and functional in the chat UI
- Clicking citations and annotations will work correctly
- No errors or missing UI elements after reruns