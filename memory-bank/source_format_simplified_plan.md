# Source Format Simplified Plan

## Issue
The source text formatting in the PDF viewer is unnecessarily complex, with too much formatting making it difficult to read. As seen in the screenshot, the current format includes:
- Heading levels for source and page numbers 
- Complex regex formatting for section headers
- Unnecessary formatting that impacts readability

## Requirements
- Keep only the source title and page number in bold
- Remove all other formatting from the source text
- Make sources clean and readable

## Implementation Plan

### 1. Modify the `format_source_for_display` function in `src/source.py`

The function currently uses:
- Regex to detect and format section headings (line 196)
- Markdown heading levels (`##` and `###`) for source ID and page number (line 200)

**Current implementation (lines 193-201):**
```python
# Create a cleaner, more readable format
# Make document section headings like "2 Related Work" less prominent than source/page info
# by using a smaller heading style or just bolding them
formatted_text = re.sub(r'^(\d+[\.\s]+[\w\s]+)$', r'**\1**', text, flags=re.MULTILINE)

# Use larger, formatted headings for Source ID and Page number to make them stand out
# while maintaining a clear visual hierarchy
markdown = f"## {source_id}\n### Page {page_num}\n\n{formatted_text}"
source_text = f"{source_id} (Page {page_num}):\n{text}"
```

**Proposed implementation:**
```python
# Simplify formatting - only bold the source ID and page number
markdown = f"**{source_id} (Page {page_num})**\n\n{text}"
source_text = f"{source_id} (Page {page_num}):\n{text}"
```

### 2. Changes Required

1. Remove the regex formatting line:
   ```python
   formatted_text = re.sub(r'^(\d+[\.\s]+[\w\s]+)$', r'**\1**', text, flags=re.MULTILINE)
   ```

2. Replace the heading-based formatting with simple bold formatting:
   ```python
   # From:
   markdown = f"## {source_id}\n### Page {page_num}\n\n{formatted_text}"
   
   # To:
   markdown = f"**{source_id} (Page {page_num})**\n\n{text}"
   ```

3. Keep the `source_text` variable unchanged as it already has a simple format.

### 3. Testing

After implementation, test by:
1. Uploading a PDF document
2. Chatting with the document to get source citations
3. Verifying that:
   - Only the source ID and page number appear in bold
   - The source text is completely unformatted
   - The layout is clean and readable

## Next Steps

1. Switch to Code mode to implement these changes
2. Test the changes with various documents
3. Document any issues that arise during testing