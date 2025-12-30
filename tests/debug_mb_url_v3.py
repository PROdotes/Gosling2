
import urllib.parse
from urllib.parse import unquote

def test_app_logic(artist, title):
    # Exact logic from side_panel_widget.py (Step 229)
    # Quote safety ONLY
    safe_artist = artist.replace('"', '\\"')
    safe_title = title.replace('"', '\\"')
    
    # Construct phrase query
    raw_query = f'artist:"{safe_artist}" AND recording:"{safe_title}"'
    encoded_query = urllib.parse.quote(raw_query)
    
    url = f"https://musicbrainz.org/search?query={encoded_query}&type=recording&method=indexed"
    
    print("-" * 20)
    print(f"Artist: {artist}")
    print(f"Title:  {title}")
    print(f"URL:    {url}")

test_app_logic("AC/DC", "Highway to Hell")
