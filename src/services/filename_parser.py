import re
from pathlib import Path
from typing import Dict, List


def parse_with_pattern(filename: str, pattern: str) -> Dict[str, str]:
    """
    Parses metadata from a filename stem using a tokenized pattern (e.g. {Artist} - {Title}).
    The last token in the pattern is greedy to absorb any remaining text.
    Duplicate tokens (e.g. two {Artist}) are collected into a list.
    """
    if not filename or not pattern:
        return {}

    # 1. Isolate the stem
    stem = Path(filename).stem

    # Strip leading UUID prefix (e.g. from staging: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx_original.mp3")
    stem = re.sub(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}_", "", stem)

    # 2. Extract tokens from the pattern (e.g., ["Artist", "Title"])
    tokens = re.findall(r"\{(.*?)\}", pattern)
    if not tokens:
        return {}

    # 3. Build regex, disambiguating duplicate token names with a numeric suffix
    parts = re.split(r"\{.*?\}", pattern)
    escaped_parts = [re.escape(p) for p in parts]
    token_counts: Dict[str, int] = {}
    capture_names: List[str] = []  # regex group name for each token position

    regex_str = "^"
    for i, token_name in enumerate(tokens):
        regex_str += escaped_parts[i]
        is_last = i == len(tokens) - 1
        quantifier = ".+" if is_last else ".+?"

        if token_name.lower() == "ignore":
            regex_str += f"(?:{quantifier})"
            capture_names.append("")
        else:
            count = token_counts.get(token_name, 0)
            token_counts[token_name] = count + 1
            group_name = f"{token_name}_{count}" if count > 0 else token_name
            capture_names.append(group_name)
            regex_str += f"(?P<{group_name}>{quantifier})"

    regex_str += escaped_parts[-1] + "$"

    # 4. Attempt to match
    try:
        match = re.match(regex_str, stem)
    except re.error:
        return {}

    if not match:
        return {}

    # 5. Merge duplicate tokens — join with "; " so downstream splitters can handle them
    raw = {k: v.strip() for k, v in match.groupdict().items()}
    result: Dict[str, str] = {}
    for base_name, count in token_counts.items():
        if count == 1:
            result[base_name] = raw[base_name]
        else:
            values = [raw[base_name]] + [
                raw[f"{base_name}_{i}"] for i in range(1, count)
            ]
            result[base_name] = "; ".join(v for v in values if v)

    return result
