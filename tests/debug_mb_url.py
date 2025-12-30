
import urllib.parse

def test_mb_url(artist, title):
    # Simulate the logic in side_panel_widget.py
    aq = urllib.parse.quote(artist)
    tq = urllib.parse.quote(title)
    url = f"https://musicbrainz.org/search?query=artist:%22{aq}%22+AND+recording:%22{tq}%22&type=recording&method=indexed"
    print(f"Artist: {artist}")
    print(f"Title:  {title}")
    print(f"URL:    {url}")
    print("-" * 20)

test_mb_url("Foo Fighters", "The Pretender")
test_mb_url('The "Band"', 'Song (Remix)')
test_mb_url("AC/DC", "Highway to Hell")
