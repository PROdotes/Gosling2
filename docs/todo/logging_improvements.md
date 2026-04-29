# Logging Improvements

## Problem
Application logs trace what happened but not why. Symptoms:
- A single UI action triggers 10 hydrations — logs show the calls but not the originating action.
- Manual edits (credits, publisher, album, ISRC) leave no trace — only the initial ingest ID3 data is logged.
- When something breaks, you have to read the code to reconstruct the call chain.

## What's needed
1. **Write operation logging** — service layer should log every data mutation at INFO level.
   - What changed (field, old value, new value)
   - Which song/entity
   - Timestamp
   - Example: `[EditService] <- update_credits(song_id=223) added Performer 'z++'`

2. **Caller context** — log the triggering action, not just the repository call.
   - Currently: 10 identical `get_song` DEBUG lines with no indication of why
   - Needed: one INFO line at the service entry point naming the operation

## Scope
Separate from the audit refactor (docs/specs/AUDIT_REFACTOR_SPEC.md), which is about transactional audit trails in the DB. This is about making gosling.log useful for debugging without reading the code.
