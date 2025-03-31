# PDF Annotation Clickable Links Implementation Plan

## Overview
This plan outlines how to implement clickable links between source citations and PDF annotations in the Chat with Docs application. This will create a bidirectional navigation experience where users can click on sources in the chat response to jump to the corresponding page in the PDF, and vice versa.

## Current State Analysis

1. The application uses `streamlit-pdf-viewer` which supports:
   - Displaying PDF documents with annotations
   - An `on_annotation_click` handler (currently only logs to console)
   - `scroll_to_page` and `scroll_to_annotation` parameters for navigation

2. Sources are currently displayed in two places:
   - In the response text as citation numbers like [1], [2], etc.
   - In the "Source Information" expander with detailed source content

3. The `create_annotations_from_sources()` function creates annotations for source citations

4. The application has document-specific response storage in `st.session_state.document_responses`

## Implementation Steps

### 1. Enhanced Source Formatting with Clickable Links

Modify the `format_source_for_display()` function in `src/source.py` to include clickable elements:

```python
def format_source_for_display(source, citation_num=None):
    """
    Format a source for display in the UI with clickable links to annotations.
    
    Args:
        source: The source node
        citation_num: Optional citation number
        
    Returns:
        A tuple of (formatted_markdown, source_text)
    """
    try:
        # Extract metadata and text based on source type (existing code)
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
        header = f"### Source [{citation_num}]"
        source_id = f"Source [{citation_num}]"
        
        # Add jump to annotation button
        header_with_button = f"{header} <span style='float:right;'><button onclick=\"jumpToAnnotation({citation_num-1})\">View in PDF</button></span>"
    else:
        header = "### Source"
        header_with_button = header
        source_id = "Source"
    
    markdown = f"{header_with_button}\n**Page:** {page_num}\n\n**Text:**\n```\n{text}\n```"
    source_text = f"{source_id} (Page {page_num}):\n{text}"
    
    return markdown, source_text
```

### 2. Add JavaScript Component for Navigation

Create a new file `src/components.py` to handle the JavaScript integration:

```python
import streamlit as st

def add_pdf_navigation_js():
    """
    Add JavaScript code for PDF navigation functionality.
    This enables clicking on sources to navigate to the corresponding annotation.
    """
    js_code = """
    <script>
    // Function to navigate to a specific annotation
    function jumpToAnnotation(annotationIndex) {
        // Store the annotation index in sessionStorage
        sessionStorage.setItem('jumpToAnnotation', annotationIndex);
        // Force page reload to apply the navigation
        window.location.reload();
        return false;
    }
    
    // Function to navigate to a specific page
    function jumpToPage(pageNum) {
        // Store the page number in sessionStorage
        sessionStorage.setItem('jumpToPage', pageNum);
        // Force page reload to apply the navigation
        window.location.reload();
        return false;
    }
    
    // Check if we need to jump to an annotation on page load
    document.addEventListener('DOMContentLoaded', function() {
        const jumpToAnnotation = sessionStorage.getItem('jumpToAnnotation');
        if (jumpToAnnotation !== null) {
            // Clear the storage to avoid repeated jumps
            sessionStorage.removeItem('jumpToAnnotation');
            // Send a custom event that Streamlit can intercept
            const event = new CustomEvent('jumpToAnnotation', { detail: jumpToAnnotation });
            window.dispatchEvent(event);
        }
        
        const jumpToPage = sessionStorage.getItem('jumpToPage');
        if (jumpToPage !== null) {
            // Clear the storage to avoid repeated jumps
            sessionStorage.removeItem('jumpToPage');
            // Send a custom event that Streamlit can intercept
            const event = new CustomEvent('jumpToPage', { detail: jumpToPage });
            window.dispatchEvent(event);
        }
    });
    </script>
    """
    
    # Inject the JavaScript code
    st.markdown(js_code, unsafe_allow_html=True)

def add_streamlit_js_handlers():
    """
    Add Streamlit JavaScript event handlers for PDF navigation.
    This uses streamlit-js-eval to capture browser events.
    """
    from streamlit_js_eval import streamlit_js_eval
    
    # Set up event listener for jumpToAnnotation
    annotation_index = streamlit_js_eval(
        """
        // Create a promise that will be resolved when the event is triggered
        const annotationPromise = new Promise((resolve) => {
            window.addEventListener('jumpToAnnotation', (event) => {
                resolve(event.detail);
            });
            
            // Resolve with null after a short timeout if no event is triggered
            setTimeout(() => resolve(null), 500);
        });
        
        // Return the promise
        return annotationPromise;
        """,
        key="annotation_listener"
    )
    
    # Set up event listener for jumpToPage
    page_num = streamlit_js_eval(
        """
        // Create a promise that will be resolved when the event is triggered
        const pagePromise = new Promise((resolve) => {
            window.addEventListener('jumpToPage', (event) => {
                resolve(event.detail);
            });
            
            // Resolve with null after a short timeout if no event is triggered
            setTimeout(() => resolve(null), 500);
        });
        
        // Return the promise
        return pagePromise;
        """,
        key="page_listener"
    )
    
    # Update session state with navigation requests
    if annotation_index is not None and annotation_index != "null":
        st.session_state.scroll_to_annotation_index = int(annotation_index)
        # Clear page navigation to avoid conflicts
        st.session_state.scroll_to_page = None
        
    if page_num is not None and page_num != "null":
        st.session_state.scroll_to_page = int(page_num)
        # Clear annotation navigation to avoid conflicts
        st.session_state.scroll_to_annotation_index = None
```

