# Identity Repo Guards — Where Do They Belong?

The contract says repos never raise. But `identity_repository.py` has several methods that raise on business rule violations. Decide per method whether the guard stays in the repo or moves to the service layer.

---

## add_alias()
Raises `ValueError` if a name collision is detected (the name already belongs to another identity).

## delete_alias()
Raises `ValueError` if the caller tries to detach the primary name (guard: primary names cannot be detached).

## set_type()
Raises `LookupError` if the identity is not found.
Also implicitly blocks group→person conversion if members exist (check the code).

## add_member()
Raises `LookupError` if the group or member identity is not found.
Raises `ValueError` if the member is itself a group (no nested groups).

## remove_member()
Currently returns None silently — no guard. Probably fine as a noop.

## merge_orphan_into()
Raises `LookupError` if the source name is not found.
Raises `ValueError` if the source identity is not a solo orphan (has aliases or is already in a group).

## update_legal_name()
Raises `LookupError` if the identity is not found.

---

## The question for each
- Is this a **structural DB invariant** (e.g. referential integrity the DB can't enforce itself)? → possibly keep in repo.
- Is this a **business rule** (e.g. "you can't demote your primary name")? → move to service layer.
- Is it just a **not-found check** on rowcount? → definitely move to service (return rowcount, service raises LookupError).
