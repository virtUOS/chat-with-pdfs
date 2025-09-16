"""
Prompt templates for different languages in the Chat with Docs application.
"""

from .i18n import I18n


class PromptTemplates:
    """Manages prompt templates for different languages."""
    
    
    QUERY_SUGGESTION_PROMPTS = {
        'en': """Based on the document '{doc_name}', please generate exactly 3 specific questions that someone might want to ask about this document. The questions should explore different aspects of the content and be specific to what's actually in the document. Return only the 3 questions, one per line, without numbering or bullets.""",
        
        'de': """Basierend auf dem Dokument '{doc_name}', generieren Sie bitte genau 3 spezifische Fragen, die jemand zu diesem Dokument stellen könnte. Die Fragen sollten verschiedene Aspekte des Inhalts erkunden und spezifisch für das sein, was tatsächlich im Dokument steht. Geben Sie nur die 3 Fragen zurück, eine pro Zeile, ohne Nummerierung oder Aufzählungszeichen."""
    }
    
    SUMMARY_QUERY_PROMPTS = {
        'en': """Please provide a brief summary of the document '{doc_name}' in English. Include the main topics, key points, and purpose of the document in 2-3 sentences.""",
        
        'de': """Bitte erstellen Sie eine kurze Zusammenfassung des Dokuments '{doc_name}' auf Deutsch. Geben Sie die Hauptthemen, wichtige Punkte und den Zweck des Dokuments in 2-3 Sätzen an."""
    }
    
    DOCUMENT_SCOPING_PROMPTS = {
        'en': """Please answer this question specifically about the document '{doc_name}' in English: {question}""",
        
        'de': """Bitte beantworten Sie diese Frage spezifisch über das Dokument '{doc_name}' auf Deutsch. Antworten Sie ausschließlich auf Deutsch: {question}"""
    }
    
    
    @staticmethod
    def get_query_suggestion_prompt(language: str | None = None) -> str:
        """
        Get the query suggestion prompt for the specified language.
        
        Args:
            language: Language code ('en' or 'de'). If None, uses current language.
            
        Returns:
            Query suggestion prompt template
        """
        if language is None:
            language = I18n.get_current_language()
        
        return PromptTemplates.QUERY_SUGGESTION_PROMPTS.get(language, PromptTemplates.QUERY_SUGGESTION_PROMPTS['en'])
    
    @staticmethod
    def get_summary_query_prompt(language: str | None = None) -> str:
        """
        Get the summary query prompt for the specified language.
        
        Args:
            language: Language code ('en' or 'de'). If None, uses current language.
            
        Returns:
            Summary query prompt template
        """
        if language is None:
            language = I18n.get_current_language()
        
        return PromptTemplates.SUMMARY_QUERY_PROMPTS.get(language, PromptTemplates.SUMMARY_QUERY_PROMPTS['en'])
    
    @staticmethod
    def get_document_scoping_prompt(language: str | None = None) -> str:
        """
        Get the document scoping prompt for the specified language.
        
        Args:
            language: Language code ('en' or 'de'). If None, uses current language.
            
        Returns:
            Document scoping prompt template
        """
        if language is None:
            language = I18n.get_current_language()
        
        return PromptTemplates.DOCUMENT_SCOPING_PROMPTS.get(language, PromptTemplates.DOCUMENT_SCOPING_PROMPTS['en'])
    
    TRANSLATION_PROMPTS = {
        'de_to_en': """Please translate the following German text to English. Maintain the same structure, formatting, and meaning. If the text contains a list of questions, keep them as a list format.

German text:
{text}

English translation:""",
        
        'en_to_de': """Please translate the following English text to German. Maintain the same structure, formatting, and meaning. If the text contains a list of questions, keep them as a list format.

English text:
{text}

German translation:"""
    }
    
    @staticmethod
    def get_translation_prompt(from_lang: str, to_lang: str) -> str:
        """
        Get the translation prompt for translating between languages.
        
        Args:
            from_lang: Source language code ('en' or 'de')
            to_lang: Target language code ('en' or 'de')
            
        Returns:
            Translation prompt template
        """
        key = f"{from_lang}_to_{to_lang}"
        return PromptTemplates.TRANSLATION_PROMPTS.get(key, "")