### 3. Update Annotation Click Handler

Enhance the `annotation_click_handler` function in `app_modular.py`:

```python
def annotation_click_handler(annotation):
    """Handle clicks on source annotations in the PDF viewer."""
    # Store the clicked annotation in session state
    st.session_state.last_clicked_annotation = annotation
    
    # Get page number
    page = annotation.get('page', 'unknown')
    
    # Try to extract citation number
    citation_num = None
    if 'title' in annotation and annotation['title'].startswith('Source ['):
        # Extract citation number from "Source [X]"
        match = re.search(r'\[(\d+)\]', annotation['title'])
        if match:
            citation_num = int(match.group(1))
    elif 'label' in annotation and annotation['label'].startswith('['):
        # Extract citation number from "[X]"
        match = re.search(r'\[(\d+)\]', annotation['label'])
        if match:
            citation_num = int(match.group(1))
    
    # Store the clicked citation for highlighting in UI
    if citation_num:
        st.session_state.highlighted_citation = citation_num
        # Also log this action
        print(f"Annotation clicked for citation [{citation_num}] on page {page}")
    else:
        print(f"Annotation clicked on page {page} (no citation number found)")
    
    # Force a rerun to update the UI
    st.rerun()
```

### 4. Update Main Application to Support Navigation

Modify the `main()` function in `app_modular.py` to add navigation support:

```python
# Near the beginning of main()
# Import new components
from src.components import add_pdf_navigation_js, add_streamlit_js_handlers

# Initialize navigation session state variables
if 'scroll_to_page' not in st.session_state:
    st.session_state.scroll_to_page = None
if 'scroll_to_annotation_index' not in st.session_state:
    st.session_state.scroll_to_annotation_index = None
if 'highlighted_citation' not in st.session_state:
    st.session_state.highlighted_citation = None

# Add JavaScript components
add_pdf_navigation_js()
add_streamlit_js_handlers()
```

### 5. Update PDF Viewer Integration

Modify the PDF viewer parameters in both PDF display blocks in `app_modular.py`:

