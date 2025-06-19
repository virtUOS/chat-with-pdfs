"""
Internationalization (i18n) utilities for the Chat with Docs application.
Provides language switching functionality and text translations.
"""

import streamlit as st
from typing import Dict, Any
from ..utils.logger import Logger


class I18n:
    """Internationalization utility class for managing translations."""
    
    # Supported languages
    SUPPORTED_LANGUAGES = {
        'en': 'English',
        'de': 'Deutsch'
    }
    
    # Translation dictionary
    TRANSLATIONS = {
        'en': {
            # UI Layout - Sidebar
            'document_upload': 'Document Upload',
            'upload_pdf_documents': 'Upload PDF documents',
            'your_documents': 'Your Documents',
            'documents_available': 'document{s} available',
            'clear_all_files': '🗑️ Clear All Files',
            'delete_all_documents': 'Delete all documents',
            'remove_document': 'Remove {filename}',
            'switch_to_document': 'Switch to {filename}',
            'settings': 'Settings',
            'select_model': 'Select Model',
            'language': 'Language',
            
            # UI Layout - Main Content
            'upload_pdf_to_start': '👈 Please upload a PDF document to start chatting',
            'select_pdf_to_start': '👈 Select a PDF document to start chatting',
            'chatting_with': "You're now chatting with: {filename} ({position}/{total})",
            'pdf_data_not_available': 'PDF data not available. Please try re-uploading the document.',
            'clear_chat': '🗑️ Clear Chat',
            'clear_chat_help': 'Clear chat history for this document',
            'show_sources': '📂 Show Sources',
            'view_images': '🖼️ View Images',
            'type_question_here': 'Type your question here...',
            'query_suggestions': 'Query suggestions:',
            'citation_mapping_not_available': '⚠️ Citation mapping not available. Source information may be incomplete.',
            
            # Tabs
            'chat': 'Chat',
            'document_info': 'Document Info',
            'images': 'Images',
            
            # Document Info
            'document_information': 'Document Information',
            'title': 'Title',
            'author': 'Author',
            'keywords': 'Keywords',
            'summary': 'Summary',
            'page_count': 'Page count',
            'table_of_contents': 'Table of Contents',
            'document_info_not_available': 'Document information not available',
            'document_id_not_found': 'Document ID not found',
            'document_data_not_found': 'Document data not found',
            'could_not_retrieve_metadata': 'Could not retrieve document metadata: {error}',
            
            # Images
            'images_from': 'Images from {filename}',
            'found_images': 'Found {count} images',
            'no_images_found': 'No images found in this document',
            'document_images_not_available': 'Document images not available',
            'image_from_page': 'Image from page {page}',
            'image_from_page_with_caption': 'Image from page {page}: {caption}',
            'image_count': 'Image {current} of {total}',
            'page': 'Page {page}',
            'error_displaying_image': 'Error displaying image: {filename}',
            'image_file_not_found': 'Image file not found: {filename}',
            
            # OCR Warnings
            'document_analysis': '📄 Document Analysis',
            'pages': 'Pages',
            'avg_text_per_page': 'Avg Text/Page',
            'avg_words_per_page': 'Avg Words/Page',
            'scanned_ratio': 'Scanned Ratio',
            'chars': 'chars',
            'ocr_limitation': '⚠️ **OCR Limitation**: This document appears to be scanned or image-based. Text extraction may be incomplete.',
            'good_text_content': '✅ **Good Text Content**: Document has sufficient extractable text.',
            'analysis': 'Analysis: {details}',
            'no_details_available': 'No details available',
            
            # OCR Warning Messages
            'potential_ocr_limitation': '⚠️ **Potential OCR Limitation Detected**',
            'pdf_appears_scanned': 'This PDF appears to be scanned or image-based ({minimal_pages}/{total_pages} pages with minimal text, avg {avg_text} characters per page).',
            'cannot_read_images': '**This application cannot read text from images.** If your PDF contains:',
            'scanned_documents': '• Scanned documents',
            'images_with_text': '• Images with text',
            'screenshots': '• Screenshots',
            'handwritten_content': '• Handwritten content',
            'missing_content_warning': 'You may be missing important content in your queries. Consider using an OCR tool to convert your PDF to searchable text first.',
            'document_processing_complete': '📄 **Document Processing Complete**',
            'pages_processed': '• **Pages processed:** {pages}',
            'average_text_per_page': '• **Average text per page:** {avg_text} characters',
            'average_words_per_page': '• **Average words per page:** {avg_words} words',
            'sufficient_text_content': 'The document appears to have sufficient text content for effective querying.',
            
            # Source Display
            'source_citation': 'Source [{citation}] (Page {page}):',
            
            # Processing Messages
            'uploading_processing_file': 'Uploading and processing file {filename}...',
            
            # Error Messages
            'error_occurred': 'An error occurred',
            'try_again': 'Please try again',
            
            # Analysis Reasons
            'most_pages_minimal_text': 'Most pages contain very little extractable text',
            'low_average_text': 'Very low average text content per page',
            'high_ratio_minimal_text': 'High ratio of pages with minimal text content',
            'sufficient_text_detected': 'Sufficient text content detected',
        },
        'de': {
            # UI Layout - Sidebar
            'document_upload': 'Dokument hochladen',
            'upload_pdf_documents': 'PDF-Dokumente hochladen',
            'your_documents': 'Ihre Dokumente',
            'documents_available': 'Dokument{s} verfügbar',
            'clear_all_files': '🗑️ Alle Dateien löschen',
            'delete_all_documents': 'Alle Dokumente löschen',
            'remove_document': '{filename} entfernen',
            'switch_to_document': 'Zu {filename} wechseln',
            'settings': 'Einstellungen',
            'select_model': 'Modell auswählen',
            'language': 'Sprache',
            
            # UI Layout - Main Content
            'upload_pdf_to_start': '👈 Bitte laden Sie ein PDF-Dokument hoch, um zu beginnen',
            'select_pdf_to_start': '👈 Wählen Sie ein PDF-Dokument aus, um zu beginnen',
            'chatting_with': "Sie chatten jetzt mit: {filename} ({position}/{total})",
            'pdf_data_not_available': 'PDF-Daten nicht verfügbar. Bitte versuchen Sie, das Dokument erneut hochzuladen.',
            'clear_chat': '🗑️ Chat löschen',
            'clear_chat_help': 'Chat-Verlauf für dieses Dokument löschen',
            'show_sources': '📂 Quellen anzeigen',
            'view_images': '🖼️ Bilder anzeigen',
            'type_question_here': 'Geben Sie hier Ihre Frage ein...',
            'query_suggestions': 'Fragevorschläge:',
            'citation_mapping_not_available': '⚠️ Zitat-Zuordnung nicht verfügbar. Quelleninformationen könnten unvollständig sein.',
            
            # Tabs
            'chat': 'Chat',
            'document_info': 'Dokument-Info',
            'images': 'Bilder',
            
            # Document Info
            'document_information': 'Dokument-Informationen',
            'title': 'Titel',
            'author': 'Autor',
            'keywords': 'Schlüsselwörter',
            'summary': 'Zusammenfassung',
            'page_count': 'Seitenzahl',
            'table_of_contents': 'Inhaltsverzeichnis',
            'document_info_not_available': 'Dokument-Informationen nicht verfügbar',
            'document_id_not_found': 'Dokument-ID nicht gefunden',
            'document_data_not_found': 'Dokumentdaten nicht gefunden',
            'could_not_retrieve_metadata': 'Dokument-Metadaten konnten nicht abgerufen werden: {error}',
            
            # Images
            'images_from': 'Bilder aus {filename}',
            'found_images': '{count} Bilder gefunden',
            'no_images_found': 'Keine Bilder in diesem Dokument gefunden',
            'document_images_not_available': 'Dokument-Bilder nicht verfügbar',
            'image_from_page': 'Bild von Seite {page}',
            'image_from_page_with_caption': 'Bild von Seite {page}: {caption}',
            'image_count': 'Bild {current} von {total}',
            'page': 'Seite {page}',
            'error_displaying_image': 'Fehler beim Anzeigen des Bildes: {filename}',
            'image_file_not_found': 'Bilddatei nicht gefunden: {filename}',
            
            # OCR Warnings
            'document_analysis': '📄 Dokument-Analyse',
            'pages': 'Seiten',
            'avg_text_per_page': 'Ø Text/Seite',
            'avg_words_per_page': 'Ø Wörter/Seite',
            'scanned_ratio': 'Scan-Verhältnis',
            'chars': 'Zeichen',
            'ocr_limitation': '⚠️ **OCR-Einschränkung**: Dieses Dokument scheint gescannt oder bildbasiert zu sein. Die Textextraktion könnte unvollständig sein.',
            'good_text_content': '✅ **Guter Textinhalt**: Das Dokument hat ausreichend extrahierbaren Text.',
            'analysis': 'Analyse: {details}',
            'no_details_available': 'Keine Details verfügbar',
            
            # OCR Warning Messages
            'potential_ocr_limitation': '⚠️ **Potenzielle OCR-Einschränkung erkannt**',
            'pdf_appears_scanned': 'Diese PDF scheint gescannt oder bildbasiert zu sein ({minimal_pages}/{total_pages} Seiten mit minimalem Text, Ø {avg_text} Zeichen pro Seite).',
            'cannot_read_images': '**Diese Anwendung kann keinen Text aus Bildern lesen.** Wenn Ihre PDF enthält:',
            'scanned_documents': '• Gescannte Dokumente',
            'images_with_text': '• Bilder mit Text',
            'screenshots': '• Screenshots',
            'handwritten_content': '• Handgeschriebene Inhalte',
            'missing_content_warning': 'Möglicherweise fehlen wichtige Inhalte in Ihren Anfragen. Erwägen Sie die Verwendung eines OCR-Tools, um Ihre PDF zuerst in durchsuchbaren Text zu konvertieren.',
            'document_processing_complete': '📄 **Dokumentverarbeitung abgeschlossen**',
            'pages_processed': '• **Verarbeitete Seiten:** {pages}',
            'average_text_per_page': '• **Durchschnittlicher Text pro Seite:** {avg_text} Zeichen',
            'average_words_per_page': '• **Durchschnittliche Wörter pro Seite:** {avg_words} Wörter',
            'sufficient_text_content': 'Das Dokument scheint ausreichend Textinhalt für effektive Abfragen zu haben.',
            
            # Source Display
            'source_citation': 'Quelle [{citation}] (Seite {page}):',
            
            # Processing Messages
            'uploading_processing_file': 'Datei {filename} wird hochgeladen und verarbeitet...',
            
            # Error Messages
            'error_occurred': 'Ein Fehler ist aufgetreten',
            'try_again': 'Bitte versuchen Sie es erneut',
            
            # Analysis Reasons
            'most_pages_minimal_text': 'Die meisten Seiten enthalten sehr wenig extrahierbaren Text',
            'low_average_text': 'Sehr geringer durchschnittlicher Textinhalt pro Seite',
            'high_ratio_minimal_text': 'Hoher Anteil von Seiten mit minimalem Textinhalt',
            'sufficient_text_detected': 'Ausreichender Textinhalt erkannt',
        }
    }
    
    @staticmethod
    def get_current_language() -> str:
        """Get the current language from session state."""
        if 'language' not in st.session_state:
            st.session_state.language = 'de'  # Default to German
        return st.session_state.language
    
    @staticmethod
    def set_language(language: str) -> None:
        """Set the current language in session state."""
        if language in I18n.SUPPORTED_LANGUAGES:
            st.session_state.language = language
            Logger.info(f"Language changed to: {language}")
        else:
            Logger.warning(f"Unsupported language: {language}")
    
    @staticmethod
    def t(key: str, **kwargs) -> str:
        """
        Translate a key to the current language.
        
        Args:
            key: Translation key
            **kwargs: Variables to substitute in the translation
            
        Returns:
            Translated string with variables substituted
        """
        current_lang = I18n.get_current_language()
        
        # Get translation from the current language, fallback to English
        translation = I18n.TRANSLATIONS.get(current_lang, {}).get(key)
        if translation is None:
            translation = I18n.TRANSLATIONS.get('en', {}).get(key, key)
            if current_lang != 'en':
                Logger.warning(f"Translation missing for key '{key}' in language '{current_lang}', using English fallback")
        
        # Handle pluralization for documents_available
        if key == 'documents_available' and 'count' in kwargs:
            count = kwargs.get('count', 0)
            if current_lang == 'de':
                # German pluralization
                if count == 1:
                    translation = translation.replace('{s}', '')
                else:
                    translation = translation.replace('{s}', 'e')
            else:
                # English pluralization
                if count == 1:
                    translation = translation.replace('{s}', '')
                else:
                    translation = translation.replace('{s}', 's')
        
        # Substitute variables
        try:
            return translation.format(**kwargs)
        except KeyError as e:
            Logger.warning(f"Missing variable {e} for translation key '{key}'")
            return translation
        except Exception as e:
            Logger.error(f"Error formatting translation for key '{key}': {e}")
            return translation
    
    @staticmethod
    def get_language_options() -> Dict[str, str]:
        """Get available language options for UI display."""
        return I18n.SUPPORTED_LANGUAGES
    
    @staticmethod
    def render_language_selector() -> None:
        """Render language selector in the sidebar."""
        current_lang = I18n.get_current_language()
        language_options = I18n.get_language_options()
        
        # Create display names with current language
        display_names = list(language_options.values())
        language_codes = list(language_options.keys())
        
        # Find current index
        try:
            current_index = language_codes.index(current_lang)
        except ValueError:
            current_index = 0
        
        selected_display = st.selectbox(
            I18n.t('language'),
            display_names,
            index=current_index,
            key='language_selector'
        )
        
        # Update language if changed
        if selected_display:
            selected_code = language_codes[display_names.index(selected_display)]
            if selected_code != current_lang:
                I18n.set_language(selected_code)
                # Translate existing document content if needed
                I18n._translate_all_documents(selected_code)
                st.rerun()
    
    @staticmethod
    def _translate_all_documents(target_language: str) -> None:
        """
        Translate all loaded documents' summaries and query suggestions to the target language.
        
        Args:
            target_language: Target language code
        """
        try:
            # Import here to avoid circular imports
            from ..core.document_manager import DocumentManager
            from ..core.state_manager import StateManager
            
            # Get all loaded documents
            if 'pdf_data' in st.session_state:
                for filename, pdf_info in st.session_state.pdf_data.items():
                    if isinstance(pdf_info, dict) and 'doc_id' in pdf_info:
                        pdf_id = pdf_info['doc_id']
                        Logger.info(f"Translating content for document {filename} (ID: {pdf_id})")
                        DocumentManager.translate_document_content_if_needed(pdf_id, target_language)
                        
        except Exception as e:
            Logger.error(f"Error translating documents to {target_language}: {e}")