"""
Internationalization (i18n) utilities for the Chat with Docs application.
Provides language switching functionality and text translations.
"""

import streamlit as st
from typing import Dict
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
            # UI Layout - Sidebar (RAGFlow version)
            'chat_assistant': 'Chat Assistant',
            'select_chat_assistant': 'Select Chat Assistant',
            'chat_assistant_help': 'Choose from your configured RAGFlow chat assistants',
            'knowledge_base_documents': 'Knowledge Base Documents',
            'documents_available': 'document{s} available',
            'no_documents_in_kb': 'No documents found in this assistant\'s knowledge base.',
            'no_chat_assistants': '⚠️ No chat assistants available. Please create chat assistants in your RAGFlow instance.',
            'error_loading_assistants': '❌ Error loading chat assistants: {error}',
            'check_ragflow_connection': 'Please check your RAGFlow connection and configuration.',
            'settings': 'Settings',
            'language': 'Language',
            
            # UI Layout - Main Content (RAGFlow version)
            'select_assistant_to_start': '👋 Please select a chat assistant from the sidebar to start chatting with documents.',
            'select_document_to_start': '📄 Please select a document from the assistant\'s knowledge base to start chatting.',
            'chatting_with': '💬 Chatting with: {filename}',
            'pdf_loading': '📄 PDF will be loaded when available from RAGFlow',
            'pdf_not_loaded': '📄 PDF not loaded yet. Please wait for the PDF to load in the viewer.',
            'document_id_not_available': 'Document ID not available',
            'failed_download_pdf': 'Failed to download PDF: {status_code}',
            'document_dataset_id_not_available': 'Document ID or Dataset ID not available',
            'error_downloading_pdf': 'Error downloading PDF: {error}',
            'clear_chat': '🗑️ Clear Chat',
            'clear_chat_help': 'Clear chat history for this document',
            'show_sources': '📂 Show Sources',
            'view_images': '🖼️ View Images',
            'type_question_here': 'Type your question here...',
            'query_suggestions': 'Query suggestions:',
            'citation_mapping_not_available': '⚠️ Citation mapping not available. Source information may be incomplete.',
            
            # RAGFlow Document Info
            'no_document_info_available': 'No document information available',
            'generate_summary': '🤖 Generate Summary',
            'generating_summary': 'Generating document summary...',
            'failed_generate_summary': 'Failed to generate summary',
            'no_document_selected': 'No document selected',
            'could_not_process_images': 'Could not process document images: {error}',
            'images_from_document': 'Images from {doc_name}',
            'found_images_count': 'Found {count} images',
            'no_images_in_document': 'No images found in this document',
            'error_extracting_images': 'Error extracting images: {error}',
            'error_displaying_image_num': 'Error displaying image {num}',
            'unknown_document': 'Unknown Document',
            'document_name': 'Document Name',
            'file_size': 'File Size',
            'document_type': 'Document Type',
            'unknown': 'Unknown',
            'dataset_id': 'Dataset ID',
            'text_chunks': 'Text Chunks',
            'chunks': 'chunks',
            'pages_count': 'pages',
            'pages': 'Pages',
            'timestamps': 'Timestamps',
            'created': 'Created',
            'updated': 'Updated',
            'document_summary': 'Document Summary',
            'show_sources': 'Show Sources',
            'similarity': 'similarity',
            'error': 'Error',
            'multiple_text_segments': 'Multiple text segments',
            'segment': 'Segment',
            'processing_document_images': 'Processing document images...',
            'images_on_page': '{count} image(s) on this page',
            'image_number': 'Image {number}',
            'error_displaying_image_number': 'Error displaying image {number}',
            'no_images_found_in_document': 'No images found in this document',
            'could_not_process_document_images': 'Could not process document images: {error}',
            'loading_pdf_from_ragflow': 'Loading PDF from RAGFlow...',
            'available_suggestions': 'Available suggestions',
            
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
            
            
            # Source Display
            'source_citation': 'Source [{citation}] (Page {page}):',
            
            # Processing Messages
            'uploading_processing_file': 'Uploading and processing file {filename}...',
            
            # Error Messages
            'error_occurred': 'An error occurred',
            'try_again': 'Please try again',
            
        },
        'de': {
            # UI Layout - Sidebar (RAGFlow version)
            'chat_assistant': 'Chat-Assistent',
            'select_chat_assistant': 'Chat-Assistent auswählen',
            'chat_assistant_help': 'Wählen Sie aus Ihren konfigurierten RAGFlow Chat-Assistenten',
            'knowledge_base_documents': 'Wissensbasis-Dokumente',
            'documents_available': 'Dokument{s} verfügbar',
            'no_documents_in_kb': 'Keine Dokumente in der Wissensbasis dieses Assistenten gefunden.',
            'no_chat_assistants': '⚠️ Keine Chat-Assistenten verfügbar. Bitte erstellen Sie Chat-Assistenten in Ihrer RAGFlow-Instanz.',
            'error_loading_assistants': '❌ Fehler beim Laden der Chat-Assistenten: {error}',
            'check_ragflow_connection': 'Bitte überprüfen Sie Ihre RAGFlow-Verbindung und -Konfiguration.',
            'settings': 'Einstellungen',
            'language': 'Sprache',
            
            # UI Layout - Main Content (RAGFlow version)
            'select_assistant_to_start': '👋 Bitte wählen Sie einen Chat-Assistenten aus der Seitenleiste, um mit Dokumenten zu chatten.',
            'select_document_to_start': '📄 Bitte wählen Sie ein Dokument aus der Wissensbasis des Assistenten, um zu chatten.',
            'chatting_with': '💬 Chatten mit: {filename}',
            'pdf_loading': '📄 PDF wird geladen, wenn es von RAGFlow verfügbar ist',
            'pdf_not_loaded': '📄 PDF noch nicht geladen. Bitte warten Sie, bis das PDF im Viewer geladen wird.',
            'document_id_not_available': 'Dokument-ID nicht verfügbar',
            'failed_download_pdf': 'PDF-Download fehlgeschlagen: {status_code}',
            'document_dataset_id_not_available': 'Dokument-ID oder Dataset-ID nicht verfügbar',
            'error_downloading_pdf': 'Fehler beim Herunterladen der PDF: {error}',
            'clear_chat': '🗑️ Chat löschen',
            'clear_chat_help': 'Chat-Verlauf für dieses Dokument löschen',
            'show_sources': '📂 Quellen anzeigen',
            'view_images': '🖼️ Bilder anzeigen',
            'type_question_here': 'Geben Sie hier Ihre Frage ein...',
            'query_suggestions': 'Fragevorschläge:',
            'citation_mapping_not_available': '⚠️ Zitat-Zuordnung nicht verfügbar. Quelleninformationen könnten unvollständig sein.',
            
            # RAGFlow Document Info
            'no_document_info_available': 'Keine Dokumentinformationen verfügbar',
            'generate_summary': '🤖 Zusammenfassung generieren',
            'generating_summary': 'Dokumentzusammenfassung wird generiert...',
            'failed_generate_summary': 'Zusammenfassung konnte nicht generiert werden',
            'no_document_selected': 'Kein Dokument ausgewählt',
            'could_not_process_images': 'Dokumentbilder konnten nicht verarbeitet werden: {error}',
            'images_from_document': 'Bilder aus {doc_name}',
            'found_images_count': '{count} Bilder gefunden',
            'no_images_in_document': 'Keine Bilder in diesem Dokument gefunden',
            'error_extracting_images': 'Fehler beim Extrahieren der Bilder: {error}',
            'error_displaying_image_num': 'Fehler beim Anzeigen von Bild {num}',
            'unknown_document': 'Unbekanntes Dokument',
            'document_name': 'Dokumentname',
            'file_size': 'Dateigröße',
            'document_type': 'Dokumenttyp',
            'unknown': 'Unbekannt',
            'dataset_id': 'Dataset-ID',
            'text_chunks': 'Text-Chunks',
            'chunks': 'Chunks',
            'pages_count': 'Seiten',
            'pages': 'Seiten',
            'timestamps': 'Zeitstempel',
            'created': 'Erstellt',
            'updated': 'Aktualisiert',
            'document_summary': 'Dokumentzusammenfassung',
            'show_sources': 'Quellen anzeigen',
            'similarity': 'Ähnlichkeit',
            'error': 'Fehler',
            'multiple_text_segments': 'Mehrere Textsegmente',
            'segment': 'Segment',
            'processing_document_images': 'Dokumentbilder werden verarbeitet...',
            'images_on_page': '{count} Bild(er) auf dieser Seite',
            'image_number': 'Bild {number}',
            'error_displaying_image_number': 'Fehler beim Anzeigen von Bild {number}',
            'no_images_found_in_document': 'Keine Bilder in diesem Dokument gefunden',
            'could_not_process_document_images': 'Dokumentbilder konnten nicht verarbeitet werden: {error}',
            'loading_pdf_from_ragflow': 'PDF wird von RAGFlow geladen...',
            'available_suggestions': 'Verfügbare Vorschläge',
            
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
            
            
            # Source Display
            'source_citation': 'Quelle [{citation}] (Seite {page}):',
            
            # Processing Messages
            'uploading_processing_file': 'Datei {filename} wird hochgeladen und verarbeitet...',
            
            # Error Messages
            'error_occurred': 'Ein Fehler ist aufgetreten',
            'try_again': 'Bitte versuchen Sie es erneut',
            
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
                st.rerun()
    