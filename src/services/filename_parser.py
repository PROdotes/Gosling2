import re
from pathlib import Path
from typing import Dict


def parse_with_pattern(filename: str, pattern: str) -> Dict[str, str]:
    """
    Parses metadata from a filename stem using a tokenized pattern (e.g. {Artist} - {Title}).
    The last token in the pattern is greedy to absorb any remaining text.
    """
    if not filename or not pattern:
        return {}

    # 1. Isolate the stem (filename without extension)
    # Using Path.stem ensures we work on "Song - Name" even if it's "path/to/Song - Name.mp3"
    stem = Path(filename).stem

    # 2. Extract tokens from the pattern (e.g., ["Artist", "Title"])
    tokens = re.findall(r"\{(.*?)\}", pattern)
    if not tokens:
        # Fallback: if no tokens, check if pattern literally matches the stem
        return {} if pattern != stem else {}

    # 3. Create a regex string by replacing tokens with capture groups
    # We split the pattern by tokens to get the literal "delimiters" between them.
    parts = re.split(r"\{.*?\}", pattern)
    escaped_parts = [re.escape(p) for p in parts]

    regex_str = "^"
    for i in range(len(tokens)):
        regex_str += escaped_parts[i]
        token_name = tokens[i]

        # The last token in the user's pattern should be greedy (.+) to
        # allow for catching the remainder of the filename as suggested in Rule 11.
        is_last = i == len(tokens) - 1
        quantifier = ".+" if is_last else ".+?"

        if token_name.lower() == "ignore":
            # Non-capturing group for things the user wants to skip
            regex_str += f"(?:{quantifier})"
        else:
            # Named capture group for results
            regex_str += f"(?P<{token_name}>{quantifier})"

    # Add the final suffix if any exists (trailing literals after the last token)
    regex_str += escaped_parts[-1] + "$"

    # 4. Attempt to match
    try:
        match = re.match(regex_str, stem)
    except re.error:
        # If the user typed an invalid token (e.g. special characters in token name)
        # we return an empty dict instead of crashing.
        return {}

    if not match:
        return {}

    # 5. Extract and cleanup
    # We strip whitespace from the captured results for data integrity.
    return {k: v.strip() for k, v in match.groupdict().items()}
