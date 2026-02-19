---
description: Prime the agent with project expertise from the Mulch directory
---
Whenever starting a new session or domain-specific task, follow these steps to ensure you are up to date on project conventions and past failures:

1. **Check for .mulch directory**: Look for the `.mulch/expertise` folder in the project root.
2. **Read Domain Expertise**:
   - If working on UI, read `.mulch/expertise/ui.jsonl`.
   - If working on Business Logic or Metadata, read `.mulch/expertise/business.jsonl`.
3. **Parse Records**:
   - `failure`: Pay attention to the "resolution" to avoid repeating bugs.
   - `convention`: Follow these rules strictly as they represent established project patterns.
   - `pattern`: Use these as templates for new implementations.
4. **Use Mulch Tools (if available)**:
   - Run `mulch status` to see the health of documentation.
   - Run `mulch prime [domain]` to generate a summary of specific expertise.
   - Use `mulch record` after fixing a tricky bug or establishing a new convention.

**CRITICAL**: Do not refactor core services without first checking for associated "tactical failures" in Mulch.
