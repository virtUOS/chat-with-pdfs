"""
PDF analysis utilities for detecting scanned documents and OCR limitations.
"""

import re
from typing import Tuple
from ..utils.logger import Logger
from .i18n import I18n


class PDFAnalyzer:
    """Utility class for analyzing PDF content and detecting potential OCR issues."""
    
    # Thresholds for detecting scanned PDFs
    MIN_TEXT_LENGTH_PER_PAGE = 50  # Minimum characters per page to consider it text-based
    MIN_WORD_COUNT_PER_PAGE = 10   # Minimum words per page
    MAX_SCANNED_RATIO = 0.3        # If more than 70% of pages are "empty", likely scanned
    
    @staticmethod
    def analyze_extracted_content(docs) -> Tuple[bool, dict]:
        """
        Analyze extracted PDF content to detect if it's likely a scanned document.
        
        Args:
            docs: Document content from pymupdf4llm extraction (can be list or string)
            
        Returns:
            Tuple of (is_likely_scanned, analysis_details)
        """
        if not docs:
            return True, {"reason": "No content extracted", "pages_analyzed": 0}
        
        # Handle case where docs is a single string (entire document)
        if isinstance(docs, str):
            docs = [{'text': docs}]  # Convert to list format
        
        total_pages = len(docs)
        pages_with_minimal_text = 0
        total_text_length = 0
        total_word_count = 0
        
        analysis_details = {
            "total_pages": total_pages,
            "pages_with_minimal_text": 0,
            "average_text_per_page": 0,
            "average_words_per_page": 0,
            "likely_scanned_ratio": 0,
            "reason": ""
        }
        
        for doc in docs:
            text = doc.get('text', '') if isinstance(doc, dict) else str(doc)
            
            # Clean text for analysis (remove excessive whitespace, markdown syntax)
            clean_text = re.sub(r'\s+', ' ', text.strip())
            clean_text = re.sub(r'[#*\-_`\[\]()!]', '', clean_text)  # Remove markdown
            
            text_length = len(clean_text)
            word_count = len(clean_text.split()) if clean_text else 0
            
            total_text_length += text_length
            total_word_count += word_count
            
            # Check if this page has minimal text content
            if text_length < PDFAnalyzer.MIN_TEXT_LENGTH_PER_PAGE or word_count < PDFAnalyzer.MIN_WORD_COUNT_PER_PAGE:
                pages_with_minimal_text += 1
                Logger.debug(f"Page with minimal text: {text_length} chars, {word_count} words")
        
        # Calculate ratios and averages
        scanned_ratio = pages_with_minimal_text / total_pages if total_pages > 0 else 1
        avg_text_per_page = total_text_length / total_pages if total_pages > 0 else 0
        avg_words_per_page = total_word_count / total_pages if total_pages > 0 else 0
        
        analysis_details.update({
            "pages_with_minimal_text": pages_with_minimal_text,
            "average_text_per_page": round(avg_text_per_page, 1),
            "average_words_per_page": round(avg_words_per_page, 1),
            "likely_scanned_ratio": round(scanned_ratio, 2)
        })
        
        # Determine if likely scanned
        is_likely_scanned = scanned_ratio > PDFAnalyzer.MAX_SCANNED_RATIO
        
        if is_likely_scanned:
            if scanned_ratio >= 0.8:
                analysis_details["reason"] = I18n.t("most_pages_minimal_text")
            elif avg_text_per_page < 30:
                analysis_details["reason"] = I18n.t("low_average_text")
            else:
                analysis_details["reason"] = I18n.t("high_ratio_minimal_text")
        else:
            analysis_details["reason"] = I18n.t("sufficient_text_detected")
        
        Logger.info(f"PDF Analysis: {analysis_details}")
        
        return is_likely_scanned, analysis_details
    
    @staticmethod
    def get_ocr_warning_message(analysis_details: dict) -> str:
        """
        Generate an appropriate warning message for potentially scanned PDFs.
        
        Args:
            analysis_details: Analysis results from analyze_extracted_content
            
        Returns:
            Formatted warning message
        """
        pages = analysis_details.get("total_pages", 0)
        minimal_pages = analysis_details.get("pages_with_minimal_text", 0)
        avg_text = analysis_details.get("average_text_per_page", 0)
        
        warning = I18n.t('potential_ocr_limitation') + "\n\n"
        warning += I18n.t('pdf_appears_scanned', minimal_pages=minimal_pages, total_pages=pages, avg_text=avg_text) + "\n\n"
        warning += I18n.t('cannot_read_images') + "\n"
        warning += I18n.t('scanned_documents') + "\n"
        warning += I18n.t('images_with_text') + "\n"
        warning += I18n.t('screenshots') + "\n"
        warning += I18n.t('handwritten_content') + "\n\n"
        warning += I18n.t('missing_content_warning')
        
        return warning
    
    @staticmethod
    def get_processing_info_message(analysis_details: dict) -> str:
        """
        Generate an informational message about the processing results.
        
        Args:
            analysis_details: Analysis results from analyze_extracted_content
            
        Returns:
            Formatted info message
        """
        pages = analysis_details.get("total_pages", 0)
        avg_text = analysis_details.get("average_text_per_page", 0)
        avg_words = analysis_details.get("average_words_per_page", 0)
        
        info = I18n.t('document_processing_complete') + "\n\n"
        info += I18n.t('pages_processed', pages=pages) + "\n"
        info += I18n.t('average_text_per_page', avg_text=avg_text) + "\n"
        info += I18n.t('average_words_per_page', avg_words=avg_words) + "\n\n"
        info += I18n.t('sufficient_text_content')
        
        return info