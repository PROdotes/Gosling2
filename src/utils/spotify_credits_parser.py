import re
from typing import List, Dict, Optional

# Constants for parsing
ROLE_SEPARATORS = re.compile(r'\s*[•·,/;&]\s*|\s+and\s+|\s*&\s*', flags=re.IGNORECASE)
SECTION_HEADER = re.compile(r'^(Performers|Writing\s*(&|and)\s*Arrangement|Production\s*(&|and)\s*Engineering|Sources|Management|Personnel)', re.IGNORECASE)

# Seeded from DB Roles table + common synonyms
ROLE_SYNONYMS = {
    'composer': 'Composer',
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
    """Clean punctuation, normalize to canonical role."""
    # Strip parentheses and dots
    t = re.sub(r'[().]', '', token).strip().lower()
    
    # Check synonyms
    if t in ROLE_SYNONYMS:
        return ROLE_SYNONYMS[t]
    
    # Fallback: Preservation with title-case
    return token.strip().title()

def parse_spotify_credits(text: str, include_sections: Optional[List[str]] = None) -> List[Dict]:
    """
    Parse Spotify credits by section.

    Args:
        text: Raw Spotify credits block text.
        include_sections: List of sections to parse (default: ["Writing & Arrangement"]).
                         Other valid: "Performers", "Production & Engineering", etc.

    Returns:
        List of dicts: [{"name": str, "roles": list, "section": str, "source": str}]
    """
    if include_sections is None:
        include_sections = ["Writing & Arrangement"]

    # Normalize include_sections for easier matching (replace & with and, strip whitespace)
    normalized_includes = [s.lower().replace('&', 'and').replace(' ', '') for s in include_sections]

    text = text.replace('\r\n', '\n').strip()
    if not text:
        return []

    # Split by section headers
    sections = {}
    current_section = None
    current_content = []

    for line in text.split('\n'):
        line_clean = line.strip()
        if not line_clean and not current_section:
            continue
            
        match = SECTION_HEADER.match(line_clean)
        if match:
            # Save previous section
            if current_section and current_content:
                sections[current_section] = '\n'.join(current_content).strip()
            # Start new section
            current_section = line_clean
            current_content = []
        elif current_section:
            current_content.append(line)

    # Save last section
    if current_section and current_content:
        sections[current_section] = '\n'.join(current_content).strip()
    
    # Parse artists from included sections
    artists = []
    for section_name, content in sections.items():
        # Normalize section name for matching (replace & with and, strip whitespace)
        section_norm = section_name.lower().replace('&', 'and').replace(' ', '')
        
        is_included = False
        for s in normalized_includes:
            if s in section_norm:
                is_included = True
                break
        
        if not is_included:
            continue

        # Parse artist/role pairs in this section using block-based separation
        artists.extend(_parse_section(content, section_name))

    return artists

def _parse_section(content: str, section_name: str) -> List[Dict]:
    """Parse artist/role pairs within a section."""
    # Spotify format uses empty lines to separate artist blocks
    # We split by one or more empty lines
    blocks = re.split(r'\n\s*\n', content)
    artists = []

    for block in blocks:
        lines = [l.strip() for l in block.split('\n') if l.strip()]
        if not lines:
            continue

        # Heuristic for name/role detection within a block
        # First line is always the name in Spotify format
        name = lines[0]
        roles = []
        
        # Remaining lines in the block are roles
        for role_line in lines[1:]:
            # If a line looks like another artist (e.g. no role tokens), 
            # we might have a name without roles or a smashed block.
            # But usually Spotify blocks are 1 name + N roles.
            tokens = ROLE_SEPARATORS.split(role_line)
            roles.extend([normalize_role(t) for t in tokens if t.strip()])

        if name and roles:
            artists.append({
                "name": name,
                "roles": list(dict.fromkeys(roles)), # Maintain order but unique
                "section": section_name,
                "source": "spotify_import"
            })
            
    return artists


