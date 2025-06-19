"""
OCR warning components for the Chat with Docs application.
Displays warnings when PDFs might contain scanned content.
"""

import streamlit as st
from ..utils.pdf_analysis import PDFAnalyzer
from ..utils.logger import Logger


def display_ocr_warning(pdf_filename: str) -> None:
    """
    Display OCR warning if the PDF is likely scanned.
    
    Args:
        pdf_filename: The PDF filename to check for OCR issues
    """
    Logger.info(f"display_ocr_warning called for PDF {pdf_filename}")
    
    # Check if we have OCR analysis for this PDF
    if 'ocr_analysis' not in st.session_state:
        Logger.info(f"No ocr_analysis in session state")
        return
    
    Logger.info(f"OCR analysis keys in session state: {list(st.session_state.ocr_analysis.keys())}")
    
    # Find the PDF ID that corresponds to this filename
    pdf_id = None
    if 'pdf_data' in st.session_state and pdf_filename in st.session_state.pdf_data:
        pdf_data = st.session_state.pdf_data[pdf_filename]
        Logger.info(f"PDF data structure for {pdf_filename}: {pdf_data}")
        
        # Try different possible keys for the PDF ID
        pdf_id = pdf_data.get('id') or pdf_data.get('pdf_id') or pdf_data.get('document_id') or pdf_data.get('doc_id')
        Logger.info(f"Found PDF ID {pdf_id} for filename {pdf_filename}")
        
        # If still no ID found, try to find it by matching in OCR analysis keys
        if not pdf_id and 'ocr_analysis' in st.session_state:
            Logger.info(f"No direct ID found, searching OCR analysis keys for match")
            # Sometimes the ID might be stored differently, let's try to find a match
            for ocr_key in st.session_state.ocr_analysis.keys():
                Logger.info(f"Checking OCR key: {ocr_key}")
                # For now, if there's only one OCR analysis entry, use it
                if len(st.session_state.ocr_analysis) == 1:
                    pdf_id = ocr_key
                    Logger.info(f"Using single OCR analysis key as PDF ID: {pdf_id}")
                    break
    
    if not pdf_id or pdf_id not in st.session_state.ocr_analysis:
        Logger.info(f"PDF {pdf_filename} (ID: {pdf_id}) not found in OCR analysis")
        Logger.info(f"Available OCR analysis keys: {list(st.session_state.ocr_analysis.keys()) if 'ocr_analysis' in st.session_state else 'None'}")
        return
    
    analysis = st.session_state.ocr_analysis[pdf_id]
    Logger.info(f"Found OCR analysis for PDF {pdf_filename} (ID: {pdf_id}): {analysis}")
    
    if analysis['is_likely_scanned']:
        # Display warning for scanned PDFs
        warning_message = PDFAnalyzer.get_ocr_warning_message(analysis['analysis_details'])
        Logger.info(f"Displaying OCR warning for PDF {pdf_filename}")
        st.warning(warning_message)
        Logger.info(f"Displayed OCR warning for PDF {pdf_filename}")
    else:
        Logger.info(f"PDF {pdf_filename} is not likely scanned, no warning needed")
        # Optionally display processing info for text-based PDFs
        if st.session_state.get('show_processing_info', False):
            info_message = PDFAnalyzer.get_processing_info_message(analysis['analysis_details'])
            st.info(info_message)


def display_ocr_status_in_sidebar(pdf_filename: str) -> None:
    """
    Display OCR status in the sidebar for the current document.
    
    Args:
        pdf_filename: The PDF filename to check for OCR issues
    """
    # Check if we have OCR analysis for this PDF
    if 'ocr_analysis' not in st.session_state:
        return
    
    # Find the PDF ID that corresponds to this filename
    pdf_id = None
    if 'pdf_data' in st.session_state and pdf_filename in st.session_state.pdf_data:
        pdf_data = st.session_state.pdf_data[pdf_filename]
        
        # Try different possible keys for the PDF ID
        pdf_id = pdf_data.get('id') or pdf_data.get('pdf_id') or pdf_data.get('document_id') or pdf_data.get('doc_id')
        
        # If still no ID found, try to find it by matching in OCR analysis keys
        if not pdf_id and 'ocr_analysis' in st.session_state:
            # For now, if there's only one OCR analysis entry, use it
            if len(st.session_state.ocr_analysis) == 1:
                pdf_id = list(st.session_state.ocr_analysis.keys())[0]
    
    if not pdf_id or pdf_id not in st.session_state.ocr_analysis:
        return
    
    analysis = st.session_state.ocr_analysis[pdf_id]
    details = analysis['analysis_details']
    
    with st.expander("📄 Document Analysis", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Pages", details.get('total_pages', 0))
            st.metric("Avg Text/Page", f"{details.get('average_text_per_page', 0)} chars")
        
        with col2:
            st.metric("Avg Words/Page", details.get('average_words_per_page', 0))
            scanned_ratio = details.get('likely_scanned_ratio', 0)
            st.metric("Scanned Ratio", f"{scanned_ratio:.1%}")
        
        if analysis['is_likely_scanned']:
            st.error("⚠️ **OCR Limitation**: This document appears to be scanned or image-based. Text extraction may be incomplete.")
        else:
            st.success("✅ **Good Text Content**: Document has sufficient extractable text.")
        
        st.caption(f"Analysis: {details.get('reason', 'No details available')}")


def check_and_display_ocr_warning_for_current_file() -> None:
    """
    Check and display OCR warning for the currently selected file.
    This function should be called in the main UI after file selection.
    """
    current_file = st.session_state.get('current_file')
    if current_file:
        display_ocr_warning(current_file)


def add_ocr_analysis_to_session_state(pdf_id: str, docs) -> None:
    """
    Analyze PDF content and add OCR analysis to session state.
    This function can be called from document processing.
    
    Args:
        pdf_id: The PDF identifier
        docs: List of documents extracted from PDF
    """
    Logger.info(f"Starting OCR analysis for PDF {pdf_id}")
    Logger.info(f"Docs type: {type(docs)}, Docs content preview: {str(docs)[:200] if docs else 'None'}")
    
    try:
        # Analyze PDF content for potential OCR issues
        is_likely_scanned, analysis_details = PDFAnalyzer.analyze_extracted_content(docs)
        
        Logger.info(f"OCR analysis complete for PDF {pdf_id}: is_likely_scanned={is_likely_scanned}")
        Logger.info(f"Analysis details: {analysis_details}")
        
        # Store OCR analysis results in session state for UI display
        if 'ocr_analysis' not in st.session_state:
            st.session_state.ocr_analysis = {}
        
        st.session_state.ocr_analysis[pdf_id] = {
            'is_likely_scanned': is_likely_scanned,
            'analysis_details': analysis_details
        }
        
        # Log the analysis results
        if is_likely_scanned:
            Logger.warning(f"PDF {pdf_id} appears to be scanned or image-based: {analysis_details['reason']}")
        else:
            Logger.info(f"PDF {pdf_id} has sufficient text content for processing")
            
    except Exception as e:
        Logger.error(f"Error during OCR analysis for PDF {pdf_id}: {e}")
        import traceback
        Logger.error(f"Traceback: {traceback.format_exc()}")