"""
Prompt templates for different languages in the Chat with Docs application.
"""

from .i18n import I18n


class PromptTemplates:
    """Manages prompt templates for different languages."""
    
    CITATION_PROMPTS = {
        'en': """
    CRITICAL INSTRUCTION: Your response MUST include numbered citations in square brackets [1], [2], etc.

    Follow these rules EXACTLY:
    1. Base your answer SOLELY on the provided sources.
    2. EVERY statement of fact MUST have a citation in square brackets [#].
    3. Format citations as [1], [2], [3], etc., corresponding to the source number.
    4. Citations must appear IMMEDIATELY after the information they support.
    5. Your answer MUST have AT LEAST ONE citation, even for simple queries.
    6. If sources don't contain relevant information, explicitly state this and explain why.
    7. DO NOT make up information or use your general knowledge.
    
    Example:
    Source 1: The sky is red in the evening and blue in the morning.
    Source 2: Water is wet when the sky is red.
    Query: When is water wet?
    Answer: According to the sources, water becomes wet when the sky is red [2], which occurs specifically in the evening [1].
    
    --------------
    
    Below are numbered sources of information:
    --------------
    
    {context_str}
    
    --------------
    
    Query: {query_str}
    
    Answer (YOU MUST INCLUDE NUMBERED CITATIONS IN FORMAT [1], [2], ETC.):
    """,
        
        'de': """
    KRITISCHE ANWEISUNG: Ihre Antwort MUSS nummerierte Zitate in eckigen Klammern [1], [2], etc. enthalten.

    Befolgen Sie diese Regeln GENAU:
    1. Stützen Sie Ihre Antwort AUSSCHLIESSLICH auf die bereitgestellten Quellen.
    2. JEDE Tatsachenaussage MUSS ein Zitat in eckigen Klammern [#] haben.
    3. Formatieren Sie Zitate als [1], [2], [3], etc., entsprechend der Quellennummer.
    4. Zitate müssen UNMITTELBAR nach den Informationen erscheinen, die sie stützen.
    5. Ihre Antwort MUSS MINDESTENS EIN Zitat haben, auch bei einfachen Anfragen.
    6. Wenn die Quellen keine relevanten Informationen enthalten, geben Sie dies explizit an und erklären Sie warum.
    7. Erfinden Sie KEINE Informationen und verwenden Sie NICHT Ihr allgemeines Wissen.
    
    Beispiel:
    Quelle 1: Der Himmel ist abends rot und morgens blau.
    Quelle 2: Wasser ist nass, wenn der Himmel rot ist.
    Anfrage: Wann ist Wasser nass?
    Antwort: Laut den Quellen wird Wasser nass, wenn der Himmel rot ist [2], was speziell am Abend auftritt [1].
    
    --------------
    
    Unten sind nummerierte Informationsquellen:
    --------------
    
    {context_str}
    
    --------------
    
    Anfrage: {query_str}
    
    Antwort (SIE MÜSSEN NUMMERIERTE ZITATE IM FORMAT [1], [2], ETC. EINSCHLIESSEN):
    """
    }
    
    REFINE_PROMPTS = {
        'en': """
    You are an expert assistant tasked with refining an existing answer using additional context.
    
    CRITICAL: You MUST preserve and include ALL citations from the original answer.
    CRITICAL: You MUST add citations for any new information from the new context.
    
    Rules:
    1. Keep all existing citations [1], [2], etc. from the original answer
    2. Add new citations for information from the new context
    3. Ensure the refined answer flows naturally while maintaining all citations
    4. Do not remove or modify existing citations
    5. Base refinements ONLY on the provided context
    
    Original Query: {query_str}
    
    Existing Answer: {existing_answer}
    
    New Context: {context_msg}
    
    Refined Answer (preserve ALL existing citations and add new ones as needed):
    """,
        
        'de': """
    Sie sind ein Experten-Assistent, der eine bestehende Antwort mit zusätzlichem Kontext verfeinern soll.
    
    KRITISCH: Sie MÜSSEN alle Zitate aus der ursprünglichen Antwort bewahren und einschließen.
    KRITISCH: Sie MÜSSEN Zitate für neue Informationen aus dem neuen Kontext hinzufügen.
    
    Regeln:
    1. Behalten Sie alle bestehenden Zitate [1], [2], etc. aus der ursprünglichen Antwort
    2. Fügen Sie neue Zitate für Informationen aus dem neuen Kontext hinzu
    3. Stellen Sie sicher, dass die verfeinerte Antwort natürlich fließt und alle Zitate beibehält
    4. Entfernen oder ändern Sie keine bestehenden Zitate
    5. Stützen Sie Verfeinerungen NUR auf den bereitgestellten Kontext
    
    Ursprüngliche Anfrage: {query_str}
    
    Bestehende Antwort: {existing_answer}
    
    Neuer Kontext: {context_msg}
    
    Verfeinerte Antwort (bewahren Sie ALLE bestehenden Zitate und fügen Sie neue nach Bedarf hinzu):
    """
    }
    
    SUMMARY_PROMPTS = {
        'en': """Please provide a concise summary of the following document.
Focus on the main topics, key points, and important information.
Keep the summary informative but brief (2-3 paragraphs maximum).

Document content:
{content}

Summary:""",
        
        'de': """Bitte erstellen Sie eine prägnante Zusammenfassung des folgenden Dokuments.
Konzentrieren Sie sich auf die Hauptthemen, wichtige Punkte und wichtige Informationen.
Halten Sie die Zusammenfassung informativ, aber kurz (maximal 2-3 Absätze).

Dokumentinhalt:
{content}

Zusammenfassung:"""
    }
    
    QUERY_SUGGESTION_PROMPTS = {
        'en': """Please generate 3 interesting and diverse questions that someone might want to ask about the following document.
The questions should:
- Cover different aspects of the document
- Be specific and actionable
- Help users explore the content effectively
- Be formatted as a simple list (one question per line)

Document content:
{content}

Questions:""",
        
        'de': """Bitte generieren Sie 3 interessante und vielfältige Fragen, die jemand zu dem folgenden Dokument stellen könnte.
Die Fragen sollten:
- Verschiedene Aspekte des Dokuments abdecken
- Spezifisch und umsetzbar sein
- Benutzern helfen, den Inhalt effektiv zu erkunden
- Als einfache Liste formatiert sein (eine Frage pro Zeile)

Dokumentinhalt:
{content}

Fragen:"""
    }
    
    @staticmethod
    def get_citation_prompt(language: str | None = None) -> str:
        """
        Get the citation prompt for the specified language.
        
        Args:
            language: Language code ('en' or 'de'). If None, uses current language.
            
        Returns:
            Citation prompt template
        """
        if language is None:
            language = I18n.get_current_language()
        
        return PromptTemplates.CITATION_PROMPTS.get(language, PromptTemplates.CITATION_PROMPTS['en'])
    
    @staticmethod
    def get_refine_prompt(language: str | None = None) -> str:
        """
        Get the refine prompt for the specified language.
        
        Args:
            language: Language code ('en' or 'de'). If None, uses current language.
            
        Returns:
            Refine prompt template
        """
        if language is None:
            language = I18n.get_current_language()
        
        return PromptTemplates.REFINE_PROMPTS.get(language, PromptTemplates.REFINE_PROMPTS['en'])
    
    @staticmethod
    def get_summary_prompt(language: str | None = None) -> str:
        """
        Get the summary prompt for the specified language.
        
        Args:
            language: Language code ('en' or 'de'). If None, uses current language.
            
        Returns:
            Summary prompt template
        """
        if language is None:
            language = I18n.get_current_language()
        
        return PromptTemplates.SUMMARY_PROMPTS.get(language, PromptTemplates.SUMMARY_PROMPTS['en'])
    
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