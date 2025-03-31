# Citation Button Additional Fixes

After implementing the first fix, there are two additional issues:

1. **Page Navigation Not Working**: Citation buttons are visible but clicking them doesn't jump to the correct page in the PDF, instead always going to the first page.

2. **Source Formatting Degraded**: The formatting of sources in the expander now looks worse than before.

## Root Cause Analysis

### Page Navigation Issue

The problem appears to be in our button implementation. We switched from using the `on_click` parameter with a callback function to a direct button click with inline `if st.button(...):` check. This changes how the navigation events propagate.

The original implementation used:
```python
st.button(
    f"[{citation_num}]",
    on_click=historical_citation_clicked,
    kwargs={"citation_num": citation_num, "page_num": page_num},
    help=f"Jump to page {page_num} in PDF"
)
```

While our new implementation uses:
```python
if st.button(
    f"[{citation_num}]",
    key=btn_key,
    help=f"Jump to page {page_num} in PDF"
):
    # Set state and navigate...
```

The problem is that when using inline `if st.button(...)`, the page rerun occurs before the session state changes are fully applied, causing the navigation to fail.

### Source Formatting Issue

The problem is in how we display the source content. The code in lines 1094-1095:

```python
# Extract just the content part (skip the header)
content_parts = markdown.split('\n')[1:]  # Skip the first line (header)
st.markdown('\n'.join(content_parts))
```

This is splitting the markdown and removing the header, but something in our changes might be affecting how this is processed.

## Solution

### Fix Page Navigation

We should revert to using the `on_click` parameter with proper callback functions:

```python
st.button(
    f"[{citation_num}]",
    key=btn_key,
    on_click=citation_clicked,
    kwargs={"citation_num": citation_num, "page_num": page_num},
    help=f"Jump to page {page_num} in PDF"
)
```

And define proper callback functions at the top level (not nested within loops) to handle the navigation.

### Fix Source Formatting

We need to ensure the source formatting is preserved. The `format_source_for_display` function returns properly formatted markdown with code blocks, so we should ensure those are maintained when displaying the content.

## Implementation Steps

1. Modify the citation button rendering code to use `on_click` parameter with callbacks
2. Define appropriate callback functions outside of loops to handle navigation
3. Check the source display code to ensure proper formatting