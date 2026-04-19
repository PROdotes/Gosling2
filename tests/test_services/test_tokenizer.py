from src.services.tokenizer import tokenize_credits, resolve_names
from src.engine.config import DEFAULT_CREDIT_SEPARATORS


class TestTokenizeCredits:
    def test_single_separator_splits_two_names(self):
        tokens = tokenize_credits("Dave Grohl & Taylor Hawkins", [" & "])
        assert tokens == [
            {"type": "name", "text": "Dave Grohl"},
            {"type": "sep", "text": " & "},
            {"type": "name", "text": "Taylor Hawkins"},
        ], f"Unexpected tokens: {tokens}"

    def test_no_separator_match_returns_single_name_token(self):
        tokens = tokenize_credits("Dave Grohl", [" & "])
        assert tokens == [
            {"type": "name", "text": "Dave Grohl"},
        ], f"Unexpected tokens: {tokens}"

    def test_empty_separators_returns_single_name_token(self):
        tokens = tokenize_credits("Dave Grohl & Taylor Hawkins", [])
        assert tokens == [
            {"type": "name", "text": "Dave Grohl & Taylor Hawkins"},
        ], f"Unexpected tokens: {tokens}"

    def test_empty_text_returns_empty_list(self):
        tokens = tokenize_credits("", [" & "])
        assert tokens == [], f"Expected empty list, got {tokens}"

    def test_multiple_separators(self):
        tokens = tokenize_credits(
            "Dave Grohl & Taylor Hawkins, Pat Smear", [" & ", ", "]
        )
        assert tokens == [
            {"type": "name", "text": "Dave Grohl"},
            {"type": "sep", "text": " & "},
            {"type": "name", "text": "Taylor Hawkins"},
            {"type": "sep", "text": ", "},
            {"type": "name", "text": "Pat Smear"},
        ], f"Unexpected tokens: {tokens}"

    def test_space_padded_separator_does_not_match_substring(self):
        tokens = tokenize_credits("oliver dragojevic i prijatelji", [" i "])
        assert tokens == [
            {"type": "name", "text": "oliver dragojevic"},
            {"type": "sep", "text": " i "},
            {"type": "name", "text": "prijatelji"},
        ], f"Unexpected tokens: {tokens}"

    def test_longest_separator_matched_first(self):
        tokens = tokenize_credits("Drake feat. Rihanna", [" feat ", " feat. "])
        assert tokens == [
            {"type": "name", "text": "Drake"},
            {"type": "sep", "text": " feat. "},
            {"type": "name", "text": "Rihanna"},
        ], f"Unexpected tokens: {tokens}"

    def test_separator_at_start_emits_orphan_sep(self):
        tokens = tokenize_credits(" & Taylor Hawkins", [" & "])
        assert tokens == [
            {"type": "sep", "text": " & "},
            {"type": "name", "text": "Taylor Hawkins"},
        ], f"Unexpected tokens: {tokens}"

    def test_separator_at_end_emits_orphan_sep(self):
        tokens = tokenize_credits("Dave Grohl & ", [" & "])
        assert tokens == [
            {"type": "name", "text": "Dave Grohl"},
            {"type": "sep", "text": " & "},
        ], f"Unexpected tokens: {tokens}"

    def test_consecutive_separators_both_emitted(self):
        tokens = tokenize_credits("Dave Grohl &  & Taylor Hawkins", [" & "])
        assert tokens == [
            {"type": "name", "text": "Dave Grohl"},
            {"type": "sep", "text": " & "},
            {"type": "sep", "text": " & "},
            {"type": "name", "text": "Taylor Hawkins"},
        ], f"Unexpected tokens: {tokens}"


class TestResolveNames:
    def test_names_are_stripped(self):
        tokens = [
            {"type": "name", "text": " Dave Grohl "},
            {"type": "sep", "text": ";"},
            {"type": "name", "text": " Taylor Hawkins "},
        ]
        assert resolve_names(tokens) == ["Dave Grohl", "Taylor Hawkins"]

    def test_ignored_sep_joins_into_single_name(self):
        tokens = [
            {"type": "name", "text": "Earth"},
            {"type": "sep", "text": ", ", "ignore": True},
            {"type": "name", "text": "Wind"},
            {"type": "sep", "text": " & ", "ignore": True},
            {"type": "name", "text": "Fire"},
            {"type": "sep", "text": " & "},
            {"type": "name", "text": "ABBA"},
        ]
        assert resolve_names(tokens) == ["Earth, Wind & Fire", "ABBA"]


class TestDefaultSeparators:
    def test_default_separators_are_defined(self):
        assert isinstance(
            DEFAULT_CREDIT_SEPARATORS, list
        ), "DEFAULT_CREDIT_SEPARATORS should be a list"
        assert (
            len(DEFAULT_CREDIT_SEPARATORS) > 0
        ), "DEFAULT_CREDIT_SEPARATORS should not be empty"
        for sep in DEFAULT_CREDIT_SEPARATORS:
            assert isinstance(sep, str), f"Separator {sep!r} should be a string"
            assert len(sep) > 0, "Separator should not be empty string"
