import re
from typing import List, Dict, Optional, Tuple

ROLE_SEPARATORS = re.compile(r'\s*[•·,/;&]\s*|\s+and\s+|\s*&\s*', flags=re.IGNORECASE)

ROLE_SYNONYMS = {
    'composer': 'Composer',
    'writer': 'Composer',
    'lyricist': 'Lyricist',
    'producer': 'Producer',
    'mixing': 'Mixing Engineer',
    'mix engineer': 'Mixing Engineer',
    'recording engineer': 'Recording Engineer',
    'mastering engineer': 'Mastering Engineer',
    'vocals': 'Vocals',
    'bass': 'Bass',
    'drums': 'Drums',
}

def normalize_role(token: str) -> str:
    t = re.sub(r'[().]', '', token).strip().lower()
    if t in ROLE_SYNONYMS:
        return ROLE_SYNONYMS[t]
    return token.strip().title()

def parse_spotify_credits(text: str) -> List[Tuple[str, str]]:
    """
    Parses Spotify credits into a flat stream of (value, label) tuples.
    Labels include: 'Title', 'Performer' (main artist), 'Publisher', or Role Name.
    """
    text = text.replace('\r\n', '\n').strip()
    if not text:
        return []

    results: List[Tuple[str, str]] = []

    # 1. Sectioning Pass
    sections = {}
    current_section = "Credits"
    current_content = []
    
    HEADER_PATTERN = re.compile(r'^(Credits|Artist|Performers|Writing\s*(&|and)\s*Arrangement|Production\s*(&|and)\s*Engineering|Sources|Management|Personnel|Other\s+Roles)', re.IGNORECASE)
    skip_sections = []

    for line in text.split('\n'):
        line_clean = line.strip()
        if not line_clean and not current_content:
            continue
            
        match = HEADER_PATTERN.match(line_clean)
        if match:
            if current_content:
                sections[current_section] = '\n'.join(current_content).strip()
            current_section = match.group(0).title()
            current_content = []
        else:
            current_content.append(line)

    if current_content:
        sections[current_section] = '\n'.join(current_content).strip()

    # 2. Emit Metadata (Title)
    if "Credits" in sections:
        lines = [l.strip() for l in sections["Credits"].split('\n') if l.strip()]
        skip_sections.append("Credits")
        if lines:
            results.append((lines[0], "Title"))

    # 3. Emit Publishers
    if "Sources" in sections:
        parts = re.split(r'[\n/•·]', sections["Sources"])
        skip_sections.append("Sources")
        for p in parts:
            p_clean = p.strip()
            if p_clean and len(p_clean) > 1:
                results.append((p_clean, "Publisher"))

    # 4. Emit Artist Roles
    for sec_name, content in sections.items():
        if sec_name in skip_sections:
            continue
            
        # Parse names/roles from blocks
        blocks = re.split(r'\n\s*\n', content)
        for block in blocks:
            lines = [l.strip() for l in block.split('\n') if l.strip()]
            if not lines: continue
            
            name = lines[0]
            for role_line in lines[1:]:
                tokens = ROLE_SEPARATORS.split(role_line)
                for t in tokens:
                    if not t.strip(): continue
                    
                    # Normalize role (remember normalize_role returns a single string now)
                    role = normalize_role(t)
                    results.append((name, role))

    return results

