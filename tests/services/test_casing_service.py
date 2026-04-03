import pytest
from src.services.casing_service import CasingService

class TestCasingServiceTitleCase:
    def test_title_case_standard(self):
        assert CasingService.to_title_case("RAZGLEDNICA") == "Razglednica"

    def test_title_case_multi_word(self):
        assert CasingService.to_title_case("THE GREAT ESCAPE") == "The Great Escape"

    def test_title_case_every_word_capitalized(self):
        # User explicitly requested NO minor word exceptions
        assert CasingService.to_title_case("queeen of the stone age") == "Queeen Of The Stone Age"

    def test_title_case_parentheses(self):
        # (Radio Edit) should stay (Radio Edit)
        assert CasingService.to_title_case("song name (radio edit)") == "Song Name (Radio Edit)"

    def test_title_case_empty(self):
        assert CasingService.to_title_case("") == ""

    def test_title_case_none_raises(self):
        with pytest.raises(ValueError):
            CasingService.to_title_case(None)

class TestCasingServiceSentenceCase:
    def test_sentence_case_standard(self):
        assert CasingService.to_sentence_case("RAZGLEDNICA") == "Razglednica"

    def test_sentence_case_multi_word(self):
        assert CasingService.to_sentence_case("THE GREAT ESCAPE") == "The great escape"

    def test_sentence_case_empty(self):
        assert CasingService.to_sentence_case("") == ""

    def test_sentence_case_none_raises(self):
        with pytest.raises(ValueError):
            CasingService.to_sentence_case(None)
