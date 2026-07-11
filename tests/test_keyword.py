from src.keyword import Keyword


class TestLiteralMatch:
    def test_exact_match(self):
        k = Keyword(["hey john"])
        assert k.is_in("hey john") == 8

    def test_case_insensitive(self):
        k = Keyword(["hey john"])
        assert k.is_in("Hey John") == 8
        assert k.is_in("HEY JOHN") == 8

    def test_substring_match(self):
        k = Keyword(["hey john"])
        assert k.is_in("hey john wake up") == 8
        assert k.is_in("say hey john now") == 12

    def test_no_match(self):
        k = Keyword(["hey john"])
        assert k.is_in("goodbye jane") is None

    def test_empty_text(self):
        k = Keyword(["hey john"])
        assert k.is_in("") is None

    def test_special_chars_escaped(self):
        k = Keyword(["hey.john"])
        assert k.is_in("hey.john") == 8
        assert k.is_in("heyXjohn") is None


class TestRegexMatch:
    def test_simple_regex(self):
        k = Keyword(["/hey\\s+john/"])
        assert k.is_in("hey  john") == 9
        assert k.is_in("hey john") == 8

    def test_regex_no_match(self):
        k = Keyword(["/hey\\s+john/"])
        assert k.is_in("heyjane") is None

    def test_regex_case_insensitive(self):
        k = Keyword(["/hey\\s+john/"])
        assert k.is_in("HEY JOHN") == 8

    def test_regex_with_anchors(self):
        k = Keyword(["/^hello/"])
        assert k.is_in("hello world") == 5
        assert k.is_in("say hello") is None

    def test_regex_optional_char(self):
        k = Keyword(["/hey\\s+joh?n/"])
        assert k.is_in("hey john") == 8
        assert k.is_in("hey jon") == 7
        assert k.is_in("hey jo") is None


class TestMultipleSynonyms:
    def test_first_synonym_matches(self):
        k = Keyword(["hey john", "hello john"])
        assert k.is_in("hey john wake up") == 8

    def test_second_synonym_matches(self):
        k = Keyword(["hey john", "hello john"])
        assert k.is_in("hello john wake up") == 10

    def test_mixed_literal_and_regex(self):
        k = Keyword(["hey john", "/hello\\s+john/"])
        assert k.is_in("hey john") == 8
        assert k.is_in("hello  john") == 11

    def test_no_synonym_matches(self):
        k = Keyword(["hey john", "hello john"])
        assert k.is_in("goodbye jane") is None


class TestEdgeCases:
    def test_empty_synonyms_list(self):
        k = Keyword([])
        assert k.is_in("anything") is None

    def test_empty_string_synonym_skipped(self):
        k = Keyword(["", "hey john"])
        assert k.is_in("hey john") == 8
        assert k.is_in("") is None

    def test_empty_regex_skipped(self):
        k = Keyword(["//", "hey john"])
        assert k.is_in("hey john") == 8

    def test_single_slash_not_regex(self):
        k = Keyword(["/"])
        assert k.is_in("/") == 1

    def test_repr(self):
        k = Keyword(["hey john", "/hello\\s+john/"])
        assert repr(k) == "Keyword(['hey john', '/hello\\\\s+john/'])"
