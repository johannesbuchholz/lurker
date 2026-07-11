import re
from typing import List


class Keyword:
    def __init__(self, synonyms: List[str]):
        self._synonyms = synonyms
        self._literals: List[str] = []
        self._patterns: List[re.Pattern] = []
        for synonym in synonyms:
            if not synonym:
                continue
            if synonym.startswith("/") and synonym.endswith("/") and len(synonym) > 1:
                pattern = synonym[1:-1]
                if pattern:
                    self._patterns.append(re.compile(pattern, re.IGNORECASE))
            else:
                self._literals.append(synonym.lower())

    def is_in(self, text: str) -> int | None:
        """Returns the character index where the keyword ends in text, or None if not found."""
        text_lower = text.lower()
        best_end = None

        for literal in self._literals:
            idx = text_lower.find(literal)
            if idx != -1:
                end = idx + len(literal)
                if best_end is None or end < best_end:
                    best_end = end

        if best_end is not None:
            return best_end

        for pattern in self._patterns:
            match = pattern.search(text)
            if match is not None:
                return match.end()

        return None

    def __repr__(self) -> str:
        return f"Keyword({self._synonyms!r})"
