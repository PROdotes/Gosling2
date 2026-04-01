from typing import List


def tokenize_credits(text: str, separators: List[str]) -> List[dict]:
    """
    Split a raw credit string into alternating name/sep tokens.
    Separators are matched longest-first to avoid prefix collisions (e.g. ' feat ' vs ' feat. ').
    Preserves exact text — no stripping.
    """
    if not text:
        return []

    if not separators:
        return [{"type": "name", "text": text}]

    sorted_seps = sorted(separators, key=len, reverse=True)

    tokens = []
    remaining = text

    while remaining:
        earliest_idx = None
        earliest_sep = None

        for sep in sorted_seps:
            idx = remaining.find(sep)
            if idx != -1 and (earliest_idx is None or idx < earliest_idx):
                earliest_idx = idx
                earliest_sep = sep

        if earliest_sep is None:
            tokens.append({"type": "name", "text": remaining})
            break

        if earliest_idx > 0:
            tokens.append({"type": "name", "text": remaining[:earliest_idx]})

        tokens.append({"type": "sep", "text": earliest_sep})
        remaining = remaining[earliest_idx + len(earliest_sep):]

    return tokens
