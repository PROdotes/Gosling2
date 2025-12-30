# Project Tools Reference

This document lists project-specific tools and their ownership domains. Agents must respect these boundaries.

---

## 📁 Location: `tools/`

### Field Editor (`tools/field_editor.py`)
**Purpose**: Manages Yellberus field definitions.

**Owns**:
- All `FieldDef` properties in `src/core/yellberus.py` EXCEPT `query_expression`
- Cross-references with `id3_frames.json` for portable fields
- Syncs with `../docs/FIELD_REGISTRY.md`

**Agent Rules**:
- ❌ **DO NOT** manually edit field properties (visible, filterable, required, etc.)
- ✅ **CAN** add/edit `query_expression` (complex SQL not in Field Editor scope)
- ✅ **CAN** add new ID3 mappings to `id3_frames.json` before using Field Editor
- 🙋 **ASK** if you disagree with field definitions

**Usage**:
```bash
python tools/field_editor.py
```

---

## 📁 Location: `tests/tools/`

### Fixture Injector (`tests/tools/inject_fixtures.py`)
**Purpose**: Seeds database with test data from JSON fixtures.

**Owns**:
- Test data injection workflow
- Reads from `tests/fixtures/test_songs.json`

**Agent Rules**:
- ✅ **CAN** update to handle new fields
- ✅ **CAN** add new fixture JSON files
- ❌ **DO NOT** use for production data

**Usage**:
```bash
python tests/tools/inject_fixtures.py
```

---

## 📁 Location: `scripts/`

### Miscellaneous Scripts
| Script | Purpose | Status |
|--------|---------|--------|
| `seed_dave_grohl.py` | Legacy test data seeder | ⚠️ Deprecated (use inject_fixtures) |
| `audit_schema.py` | Schema auditing | Active |
| `validate_schema.py` | Schema validation | Active |
| `inspect_groups.py` | Debug group relationships | Active |
| `mutation_test.py` | Mutation testing | Active |

---

## Adding New Tools

When creating new tools:
1. Place in appropriate directory (`tools/` or `scripts/`)
2. Add entry to this document
3. Define ownership boundaries
4. Specify what agents can/cannot do

---

*Last updated: 2025-12-23 by Vesper*
