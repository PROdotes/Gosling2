import pytest
from src.utils.spotify_credits_parser import parse_spotify_credits

def test_full_spotify_example():
    """Test standard Spotify credits block with multiple sections."""
    text = """
Performers
Kingsley Okorie
Bass

Benjamin James
Drums

Writing & Arrangement
Kingsley Chukwudi Okorie
Composer • Lyricist

Benjamin Chukwudi James
Composer • Lyricist

Jennifer Ejoke
Composer • Lyricist

Production & Engineering
Kingsley Okorie
Producer • Recording Engineer

Benjamin James
Producer • Recording Engineer

Spax
Mixing Engineer

Gerhard Westphalen
Mastering Engineer

Sources
Sounds From The Cave/RCA Records
"""
    # Default should only extract "Writing & Arrangement"
    artists = parse_spotify_credits(text)
    assert len(artists) == 3
    assert artists[0]["name"] == "Kingsley Chukwudi Okorie"
    assert "Composer" in artists[0]["roles"]
    assert "Lyricist" in artists[0]["roles"]
    assert artists[1]["name"] == "Benjamin Chukwudi James"
    assert artists[2]["name"] == "Jennifer Ejoke"

def test_extract_other_sections():
    """Test extracting non-default sections."""
    text = """
Performers
Kingsley Okorie
Bass
"""
    artists = parse_spotify_credits(text, include_sections=["Performers"])
    assert len(artists) == 1
    assert artists[0]["name"] == "Kingsley Okorie"
    assert artists[0]["roles"] == ["Bass"]

def test_multi_line_roles():
    """Test that roles on separate lines are consolidated."""
    text = """
Writing & Arrangement
Kingsley Okorie
Producer
Recording Engineer
"""
    artists = parse_spotify_credits(text, include_sections=["Writing & Arrangement"])
    assert len(artists) == 1
    assert "Producer" in artists[0]["roles"]
    assert "Recording Engineer" in artists[0]["roles"]

def test_multiple_role_separators():
    """Test various role separators (·, •, /, and, &)."""
    text = """
Writing & Arrangement
John Doe
Composer • Producer / Lyricist & Mixing and Engineer
"""
    artists = parse_spotify_credits(text)
    assert len(artists) == 1
    roles = artists[0]["roles"]
    assert "Composer" in roles
    assert "Producer" in roles
    assert "Lyricist" in roles
    assert "Mixing Engineer" in roles

def test_unknown_role_tokens():
    """Test that unknown tokens are preserved with Title Case."""
    text = """
Writing & Arrangement
Artist X
Future Jazz Wizard
"""
    artists = parse_spotify_credits(text)
    assert len(artists) == 1
    assert "Future Jazz Wizard" in artists[0]["roles"]

def test_non_ascii_names():
    """Test preservation of non-ASCII characters."""
    text = """
Writing & Arrangement
José Müller
Composer
"""
    artists = parse_spotify_credits(text)
    assert len(artists) == 1
    assert artists[0]["name"] == "José Müller"

def test_parenthetical_roles():
    """Test that parentheses in roles are stripped."""
    text = """
Writing & Arrangement
John Doe
(Lyricist)
"""
    artists = parse_spotify_credits(text)
    assert len(artists) == 1
    assert "Lyricist" in artists[0]["roles"]

def test_empty_input():
    """Test empty input returns empty list."""
    assert parse_spotify_credits("") == []
    assert parse_spotify_credits("   ") == []

def test_no_roles_in_section():
    """Test section with only names (heuristic should skip)."""
    text = """
Writing & Arrangement
Name Without Role

Another Name
"""
    artists = parse_spotify_credits(text)
    assert len(artists) == 0

def test_duplicate_names_in_section():
    """Test that duplicate names with different roles are included."""
    text = """
Writing & Arrangement
Spax
Composer

Spax
Producer
"""
    artists = parse_spotify_credits(text)
    assert len(artists) == 2
    assert artists[0]["roles"] == ["Composer"]
    assert artists[1]["roles"] == ["Producer"]

def test_section_name_variations():
    """Test matching variations of section names."""
    text = """
Writing and Arrangement
John Doe
Composer
"""
    artists = parse_spotify_credits(text, include_sections=["Writing & Arrangement"])
    assert len(artists) == 1
    assert artists[0]["name"] == "John Doe"
