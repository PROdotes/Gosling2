import re


class CasingService:
    @staticmethod
    def to_title_case(text: str) -> str:
        """
        Converts text to Title Case (Every word capitalized).
        Explicitly requested: NO minor word exceptions (like 'of', 'the').
        """
        if text is None:
            raise ValueError("Input text cannot be None")
        if not text:
            return ""

        def capitalize_word(match):
            word = match.group(0)
            return word[0].upper() + word[1:].lower()

        # Matches any sequence of word characters (including unicode/diacritics if supported by \w)
        # We capitalize every chunk of letters.
        # This handles parentheses correctly because they are not word characters.
        return re.sub(r"[a-zA-Z\u00C0-\u017F]+", capitalize_word, text)

    @staticmethod
    def to_sentence_case(text: str) -> str:
        """
        Converts text to Sentence case.
        Capitalizes only the first letter of the entire string, the rest is lowercase.
        """
        if text is None:
            raise ValueError("Input text cannot be None")
        if not text:
            return ""

        # Find the first letter to capitalize
        match = re.search(r"[a-zA-Z\u00C0-\u017F]", text)
        if not match:
            return text.lower()  # No letters? just lower

        start_idx = match.start()
        return (
            text[:start_idx] + text[start_idx].upper() + text[start_idx + 1 :].lower()
        )
