"""
Source citations component for chat messages.

Handles the display of source citations with scroll-to-annotation functionality
and proper color mapping that matches PDF annotations.
"""

import streamlit as st
from typing import Dict, Any, List, Set

from ...utils.logger import Logger
from ...utils.i18n import I18n
from ...utils.source_formatting import (
    format_source_for_display, 
    get_source_page_numbers_for_display, 
    format_page_numbers_for_display
)
from ..layout_state_manager import LayoutStateManager


def render_source_citations(msg: Dict[str, Any]) -> None:
    """
    Render source citations for a chat message.
    
    Args:
        msg: Chat message containing citations and sources
    """
    citation_numbers = msg.get("citations", [])
    
    # Only display sources for citations present in the answer
    if not citation_numbers:
        return
    
    # Display sources if this is an assistant message with sources
    if msg["role"] == "assistant" and msg.get("sources"):
        with st.expander(I18n.t('show_sources')):
            _render_citation_sources(msg, citation_numbers)


def _render_citation_sources(msg: Dict[str, Any], citation_numbers: List[int]) -> None:
    """
    Render the actual citation sources with scroll functionality.
    
    Args:
        msg: Chat message containing citation mapping and sources
        citation_numbers: List of citation numbers to display
    """
    # Only display sources that are actually cited in the response
    displayed_sources: Set[int] = set()
    
    # Only proceed if we have a citation mapping
    if "citation_mapping" not in msg:
        st.warning(I18n.t('citation_mapping_not_available'))
        return
    
    sorted_citations = sorted(citation_numbers)
    color_options = ["lightcoral", "lightblue", "lightgreen", "lightsalmon", "plum"]
    
    # Use the real citation-to-annotation mapping from annotation creation
    citation_to_annotation_pos = LayoutStateManager.get_citation_to_annotation_mapping()
    
    for idx, citation_num in enumerate(sorted_citations):
        # Use the original citation number from RAGFlow (ID:0 -> 0, ID:1 -> 1, etc.)
        display_num = citation_num
        
        # Debug: Log the mapping
        Logger.info(f"Citation mapping: original_id={citation_num}, display_num={display_num}, annotation_pos={citation_to_annotation_pos.get(citation_num)}")
        
        # Get the original source index from the mapping
        if str(citation_num) in msg["citation_mapping"]:
            original_source_index = msg["citation_mapping"][str(citation_num)]
            
            if original_source_index in displayed_sources:
                continue  # Skip if already displayed this source
            
            if original_source_index < len(msg["sources"]):
                _render_single_source(
                    msg["sources"][original_source_index],
                    citation_num,
                    display_num,
                    original_source_index,
                    color_options,
                    citation_to_annotation_pos,
                    displayed_sources,
                    idx,
                    len(sorted_citations)
                )
        else:
            Logger.warning(f"Citation number {citation_num} not found in mapping")


def _render_single_source(
    source: Any,
    citation_num: int,
    display_num: int,
    original_source_index: int,
    color_options: List[str],
    citation_to_annotation_pos: Dict[int, List[int]],
    displayed_sources: Set[int],
    idx: int,
    total_citations: int
) -> None:
    """
    Render a single source citation with metadata and scroll functionality.
    
    Args:
        source: Source object containing text and metadata
        citation_num: Original citation number
        display_num: Display citation number
        original_source_index: Index in the sources array
        color_options: Available colors for citation display
        citation_to_annotation_pos: Mapping from citations to annotation positions
        displayed_sources: Set of already displayed source indices
        idx: Current citation index
        total_citations: Total number of citations
    """
    try:
        full_text = getattr(source, 'text', '')
        Logger.info(f"Full source text (len={len(full_text)}): {full_text[:500].replace('\n', ' ')}")
    except Exception as e:
        Logger.warning(f"Error logging full source text: {e}")
    
    # Extract all page numbers that this source spans
    try:
        page_numbers = get_source_page_numbers_for_display(source)
        page_display = format_page_numbers_for_display(page_numbers)
    except Exception:
        page_display = 'Error'
    
    # Get document name and similarity for nice display
    if isinstance(source, dict):
        doc_name = source.get('metadata', {}).get('document_name', 'Unknown Document')
        similarity = source.get('metadata', {}).get('similarity', 0.0)
    else:
        doc_name = 'Unknown Document'
        similarity = 0.0
    
    # Get the color that matches the annotation (use citation_num for consistency)
    source_color = color_options[citation_num % len(color_options)]
    
    # Create header with citation info and scroll button
    header_col1, header_col2 = st.columns([4, 1])
    
    with header_col1:
        # Create a colored container for the source
        st.markdown(f"""
        <div style="border-left: 4px solid {source_color}; padding-left: 12px; margin: 8px 0;">
            <strong>{display_num}. {doc_name}</strong> (similarity: {similarity:.3f})
        </div>
        """, unsafe_allow_html=True)
    
    with header_col2:
        # Add button to scroll to this annotation
        annotation_positions = citation_to_annotation_pos.get(citation_num, [])
        annotation_position = annotation_positions[0] if annotation_positions else None
        
        if annotation_position and st.button("📍", key=f"scroll_to_{citation_num}_{original_source_index}",
                                           help=I18n.t('scroll_to_annotation', citation=display_num)):
            # Set the annotation position to scroll to (1-indexed)
            Logger.info(f"Button clicked: citation_num={citation_num}, display_num={display_num}, annotation_position={annotation_position}")
            Logger.info(f"Citation has {len(annotation_positions)} annotations at positions: {annotation_positions}")
            Logger.info(f"Using stored mapping: {citation_to_annotation_pos}")
            LayoutStateManager.set_scroll_to_annotation(annotation_position)
            st.rerun()
    
    if page_display not in ['N/A', 'Error']:
        st.caption(f"📄 {page_display}")
    
    # Always display unified source text
    source_text = format_source_for_display(source)
    st.markdown(f"   {source_text}")
    
    # Add separator between sources, but not after the last one
    if idx < total_citations - 1:
        st.markdown("---")  # Add separator between sources
    
    displayed_sources.add(original_source_index)