# Identities Contract Registry

> **LAW**: This file is updated BEFORE the code changes. The signature here is the truth.
> Format: `method_name(param: type, ...) -> ReturnType — plain English description`

---

## IdentityRepository
*Location: `src/v3core/data/identity_repository.py`*

**Responsibility**: DB reads and writes for the Identities and GroupMemberships tables.

*(No methods defined yet — add them here before implementation)*

---

## ArtistNameRepository
*Location: `src/v3core/data/artist_name_repository.py`*

**Responsibility**: DB reads and writes for the ArtistNames table. The text search entry point for Tier 1 discovery.

*(No methods defined yet — add them here before implementation)*

---

## IdentityService
*Location: `src/v3core/services/identity_service.py`*

**Responsibility**: Stateless "Grohlton Brain." Takes an identity ID or name string, returns a resolved Set of all related identity IDs.

*(No methods defined yet — add them here before implementation)*
