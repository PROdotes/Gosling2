---
description: Vertical Slice Blueprinting (Contract-First Planning)
---
1. **Identify the Vertical Slice**: Define the path from Repo -> Service/Business -> API Router -> Frontend JS.
2. **Audit the Haystack**: Run a schema/grep audit for the related entities (check CASCADE, SOFT-DELETE, and Constraints).
3. **Generate the VSM Table**: Map every [Input x DB State] permutation to a Hard-Outcome across all 4 layers.
4. **Identify the "Needle"**: Explicitly list potential failure modes (Concurrency, Duplicate, Missing ID, Soft-Delete).
5. **STOP**: Present the Matrix and Signatures. Do NOT write code (Tests or Implementation) until the User signs off on the "Banker Mode" rules.
