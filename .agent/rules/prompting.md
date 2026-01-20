---
trigger: always_on
---

# User Interaction & UI Guidelines

## 1. Speak Human, Not Tech
- **Avoid Jargon**: Never use terms like "Merge", "Consume", "Identity", "Entity", "Conflict", "Resolution", or "Database" in UI wording.
- **Hide the Plumbing**: Do not describe the technical steps the system is taking (e.g., "Moving songs", "Updating references"). Focus ONLY on the end result.
  - Bad: "Do you want to move all songs from 'Abb' to 'Abba'?" (Process-focused)
  - Good: "Do you want to combine them?" (Outcome-focused)

## 2. Keep It Simple (The "Night Shift DJ" Rule)
- **Minimal Text**: Reading takes time. Use the fewest words possible to convey the meaning.
- **One Clear Goal**: Dialogs should focus on a single decision. Don't overload the user with multiple options.
- **Context Matters**: A DJ working a night shift doesn't have the mental bandwidth to parse complex logic or read about file operations.
- **Don't Ask Obvious Questions**: If the user renames "Abb" to "Abba", they obviously know "Abba" exists. Don't confirm facts ("Abba is already in your library"). Just confirm the ACTION ("Combine them?").

## 3. The Baggage Rule (Non-Negotiable)
- **Silent by Default**: Renaming or Linking is an expression of intent. The system should just execute.
- **No Prompt for Shells**: If merging A into B, and B has no songs, no aliases, and no group members, do it **silently**. 
- **The Only Prompt Scenario**: Only prompt if B has "baggage" (existing aliases or structural relationships) that would be non-trivially combined with A's. Even then, keep it to a single "Combine?" question.
- **Never technical**: Do not list usage counts or primary keys.

## 4. Warn Only When Destructive
- **Don't Nag**: Do not confirm routine actions (e.g., successful saves).
- **Destructive Warnings**: Only interrupt the user if they are about to permanently lose data or make a significant, hard-to-reverse change.
- **Clear Consequences**: If you do warn, explain *exactly* what will happen in plain English (e.g., "This will delete 'Abb'.").

## 4. Specific Scenarios
- **Renaming to Existing Item**:
  - Implied Intent: The user likely made a typo or wants to consolidate.
  - Preferred Action: "Combine" or "Fix".
  - Avoid framing it as a technical "Merge vs Alias" choice unless the context demands it.