# Lookup Documentation Guide

These markdown files in `docs/lookup/` serve as quick-reference docs for LLMs to navigate the codebase without reading every file.

## Purpose

When an LLM needs to find where something is implemented or how to use a module, it should check these lookup files first instead of searching the entire codebase.

## Structure

Each file covers a directory in `src/`:

```
# Category Name
*Location: `src/category/`

---

## filename
*Location: `src/category/filename.py`*
**Responsibility**: Brief description of what this module does.

### function_name(args) -> return_type
Description of what this function does.
- Any important notes about usage
