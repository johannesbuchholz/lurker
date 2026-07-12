import re
from re import Pattern, Match
from typing import Any


class KeyParagraphMapping:

    @staticmethod
    def compile_regexes(keys: list[str]) -> list[Pattern]:
        patterns = []
        for key in keys:
            if key.startswith("/") and key.endswith("/"):
                pattern_string = key[1:-1]
            else:
                pattern_string = ".*" + key + ".*"
            patterns.append(re.compile(pattern_string))
        return patterns

    def __init__(self, keys: list[str], command: str | int | None | dict[str, Any]):
        self.keys = keys
        self.value = command
        self.patterns: List[Pattern] = self.compile_regexes(self.keys)

    def matches(self, snippet: str) -> Match | None:
        for p in self.patterns:
            match = p.match(snippet)
            if match is not None:
                return match
        return None

    def __repr__(self):
        return str(self.keys)

    def __str__(self):
        return f"{self.__class__.__name__}[keys: {self.keys}, command: {self.value}]"
