from src.utils.text import strip_diacritics, normalize_for_search, _TRANS_MAP


class TestTransliterationMap:
    """Guard rails: if someone removes a key from transliterations.json,
    the functional tests below would silently change behavior. These assert the
    map itself contains the entries the matrix depends on."""

    def test_slavic_dj_present(self):
        assert _TRANS_MAP.get("Đ") == "Dj"
        assert _TRANS_MAP.get("đ") == "dj"

    def test_eszett_present(self):
        assert _TRANS_MAP.get("ß") == "ss"

    def test_ligatures_present(self):
        assert _TRANS_MAP.get("Æ") == "Ae"
        assert _TRANS_MAP.get("æ") == "ae"
        assert _TRANS_MAP.get("Œ") == "Oe"
        assert _TRANS_MAP.get("œ") == "oe"


class TestStripDiacritics:
    """Casing-preserving ASCII reduction. Used by the file writer."""

    def test_empty_string(self):
        assert strip_diacritics("") == ""

    def test_pure_ascii_passthrough(self):
        assert strip_diacritics("DJ Khaled") == "DJ Khaled"
        assert strip_diacritics("Keiino") == "Keiino"

    def test_nfkd_decomposable_accents(self):
        # NFKD splits these into base + combining mark; ascii-ignore drops the mark.
        assert strip_diacritics("MÖTLEY CRÜE") == "MOTLEY CRUE"
        assert strip_diacritics("Måneskin") == "Maneskin"
        assert strip_diacritics("Noëp") == "Noep"
        assert strip_diacritics("Sigur Rós") == "Sigur Ros"

    def test_eszett_to_ss(self):
        # ß has no NFKD decomposition; only the custom map saves it from being dropped.
        assert strip_diacritics("Straße") == "Strasse"

    def test_slavic_dj_explicit_mapping(self):
        # Đ / đ are atomic; without the custom map they would be dropped by ascii-ignore.
        assert strip_diacritics("Đorđe") == "Djordje"

    def test_no_digraph_collapse(self):
        # Existing 'dj' in real words must remain untouched — no collapse.
        assert strip_diacritics("DJ Khaled") == "DJ Khaled"
        assert strip_diacritics("Djelim sa tobom") == "Djelim sa tobom"

    def test_ligatures(self):
        assert strip_diacritics("Æther") == "Aether"
        assert strip_diacritics("œuvre") == "oeuvre"

    def test_casing_preserved(self):
        assert strip_diacritics("MÖTLEY CRÜE") == "MOTLEY CRUE"
        assert strip_diacritics("mötley crüe") == "motley crue"


class TestNormalizeForSearch:
    """Same as strip_diacritics but lowercased. Used to populate _Search columns
    and to normalize incoming search queries — read and write must agree."""

    def test_empty_string(self):
        assert normalize_for_search("") == ""

    def test_lowercases_after_stripping(self):
        assert normalize_for_search("MÖTLEY CRÜE") == "motley crue"
        assert normalize_for_search("Noëp") == "noep"
        assert normalize_for_search("Måneskin") == "maneskin"

    def test_slavic_dj(self):
        assert normalize_for_search("Đorđe") == "djordje"

    def test_eszett(self):
        assert normalize_for_search("Straße") == "strasse"

    def test_read_write_symmetry(self):
        # The whole point: query a name typed any way matches the stored shadow form.
        stored = normalize_for_search("Noëp")
        assert normalize_for_search("noep") == stored
        assert normalize_for_search("NOËP") == stored
        assert normalize_for_search("Noep") == stored

    def test_no_digraph_collapse(self):
        assert normalize_for_search("DJ Khaled") == "dj khaled"