```python
# Display the PDF with the viewer (around line 661 and line 696)
pdf_viewer(
    input=pdf_binary,
    annotations=annotations,
    annotation_outline_size=5,  # Make outlines more visible
    height=800,
    on_annotation_click=annotation_click_handler,
    # Add navigation parameters
    scroll_to_page=st.session_state.get('scroll_to_page'),
    scroll_to_annotation=st.session_state.get('scroll_to_annotation_index')
)

# After displaying the PDF, clear the navigation parameters to avoid repeated scrolling
st.session_state.scroll_to_page = None
st.session_state.scroll_to_annotation_index = None
```

### 6. Make Sources in Chat Response Clickable

When displaying sources in the response expander, update to include clickable buttons:

```python
# Update the source display in chat_tab (around line 810)
with st.expander("Source Information"):
    for citation_num in sorted(citation_numbers):
        source_index = citation_num - 1
        
        try:
            if source_index in displayed_sources:
                continue  # Skip if already displayed
            
            if source_index < len(response_data['sources']):
                source = response_data['sources'][source_index]
                
                # Format the source for display with clickable elements
                markdown, source_text = format_source_for_display(source, citation_num)
                
                # Check if this source should be highlighted
                if st.session_state.get('highlighted_citation') == citation_num:
                    st.markdown(markdown, unsafe_allow_html=True)
                    # Add highlight effect
                    st.success(f"This source was clicked in the PDF viewer")
                    # Reset highlight after displaying
                    st.session_state.highlighted_citation = None
                else:
                    st.markdown(markdown, unsafe_allow_html=True)
                
                # Add to tracking set and sources list for history
                displayed_sources.add(source_index)
                sources.append(source_text)
                
                # Add horizontal rule between sources
                if citation_num != sorted(citation_numbers)[-1]:
                    st.markdown("---")
        except IndexError:
            st.warning(f"Citation [{citation_num}] does not match any available source.")
```

### 7. Add Citation Number Links in Response Text

To make citation numbers in the response text clickable, add post-processing to the displayed response:

```python
# In the chat message display section (around line 795)
# Original:
# st.markdown(response_data['answer'])

# Replace with:
answer_text = response_data['answer']
# Add clickable links to citation numbers
linked_answer = re.sub(
    r'\[(\d+)\]',
    r'<a href="#" onclick="jumpToAnnotation(\g<1>-1); return false;">[\g<1>]</a>',
    answer_text
)
st.markdown(linked_answer, unsafe_allow_html=True)
```

## Alternative Implementation (Streamlit Components Only)

If the JavaScript approach has issues, we can implement a simpler version using only Streamlit components:

```python
# In the source display section
for citation_num in sorted(citation_numbers):
    # Display source information
    st.markdown(f"### Source [{citation_num}]")
    st.markdown(f"**Page:** {page_num}")
    
    # Add a button to navigate to this source in the PDF
    if st.button(f"View Source [{citation_num}] in PDF", key=f"src_btn_{citation_num}"):
        st.session_state.scroll_to_page = page_num
        st.rerun()
```

## Testing Plan

1. **Basic Navigation Flow**:
   - Display a document with sources
   - Generate a response with citations
   - Click on a source in the expander and verify it navigates to the correct page
   - Click on a citation number in the response and verify it navigates to the correct annotation
   - Click on an annotation in the PDF and verify it highlights the corresponding source

2. **Multiple Document Support**:
   - Test with multiple documents loaded
   - Ensure navigation works correctly for each document
   - Verify annotations and navigation are document-specific

3. **Edge Cases**:
   - Test with sources that don't have valid page numbers
   - Test with very long documents
   - Test with multiple citations referring to the same page

## Implementation Flow

```mermaid
flowchart TD
    A[User Gets Response with Citations] --> B[Display Response with Clickable Citations]
    B --> C[Display Sources in Expander with Navigation Buttons]
    D[User Clicks Citation in Response] --> E[Navigate to Annotation in PDF]
    F[User Clicks View Button in Source] --> E
    G[User Clicks Annotation in PDF] --> H[Highlight Corresponding Source in Expander]
    I[PDF Viewer Component] --> J[Shows Annotations with Clickable Areas]