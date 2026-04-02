from src.engine.models.spotify import SpotifyCredit, SpotifyParseResult


class SpotifyService:
    """
    Pure logic service for parsing raw Spotify credits text.
    """

    @staticmethod
    def parse_credits(
        raw_text: str, reference_title: str, known_roles: list[str]
    ) -> SpotifyParseResult:
        # Split into lines and filter empty ones
        original_lines = [line.strip() for line in raw_text.splitlines()]
        # We keep empty lines for context state (resetting name)

        parsed_title = ""
        credits = []
        publishers = []

        if not original_lines:
            return SpotifyParseResult(
                parsed_title="", title_match=False, credits=[], publishers=[]
            )

        # Iterate via index to handle the fixed header/title/artist structure first
        idx = 0

        # 1. Skip "Credits"
        if idx < len(original_lines) and original_lines[idx].lower() == "credits":
            idx += 1

        # 2. Capture title
        if idx < len(original_lines):
            # Advance until we find a non-blank line
            while idx < len(original_lines) and not original_lines[idx]:
                idx += 1
            if idx < len(original_lines):
                parsed_title = original_lines[idx]
                idx += 1

        # 3. Skip "Artist" line
        while idx < len(original_lines) and not original_lines[idx]:
            idx += 1
        if idx < len(original_lines) and original_lines[idx].lower() == "artist":
            idx += 1

        current_name = ""
        in_sources = False

        # Headings to track state transitions
        headings = {
            "composition & lyrics",
            "production & engineering",
            "performers",
            "sources",
        }

        # 4. Role keywords for heuristic detection, sourced from the DB Roles table
        role_keywords = {r.lower() for r in known_roles}

        # 5. Parse the remaining lines
        for line in original_lines[idx:]:
            if not line:
                current_name = ""
                continue

            low_line = line.lower()
            if low_line in headings:
                in_sources = low_line == "sources"
                current_name = ""
                continue

            if in_sources:
                publishers.extend(p.strip() for p in line.split("/") if p.strip())
                continue

            # Core Heuristic: Role or Name?
            # Bullet lines are always roles; solo lines only if they exactly match a known role
            is_role = "\u2022" in line or low_line in role_keywords

            if is_role:
                # It's a role line ($Person -> $Role association)
                if not current_name:
                    continue  # orphaned role
                for r in line.split("\u2022"):
                    if (
                        credit_role := r.strip()
                    ) and credit_role.lower() in role_keywords:
                        credits.append(
                            SpotifyCredit(name=current_name, role=credit_role)
                        )
            else:
                # It's a name line
                current_name = line

        title_match = (
            parsed_title.lower() == reference_title.lower()
            if reference_title
            else False
        )

        return SpotifyParseResult(
            parsed_title=parsed_title,
            title_match=title_match,
            credits=credits,
            publishers=list(dict.fromkeys(publishers)),  # Deduplicate
        )
