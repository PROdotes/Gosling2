from src.services.spotify_service import SpotifyService

KNOWN_ROLES = ["Performer", "Composer", "Lyricist", "Producer"]


class TestSpotifyServiceParse:
    def test_parse_full_credits_spec_example(self):
        """Validates the exact example from the spec."""
        raw = """Credits
Bezuvjetno
Artist

Composition & Lyrics
Goran Boskovic
Composer \u2022 Lyricist

Mirko Mirkic
Composer

Production & Engineering
Goran Boskovic
Arranger \u2022 Producer

\u017deljko Nikolin
Arranger \u2022 Producer

Mirko Mirkic
Producer

Sources
Menart/Croatia Records"""

        # Act
        res = SpotifyService.parse_credits(
            raw, reference_title="Bezuvjetno", known_roles=KNOWN_ROLES
        )

        # Assert - Rule 69 (Exhaustive fields)
        expected_title = "Bezuvjetno"
        assert (
            res.parsed_title == expected_title
        ), f"Expected {expected_title}, got {res.parsed_title}"
        assert (
            res.title_match is True
        ), f"Expected title_match to be True for '{expected_title}'"

        # Verify credits: Goran Boskovic (Composer, Lyricist, Producer — Arranger not in known_roles)
        goran_credits = [c for c in res.credits if c.name == "Goran Boskovic"]
        assert (
            len(goran_credits) == 3
        ), f"Expected 3 credits for Goran, got {len(goran_credits)}"
        roles = {c.role for c in goran_credits}
        expected_roles = {"Composer", "Lyricist", "Producer"}
        assert roles == expected_roles, f"Expected roles {expected_roles}, got {roles}"

        # Verify Zeljko Nikolin (Arranger not in known_roles, only Producer)
        zeljko_credits = [c for c in res.credits if c.name == "\u017deljko Nikolin"]
        assert (
            len(zeljko_credits) == 1
        ), f"Expected 1 credit for Zeljko, got {len(zeljko_credits)}"
        expected_zeljko_roles = {"Producer"}
        assert {
            c.role for c in zeljko_credits
        } == expected_zeljko_roles, f"Expected roles {expected_zeljko_roles}, got { {c.role for c in zeljko_credits} }"

        # Verify Mirko Mirkic
        mirko_credits = [c for c in res.credits if c.name == "Mirko Mirkic"]
        assert (
            len(mirko_credits) == 2
        ), f"Expected 2 credits for Mirko, got {len(mirko_credits)}"
        expected_mirko_roles = {"Composer", "Producer"}
        assert {
            c.role for c in mirko_credits
        } == expected_mirko_roles, f"Expected roles {expected_mirko_roles}, got { {c.role for c in mirko_credits} }"

        # Verify publishers
        expected_publishers = ["Menart", "Croatia Records"]
        assert (
            len(res.publishers) == 2
        ), f"Expected 2 publishers, got {len(res.publishers)}"
        for pub in expected_publishers:
            assert (
                pub in res.publishers
            ), f"Expected publisher '{pub}' in result {res.publishers}"

    def test_parse_title_match_is_case_insensitive(self):
        raw = "Credits\nBEZUVJETNO\nArtist"
        res = SpotifyService.parse_credits(
            raw, reference_title="bezuvjetno", known_roles=KNOWN_ROLES
        )
        assert (
            res.title_match is True
        ), f"Expected title_match to be True for case-insensitive match, got {res.title_match}"

    def test_parse_title_mismatch_fails_on_different_title(self):
        raw = "Credits\nWrong Song\nArtist"
        res = SpotifyService.parse_credits(
            raw, reference_title="Correct Song", known_roles=KNOWN_ROLES
        )
        assert (
            res.title_match is False
        ), f"Expected title_match to be False for mismatch, got {res.title_match}"

    def test_parse_empty_input_returns_graceful_defaults(self):
        res = SpotifyService.parse_credits(
            "", reference_title="Some Title", known_roles=KNOWN_ROLES
        )
        assert (
            res.parsed_title == ""
        ), f"Expected empty string for parsed_title, got '{res.parsed_title}'"
        assert (
            res.title_match is False
        ), "Expected title_match to be False for empty input"
        assert res.credits == [], f"Expected empty list for credits, got {res.credits}"
        assert (
            res.publishers == []
        ), f"Expected empty list for publishers, got {res.publishers}"

    def test_parse_junk_text_returns_empty_data(self):
        raw = "This is not a spotify credits list.\nIt has no structure."
        res = SpotifyService.parse_credits(
            raw, reference_title="Any", known_roles=KNOWN_ROLES
        )
        assert res.credits == [], f"Expected empty list for credits, got {res.credits}"
        assert (
            res.publishers == []
        ), f"Expected empty list for publishers, got {res.publishers}"

    def test_parse_role_without_name_skips_credit(self):
        """Verifies that a role line appearing before a name is ignored."""
        raw = "Credits\nTitle\nArtist\n\nComposer \u2022 Lyricist"
        res = SpotifyService.parse_credits(
            raw, reference_title="Title", known_roles=KNOWN_ROLES
        )
        assert (
            res.credits == []
        ), f"Expected empty list for orphan roles, got {res.credits}"

    def test_parse_unknown_roles_are_dropped(self):
        """Verifies that roles not in known_roles are not appended as credits."""
        raw = "Credits\nTitle\nArtist\n\nUnknown Person\nSpace Traveler \u2022 Magic Wizard"
        res = SpotifyService.parse_credits(
            raw, reference_title="Title", known_roles=KNOWN_ROLES
        )
        assert (
            res.credits == []
        ), f"Expected no credits for unknown roles, got {res.credits}"

    def test_parse_name_without_roles_is_ignored(self):
        """A name with no following bullet lines results in no credits."""
        raw = "Credits\nTitle\nArtist\n\nLonely Person\nAnother Person\nComposer \u2022 Lyricist"
        res = SpotifyService.parse_credits(
            raw, reference_title="Title", known_roles=KNOWN_ROLES
        )
        # lonely person should be gone, only another person remains
        names = {c.name for c in res.credits}
        assert "Lonely Person" not in names, "Expected 'Lonely Person' to be skipped"
        assert "Another Person" in names, f"Expected 'Another Person' in {names}"

    def test_parse_blank_line_resets_name_state(self):
        """Verify that a blank line prevents trailing roles from attaching to the wrong person."""
        raw = "Credits\nTitle\nArtist\n\nPerson A\n\nComposer \u2022 Lyricist"
        res = SpotifyService.parse_credits(
            raw, reference_title="Title", known_roles=KNOWN_ROLES
        )
        assert (
            len(res.credits) == 0
        ), f"Expected 0 credits due to name reset, got {len(res.credits)}"

    def test_parse_sources_multislash_and_whitespace(self):
        raw = "Credits\nTitle\nArtist\n\nSources\nLabel A / Label B /   Label C  "
        res = SpotifyService.parse_credits(
            raw, reference_title="Title", known_roles=KNOWN_ROLES
        )
        expected_publishers = ["Label A", "Label B", "Label C"]
        assert (
            res.publishers == expected_publishers
        ), f"Expected {expected_publishers}, got {res.publishers}"

    def test_parse_reference_title_none_fails_match(self):
        """Rule 65: Test with None parameter."""
        raw = "Credits\nTitle\nArtist"
        res = SpotifyService.parse_credits(
            raw, reference_title=None, known_roles=KNOWN_ROLES
        )
        assert (
            res.title_match is False
        ), "Expected title_match False when reference_title is None"

    def test_parse_solo_unknown_role_not_in_db_is_skipped(self):
        """A solo role line not in known_roles (e.g. Arranger not seeded) is treated as a name, not a credit."""
        raw = """Credits
Rasplele se kose Bosne
Artist

Composition & Lyrics
Miroslav Rus
Composer • Lyricist • Arranger

Mihael Blum
Arranger

Production & Engineering
Miroslav Rus
Producer

Mihael Blum
Producer

Sources
Hit Records"""
        res = SpotifyService.parse_credits(
            raw, reference_title="Rasplele se kose Bosne", known_roles=KNOWN_ROLES
        )
        blum_credits = [c for c in res.credits if c.name == "Mihael Blum"]
        assert (
            len(blum_credits) == 1
        ), f"Expected 1 credit for Blum (Producer only), got {len(blum_credits)}"
        assert blum_credits[0].role == "Producer"

    def test_parse_writer_role_expands_to_composer_and_lyricist(self):
        """Verifies that 'Writer' role expands to both Composer and Lyricist."""
        raw = "Credits\nTitle\nArtist\n\nJohn Doe\nWriter"
        # Even if Composer/Lyricist are the only known roles, Writer should work as a heuristic
        res = SpotifyService.parse_credits(
            raw, reference_title="Title", known_roles=["Composer", "Lyricist"]
        )

        assert (
            len(res.credits) == 2
        ), f"Expected 2 credits for Writer, got {len(res.credits)}"
        roles = {c.role for c in res.credits}
        assert roles == {
            "Composer",
            "Lyricist",
        }, f"Expected roles {{'Composer', 'Lyricist'}}, got {roles}"
        assert all(c.name == "John Doe" for c in res.credits)

    def test_parse_writer_expansion_is_case_insensitive(self):
        """Verifies that 'WRITER' or 'writer' also expand."""
        raw = "Credits\nTitle\nArtist\n\nJane Doe\nWRITER"
        res = SpotifyService.parse_credits(
            raw, reference_title="Title", known_roles=["Composer", "Lyricist"]
        )

        roles = {c.role for c in res.credits}
        assert roles == {"Composer", "Lyricist"}

    def test_parse_writer_with_other_roles_on_same_line(self):
        """Verifies that Writer expands when bulleted with other roles."""
        raw = "Credits\nTitle\nArtist\n\nBob Smith\nProducer \u2022 Writer"
        res = SpotifyService.parse_credits(
            raw,
            reference_title="Title",
            known_roles=["Composer", "Lyricist", "Producer"],
        )

        roles = {c.role for c in res.credits}
        assert roles == {"Producer", "Composer", "Lyricist"}

    def test_parse_writer_expansion_deduplicates_against_explicit_roles(self):
        """Verifies that if Composer is also listed, we don't get a duplicate 'Composer'."""
        raw = "Credits\nTitle\nArtist\n\nAlice Ali\nComposer \u2022 Writer"
        res = SpotifyService.parse_credits(
            raw, reference_title="Title", known_roles=["Composer", "Lyricist"]
        )

        # Alice should have exactly 2 credits: Composer and Lyricist (not 2x Composer)
        assert len(res.credits) == 2, f"Expected 2 credits, got {len(res.credits)}"
        roles = [c.role for c in res.credits]
        assert roles.count("Composer") == 1
        assert roles.count("Lyricist") == 1
