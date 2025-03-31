# Decision Log

This file records architectural and implementation decisions using a list format.
2025-03-21 13:34:12 - Log of updates made.

## Initial System Architecture Documentation (2025-03-21)

### Decision

* Document the existing architecture of the Chat-with-Docs application
* Create Memory Bank for tracking project progress and decisions

### Rationale 

* Understanding the current system design is essential for future improvements
* Memory Bank provides consistent tracking of project development and decisions
* Documentation helps establish a baseline for future enhancements

### Implementation Details

* Created comprehensive documentation of system components and data flow
* Established Memory Bank with productContext, activeContext, progress, and decision log


## UI Enhancement with Tabbed Interface and Error Fix (2025-03-21 14:43:07)

### Decision

* Implement a tabbed interface for document information display
* Fix error in document metadata retrieval functionality
* Improve robustness of document store interaction

### Rationale

* Tabbed interface improves user experience by organizing related content
* Error in document metadata retrieval was preventing proper display of document information
* Code needed to be more robust to handle different versions of LlamaIndex API

### Implementation Details

* Created three tabs: Chat, Document Info, and Images
* Fixed 'SimpleDocumentStore' object has no attribute '_docstore' error with multiple fallback methods
* Enhanced document metadata retrieval with a multi-step approach to accommodate API variations
* Implemented a 3-column grid layout for image display
* Used helper functions to encapsulate document info and image display logic

* Identified key technical components including LlamaIndex, PyMuPDF4LLM, and OpenAI integration


## Automatic Document Summarization Implementation (2025-03-21 14:58:22)

### Decision

* Implement automatic document summarization using the new SUMMARY_MODEL environment variable
* Generate concise summaries of uploaded documents using the specified LLM
* Display summaries in the Document Info tab

### Rationale

* Document summaries provide users with a quick overview of document content
* Leveraging LLMs for summarization improves user experience without manual effort
* Environment variable configuration allows flexibility in model selection based on cost/performance needs

### Implementation Details

* Added SUMMARY_MODEL to config.py to read from environment variables
* Created document_summaries storage in session state for persistence
* Implemented generate_document_summary function to create concise document summaries


## Document-Specific PDF Annotations

**2025-03-21 15:35:00**

### Decision
Implement document-specific storage for query responses to ensure PDF annotations only appear for the document they were generated for.

### Rationale
Currently, annotations created from query responses are not properly tied to their source documents. When switching between documents, annotations from one document may incorrectly appear in another document. This is because the application uses a single global session state variable to store the current response.

### Implementation Details
1. Create a document-specific response storage dictionary in session state (`st.session_state.document_responses`)
2. Update response storage logic to save responses by document name
3. Modify annotation creation logic to use document-specific responses
4. Update document deletion to clean up document-specific responses

This approach maintains the existing annotation creation functionality while ensuring annotations are correctly scoped to their respective documents.


## Document-Specific PDF Annotations: Streamlit Refresh Issue

**2025-03-21 15:44:00**

### Decision
Implement a page rerun using `st.rerun()` after storing document-specific responses to ensure annotations are immediately visible in the PDF viewer.

### Rationale
Testing revealed that while the document-specific response storage works correctly, Streamlit doesn't automatically refresh the PDF viewer component with the new annotations after a response is generated. The annotations only appear when Streamlit re-renders on the next user interaction (e.g., when typing a new question).

### Implementation Details
Modify the response handling code to force a page rerun after storing the response and displaying it in the chat container. This ensures the PDF viewer is refreshed with the new annotations immediately after a response is generated, providing better user experience.
* Updated process_pdf to trigger summarization during document processing
* Modified display_document_info to show the summary in the Document Info tab

## Citation Button Key Collision Fix

**2025-03-21 16:37:00**

### Decision
Implement a robust unique key generation system for Streamlit UI components, particularly for citation buttons and source view buttons in the chat interface.

### Rationale
Users experienced errors when generating chat responses due to key collisions in Streamlit UI components. The error message "There are multiple elements with the same key" would appear when citation buttons were created. This happened because:

1. Citation button keys were generated using only a timestamp (`int(time.time())`)
2. Multiple responses generated in the same second would have identical timestamps
3. The same citation numbers appearing in different responses caused key collisions
4. Rapid UI refreshes could lead to component duplication with the same keys

These key collisions led to a poor user experience, making the citation navigation feature unreliable.

### Implementation Details
1. Created a `generate_unique_component_key()` utility function in `src/utils.py` that combines:
   - A session-specific random string (generated once per session)
   - An incrementing counter that increases with each key generation
   - The current timestamp with millisecond precision
   - Context information (like message position in chat history)
   - Component type and identifier information

2. Updated citation button implementation to use the new unique key generation
3. Updated source view button implementation to use the same system
4. Added error handling around button generation to prevent app crashes


## Citation Button Fix: Visibility Issue Resolution

**2025-03-21 16:43:00**

### Decision
Revise the citation button key generation approach to create stable, consistent keys that persist across Streamlit reruns while still preventing key collisions.

### Rationale
After implementing the initial solution for the key collision issue, we discovered that citation buttons were disappearing entirely. This occurred because our key generation strategy created completely new unique keys on every rerun, causing Streamlit to treat them as new elements rather than updates to existing ones. A key insight was identified: "a Streamlit element with a new ID replacing another element erases the previous element after a rerun."

### Implementation Details
1. Created a new `generate_stable_component_key()` function that omits the changing elements (timestamp and incrementing counter) from the key generation
2. Modified the key generation to focus on stability across reruns while maintaining uniqueness between different citations
3. Used consistent context identifiers (response index in chat history) instead of volatile timestamps
4. Created a detailed revision plan in `memory-bank/citation_button_fix_revised.md`
5. Added error handling to ensure graceful fallback if any issues occur

