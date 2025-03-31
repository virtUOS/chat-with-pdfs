# Query Pill Citation Sources Implementation

Based on the analysis in the fix plan, here are the exact code changes needed to fix the issue of extra sources appearing in the expander when using query pills.

## Code Changes

### 1. Modify the Source Display Code for Chat History (Line ~939)

Find this section in `app_modular.py` (around line 939):

```python
if msg.get("sources"):
    # Add a heading for Sources before the expander
    with st.expander("Show Sources"):
        # Display sources with consistent simple formatting
        for i, source_text in enumerate(msg["sources"]):
            st.write(source_text)
            if i < len(msg["sources"]) - 1:
                st.markdown("---")
```

Replace it with this updated code that filters sources based on citation numbers:

```python
if msg.get("sources"):
    # Add a heading for Sources before the expander
    with st.expander("Show Sources"):
        # Get citation numbers for this message
        citation_numbers = msg.get("citations", [])
        
        if citation_numbers:
            # Only display sources that are actually cited in the response
            displayed_sources = set()
            
            for citation_num in sorted(citation_numbers):
                source_index = citation_num - 1  # Convert 1-based citation to 0-based index
                
                if source_index in displayed_sources:
                    continue  # Skip if already displayed this source
                
                if source_index < len(msg["sources"]):
                    source_text = msg["sources"][source_index]
                    st.write(source_text)
                    displayed_sources.add(source_index)
                    
                    # Add separator between sources
                    if len(displayed_sources) < len(citation_numbers):
                        st.markdown("---")
        else:
            # Fallback: If no citations found, show all sources
            for i, source_text in enumerate(msg["sources"]):
                st.write(source_text)
                if i < len(msg["sources"]) - 1:
                    st.markdown("---")
```

### 2. Fix Source Formatting in Response Generation (Lines ~1081-1087)

The source format being stored during response generation should already include the correct source number, but let's ensure it's consistent:

```python
# Update this section around line 1081-1087
source = response_data['sources'][source_index]
                                                                
# Format the source for display
markdown, source_text = format_source_for_display(source, citation_num)

# Store formatted text for history
sources.append(markdown)
```

### 3. Ensure Correct Source Storage For Query Pill Path (Lines ~879-886)

Make sure the query pill code path uses the same formatting approach:

```python
# Around lines 879-886 in the pill handling code path
sources = []
images = []

# Format source information if available
if 'sources' in response_data and response_data['sources']:
    # Extract citation numbers first
    all_citation_numbers = extract_citation_indices(response_data['answer'])
    unique_citation_numbers = sorted(list(set(all_citation_numbers)))
    
    # Only format sources that are actually cited
    for citation_num in unique_citation_numbers:
        source_index = citation_num - 1
        if source_index < len(response_data['sources']):
            source = response_data['sources'][source_index]
            markdown, _ = format_source_for_display(source, citation_num)
            sources.append(markdown)
```

## Testing Steps

After making these changes:

1. **Test with Query Pills**
   - Upload a document to generate query suggestions
   - Click on a query pill
   - Examine the response and check that:
     - Only sources cited in the text appear in the expander
     - Source numbers match citation numbers in the text
     - No extra sources appear

2. **Test with Regular Chat**
   - Ask a question via the chat input
   - Verify the sources in the expander match the citations in the text
   - Ensure no extra sources appear

3. **Edge Cases**
   - Test with responses that have no citations
   - Test with responses citing the same source multiple times
   - Test with responses having non-sequential citations (e.g., only [1] and [3])

## Expected Results

After implementing these changes:
- The source expander should only show sources that correspond to citation numbers in the text
- Source numbering should match citation numbers in the text
- This behavior should be consistent between query pills and regular chat input

## Rollback Plan

If issues arise after implementation:
1. Revert to the original code in each of the modified sections
2. Document any new issues observed after the fix attempt
3. Develop a revised approach based on additional findings

After this fix is implemented, the citation behavior should be more intuitive and consistent for users, regardless of whether they're using query pills or regular chat input.