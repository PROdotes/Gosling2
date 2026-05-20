import unicodedata
from src.utils.json_loaders import load_transliterations

_TRANS_MAP = load_transliterations()


def strip_diacritics(text: str) -> str:
    """Reduce text to ASCII. Applies the custom transliteration map first (for chars
    NFKD cannot decompose, e.g. Đ -> Dj, ß -> ss), then NFKD-normalizes and drops the
    combining marks left behind. Casing is preserved; used by the file writer."""
    for char, replacement in _TRANS_MAP.items():
        text = text.replace(char, replacement)
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("ascii", "ignore").decode("ascii")


def normalize_for_search(text: str) -> str:
    """Lowercase ASCII form for shadow search columns. Read and write paths must call
    this same function so the SQL LIKE target matches what was stored."""
    return strip_diacritics(text).lower()