This revised approach ensures citation buttons remain visible and functional across Streamlit reruns while still preventing key collisions between different citations.


## 2025-03-21: Citation Button Persistence Solution

### Decision
Implement a new approach to make citation buttons persist across Streamlit reruns by storing citation information in session state and ensuring buttons are recreated consistently on each render.

### Rationale
After fixing the duplicate ID error with citation buttons through deduplication, a new issue emerged where the buttons weren't visible in the UI. Analysis showed this was caused by Streamlit's rerun mechanism, which was recreating the UI elements but not preserving them correctly - especially problematic with the double `st.rerun()` calls in the annotation handler.

### Implementation Details
1. Store citation information in session state for reliability
2. Fix the redundant rerun calls in annotation handler (remove one of the double calls)
3. Create a pattern where UI elements are consistently recreated from session state on each render
4. Add explicit keys to all Streamlit components to prevent collisions

Full details in [citation_button_persistence_solution.md](citation_button_persistence_solution.md)

## 2025-03-31: Remove Citation Button Navigation Functionality

### Decision

Remove the citation button and PDF annotation jumping functionality from the application while keeping the visual annotations in the PDF documents and citation numbers in the text responses.

### Rationale

1. **Persistent Technical Issue**: Despite multiple implementation attempts and fixes, the annotation jumping functionality consistently fails to navigate to the correct page, always returning to the first page of the document.

2. **User Experience Impact**: The unreliable jumping behavior creates a confusing and frustrating user experience.

3. **Maintenance Burden**: The complex state management, synchronization issues, and click handling for this feature have become difficult to maintain and debug.

4. **Cost-Benefit Analysis**: The core value of the application (chatting with documents and seeing citations) remains intact even without the jumping functionality.

### Implementation Details

1. **Components to Remove**:
   - Citation buttons below chat responses
   - "View" buttons in source expanders
   - Annotation click handlers for navigation
   - PDF viewer scroll_to_annotation parameter

2. **Components to Keep**:
   - Citation numbers in text responses ([1], [2], etc.)
   - Visual PDF annotations with borders and labels
   - Source information display with citation numbers

Detailed implementation plan is documented in `memory-bank/citation_button_removal_plan.md`.



## 2025-03-31 15:30:00 - Solution for UI Spacing Issue between Tabs and Content

### Decision
Moved container height calculation code outside the tab context in app_modular.py.

### Rationale
When height calculation code was inside the chat_tab section, it was adding extra padding/spacing above the chat container.

### Implementation Details
The problematic code block was:
```python
# Create a scrollable container for the chat history with dynamic height
screen_height = streamlit_js_eval(js_expressions='screen.height', key='screen_height')
main_container_dimensions = st_dimensions(key="main")
height_column_container = int(screen_height * 0.5) if main_container_dimensions else 400
```

Moving this code outside the chat_tab context but before the chat container creation eliminated the unwanted spacing. This suggests that Streamlit may add additional padding when calculating dimensions inside nested contexts like tabs.


## 2025-03-31 15:32:00 - Query Suggestions Implementation and Citation Sources Fix

### Decision

1. Implement query suggestions as interactive pills above the chat interface
2. Fix citation source display to properly match source numbers with citation references in text
3. Resolve UI spacing issues between tab containers and content

### Rationale

1. **Query Suggestions**: Improve user experience by providing auto-generated, contextually relevant questions that users can click on to quickly interrogate documents
2. **Citation Source Fix**: When using query pills, incorrect sources were being displayed in the expander that didn't match citation numbers in the text responses
3. **UI Spacing**: Excessive space between container tabs and chat content reduced the usable space for chat interactions

### Implementation Details

#### Query Suggestions Pills Implementation

1. Added `generate_query_suggestions()` function in `src/document.py` to create 3 contextually relevant questions per document
2. Modified document processing to generate and store suggestions in session state
3. Implemented Streamlit pills component in the UI with the following functionality:
   - Display suggestions as clickable pills above the chat container
   - When clicked, submit the suggestion as a query and process it like a regular chat input
   - Remove used suggestions from the available options

#### Citation Source Display Fix

1. Modified the source display logic to filter sources based on citation numbers:
   ```python
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
   ```

2. Ensured consistent source storage and citation mapping between regular queries and pill-initiated queries

#### UI Spacing Fix

Moved height calculation code outside the chat_tab context to prevent unwanted padding:
```python
# Moved this code outside the chat_tab context
screen_height = streamlit_js_eval(js_expressions='screen.height', key='screen_height')
main_container_dimensions = st_dimensions(key="main")
height_column_container = int(screen_height * 0.5) if main_container_dimensions else 400
```

These combined changes significantly improve the user experience by providing better query suggestions, correctly displaying citation sources, and making more efficient use of the UI space.


## 2025-03-31 15:56:00 - GitHub Repository Setup

### Decision
Decided to set up version control and push the Chat-with-Docs project to GitHub.

### Rationale
- Enable proper version control for the project
- Facilitate collaboration and code sharing
- Establish a backup of the codebase
- Make it easier to track changes and issues

### Implementation Details
- Created a comprehensive GitHub push plan in `memory-bank/github_push_plan.md`
- Created a README.md with project documentation, features, and setup instructions
- Plan includes creating a .gitignore file to exclude temporary files, environment files, and generated assets
- Will switch to Code mode to execute the Git commands and complete the setup


This approach ensures uniqueness across multiple dimensions, making key collisions practically impossible while maintaining a clean UI and consistent functionality.