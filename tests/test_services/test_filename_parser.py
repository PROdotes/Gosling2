from src.services.filename_parser import parse_with_pattern


class TestFilenameParserPattern:
    def test_basic_dash_separator(self):
        filename = "Oliver - Cezanj.mp3"
        pattern = "{Artist} - {Title}"
        result = parse_with_pattern(filename, pattern)
        assert result == {"Artist": "Oliver", "Title": "Cezanj"}

    def test_ignore_track_number(self):
        filename = "01 - Oliver - Cezanj.mp3"
        pattern = "{Ignore} - {Artist} - {Title}"
        result = parse_with_pattern(filename, pattern)
        # {Ignore} should be discarded from the result dictionary
        assert result == {"Artist": "Oliver", "Title": "Cezanj"}
        assert "Ignore" not in result

    def test_extract_year_and_album(self):
        filename = "Oliver - Cezanj [Album Name] (2024).mp3"
        pattern = "{Artist} - {Title} [{Album}] ({Year})"
        result = parse_with_pattern(filename, pattern)
        assert result == {
            "Artist": "Oliver",
            "Title": "Cezanj",
            "Album": "Album Name",
            "Year": "2024",
        }

    def test_custom_underscore_separator(self):
        filename = "Oliver_Cezanj_120.wav"
        pattern = "{Artist}_{Title}_{BPM}"
        result = parse_with_pattern(filename, pattern)
        assert result == {"Artist": "Oliver", "Title": "Cezanj", "BPM": "120"}

    def test_mismatch_returns_empty_dict(self):
        # Pattern expects a dash, filename uses underscore
        filename = "Oliver_Cezanj.mp3"
        pattern = "{Artist} - {Title}"
        result = parse_with_pattern(filename, pattern)
        assert result == {}

    def test_strip_whitespace_from_results(self):
        filename = "Oliver   -   Cezanj.mp3"
        pattern = "{Artist} - {Title}"
        result = parse_with_pattern(filename, pattern)
        assert result == {"Artist": "Oliver", "Title": "Cezanj"}

    def test_dot_separator_with_extension_collision(self):
        filename = "Oliver.Cezanj.mp3"
        pattern = "{Artist}.{Title}"
        result = parse_with_pattern(filename, pattern)
        assert result == {"Artist": "Oliver", "Title": "Cezanj"}

    def test_multiple_ignores(self):
        filename = "[Official Video] Oliver - Cezanj (Original Mix).mp3"
        pattern = "[{Ignore}] {Artist} - {Title} ({Ignore})"
        result = parse_with_pattern(filename, pattern)
        assert result == {"Artist": "Oliver", "Title": "Cezanj"}

    def test_last_token_is_greedy(self):
        # The final token should absorb any trailing content
        filename = "Oliver - Cezanj - Extra Content.mp3"
        pattern = "{Artist} - {Title}"
        result = parse_with_pattern(filename, pattern)
        assert result == {"Artist": "Oliver", "Title": "Cezanj - Extra Content"}
