# PDF Annotation Implementation Plan

## Overview
This plan outlines the necessary changes to implement PDF page annotations that highlight source pages with red borders when displaying answers in the Chat with Docs application.

## Current State Analysis
1. The application already uses `streamlit_pdf_viewer` which supports annotations
2. Word coordinates are extracted during document processing and available
3. Helper function `create_annotations_from_sources()` exists in `src/source.py` but isn't currently used
4. There are placeholders in `app_modular.py` for annotation logic (lines 626-628 and 648-651)

## Implementation Steps

### 1. Modify `create_annotations_from_sources()` function

Currently, the function in `src/source.py` creates highlight annotations for specific text regions. We need to modify it to create page-level annotations with red borders.

```python
def create_annotations_from_sources(answer_text, sources):
    """
    Create PDF annotations from sources that are cited in the answer text.
    
    Args:
        answer_text: The answer text containing citations
        sources: List of source nodes
        
    Returns:
        A list of annotation dictionaries
    """
    citations = extract_citation_indices(answer_text)
    annotations = []
    
    # Track which pages we've already annotated to avoid duplicates
    annotated_pages = set()
    
    for idx in citations:
        if idx <= len(sources):
            source = sources[idx-1]  # Convert 1-based citation to 0-based index
            
            # Extract page number from source
            page_num = None
            if hasattr(source, 'node'):
                page_num = source.node.metadata.get('page', 0)
            elif hasattr(source, 'metadata') and hasattr(source, 'text'):
                page_num = source.metadata.get('page', 0)
            
            # Only add page annotation if we have a valid page number
            # We'll allow duplicate page annotations with different citation numbers
            if page_num is not None:
                # Create a page-level annotation with a red border and citation label
                page_annotation = {
                    'page': int(page_num),
                    'x': 0,  # Start at left edge
                    'y': 0,  # Start at top
                    'width': 100,  # Cover full width (percentage)
                    'height': 100,  # Cover full height (percentage)
                    'outline': True,  # Just show border, don't fill
                    'color': "red",  # Red border
                    'border_width': 5,  # Thicker border
                    'title': f"Source [{idx}]",  # Add citation number as label
                    'label': f"[{idx}]"  # Alternative label property
                }
                annotations.append(page_annotation)
    
    return annotations
```

### 2. Update Annotation Logic in `app_modular.py`

Add the annotation creation code to both PDF viewer placeholder locations:

Location 1 (around line 626-628):
```python
# Create annotations if we have a response with sources
annotations = []
if 'response' in st.session_state and st.session_state.response and 'sources' in st.session_state.response:
    # Import the function
    from src.source import create_annotations_from_sources
    # Create annotations based on the answer and sources
    annotations = create_annotations_from_sources(
        st.session_state.response['answer'],
        st.session_state.response['sources']
    )
```

Location 2 (around line 648-651):
```python
# Create annotations if we have a response with sources
annotations = []
if 'response' in st.session_state and st.session_state.response and 'sources' in st.session_state.response:
    # Import the function
    from src.source import create_annotations_from_sources
    # Create annotations based on the answer and sources
    annotations = create_annotations_from_sources(
        st.session_state.response['answer'],
        st.session_state.response['sources']
    )
```

### 3. Update PDF Viewer Configuration

Ensure the PDF viewer is configured to properly display the annotations with labels:

```python
# Display the PDF with the viewer
pdf_viewer(
    input=pdf_binary,
    annotations=annotations,
    annotation_outline_size=5,  # Make outlines more visible
    height=800,
    show_annotation_labels=True  # Enable displaying citation labels
)
```

### 4. Additional Considerations for Labeling

Based on the [streamlit-pdf-viewer documentation](https://github.com/lfoppiano/streamlit-pdf-viewer), we need to ensure the annotation properties for labeling are correctly implemented:

1. Primary approach: Use the `title` property for the citation label:
   ```python
   'title': f"Source [{idx}]"
   ```

2. Fallback approach if `title` isn't supported: Try the `content` property:
   ```python
   'content': f"Source [{idx}]"
   ```

3. Alternative placement: If label positioning is an issue, consider placing the label at a specific location on the page:
   ```python
   # Add a separate text annotation for the label
   annotations.append({
       'page': int(page_num),
       'x': 5,  # Position near top-left
       'y': 5,
       'content': f"Source [{idx}]",
       'color': "red"
   })
   ```

The best approach will be determined during testing, and the implementation can be adjusted accordingly.

## Testing Strategy
1. Upload a PDF document
2. Ask a question that requires information from specific pages
3. Verify that pages containing cited source information are highlighted with red borders
4. Confirm that each annotation displays the correct citation number label
5. Test with multiple citations from different pages
6. Test with multiple citations from the same page to ensure labels are properly displayed
7. Verify that the borders and labels are clearly visible and properly positioned

## Implementation Flow

```mermaid
flowchart TD
    A[User gets answer with sources] --> B[Extract source citations]
    B --> C[Identify source pages]
    C --> D[Create page-level annotations with red borders]
    D --> E[Add citation number labels to annotations]
    E --> F[Display PDF with labeled annotations]