
import urllib.parse
from urllib.parse import unquote

def escape_lucene(s):
    # List based on Apache Lucene documentation
    special_chars = ['+', '-', '&', '|', '!', '(', ')', '{', '}', '[', ']', '^', '"', '~', '*', '?', ':', '\\', '/']
    for char in special_chars:
        s = s.replace(char, f"\\{char}")
    return s

def test_mb_url(artist, title):
    # 1. Escape Lucene chars
    safe_artist = escape_lucene(artist)
    safe_title = escape_lucene(title)
    
    # 2. Construct raw query with quotes: artist:"Name" AND recording:"Title"
    raw_query = f'artist:"{safe_artist}" AND recording:"{safe_title}"'
    
    # 3. URL Encode
    encoded_query = urllib.parse.quote(raw_query)
    
    url = f"https://musicbrainz.org/search?query={encoded_query}&type=recording&method=indexed"
    
    print("-" * 20)
    print(f"Artist: {artist}")
    print(f"Title:  {title}")
    print(f"Safe A: {safe_artist}")
    print(f"Safe T: {safe_title}")
    # Decode logic verify
    print(f"Decoded Query: {unquote(encoded_query)}")
    print(f"URL:    {url}")

test_mb_url("Foo Fighters", "The Pretender")
test_mb_url('The "Band"', 'Song (Remix)')
test_mb_url("AC/DC", "Highway to Hell")
