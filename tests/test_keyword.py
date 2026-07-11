from src.lurker import Keyword


class TestLiteralMatch:
    def test_exact_match(self):
        k = Keyword(["hey john"])
        assert k.is_in("hey john") is True

    def test_case_insensitive(self):
        k = Keyword(["hey john"])
        assert k.is_in("Hey John") is True
        assert k.is_in("HEY JOHN") is True

    def test_substring_match(self):
        k = Keyword(["hey john"])
        assert k.is_in("hey john wake up") is True
        assert k.is_in("say hey john now") is True

    def test_no_match(self):
        k = Keyword(["hey john"])
        assert k.is_in("goodbye jane") is False

    def test_empty_text(self):
        k = Keyword(["hey john"])
        assert k.is_in("") is False

    def test_special_chars_escaped(self):
        k = Keyword(["hey.john"])
        assert k.is_in("hey.john") is True
        assert k.is_in("heyXjohn") is False


class TestRegexMatch:
    def test_simple_regex(self):
        k = Keyword(["/hey\\s+john/"])
        assert k.is_in("hey  john") is True
        assert k.is_in("hey john") is True

    def test_regex_no_match(self):
        k = Keyword(["/hey\\s+john/"])
        assert k.is_in("heyjane") is False

    def test_regex_case_insensitive(self):
        k = Keyword(["/hey\\s+john/"])
        assert k.is_in("HEY JOHN") is True

    def test_regex_with_anchors(self):
        k = Keyword(["/^hello/"])
        assert k.is_in("hello world") is True
        assert k.is_in("say hello") is False

    def test_regex_optional_char(self):
        k = Keyword(["/hey\\s+joh?n/"])
        assert k.is_in("hey john") is True
        assert k.is_in("hey jon") is True
        assert k.is_in("hey jo") is False


class TestMultipleSynonyms:
    def test_first_synonym_matches(self):
        k = Keyword(["hey john", "hello john"])
        assert k.is_in("hey john wake up") is True

    def test_second_synonym_matches(self):
        k = Keyword(["hey john", "hello john"])
        assert k.is_in("hello john wake up") is True

    def test_mixed_literal_and_regex(self):
        k = Keyword(["hey john", "/hello\\s+john/"])
        assert k.is_in("hey john") is True
        assert k.is_in("hello  john") is True

    def test_no_synonym_matches(self):
        k = Keyword(["hey john", "hello john"])
        assert k.is_in("goodbye jane") is False


class TestEdgeCases:
    def test_empty_synonyms_list(self):
        k = Keyword([])
        assert k.is_in("anything") is False

    def test_empty_string_synonym_skipped(self):
        k = Keyword(["", "hey john"])
        assert k.is_in("hey john") is True
        assert k.is_in("") is False

    def test_empty_regex_skipped(self):
        k = Keyword(["//", "hey john"])
        assert k.is_in("hey john") is True

    def test_single_slash_not_regex(self):
        k = Keyword(["/"])
        assert k.is_in("/") is True

    def test_repr(self):
        k = Keyword(["hey john", "/hello\\s+john/"])
        assert repr(k) == "Keyword(['hey john', '/hello\\\\s+john/'])"
