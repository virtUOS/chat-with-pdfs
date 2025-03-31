# Source Format Fix Summary

## Issue
The source display in the PDF viewer had excessive formatting that made it hard to read.

## Solution
The user implemented a simplified approach by replacing `st.markdown()` with `st.write()` in the app_modular.py file.

## Implementation Details
The key fix was changing the Streamlit display method:
- `st.markdown()` interprets and renders Markdown formatting (which was causing the weird formatting)
- `st.write()` is more flexible and handles the text with less special formatting

This simple change resolved the formatting issues without needing to modify the source formatting function in src/source.py.

## Current Status
The formatting has been fixed by the user and now appears correctly with cleaner, more readable source displays.