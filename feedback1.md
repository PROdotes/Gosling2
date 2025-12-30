To make this UI feel cohesive and intentional, you need to tighten visual hierarchy, consistency, and focus. The screen is not fundamentally broken; it is fragmented. Below is a structured, design-system–oriented approach to “bringing it together.”

1. Establish a Clear Visual Hierarchy
Right now, everything has roughly the same weight, which forces the eye to scan instead of flow.
Primary
Track Identity: Artist – Title
This should be the strongest visual element on the screen.
Increase size and weight.
Reduce surrounding noise (icons, borders).
Secondary
Core metadata: Performer, Title, Album, Year, Genre
These should read as one logical group.
Visually cluster them (shared background or subtle divider).
Tertiary
Administrative metadata: ISRC, Publisher, Producer, Lyricist, Notes
These should visually recede.
Smaller labels, lighter contrast, possibly collapsible.
Actionable change
Split the form into two vertical sections:
Track Info
Rights & Publishing

2. Reduce Over-Bordering and “Box Fatigue”
Nearly every element is boxed, outlined, or inset. This creates visual noise.
Problems
Inputs, buttons, headers, and containers all use similar outlines.
No element feels special because everything is emphasized.
Fix
Choose one primary containment method:
Either cards OR outlines—not both.
Prefer flat inputs with a single bottom border or subtle fill.
Reserve strong outlines for:
Active focus
Primary action buttons
Rule of thumb
If everything is framed, nothing is framed.

3. Normalize Spacing and Alignment
Spacing inconsistency is one of the biggest reasons UIs feel “off.”
What to do
Use a spacing scale (e.g., 8px system: 8 / 16 / 24 / 32).
Ensure:
Equal vertical spacing between all fields
Labels align perfectly on a baseline
Inputs are the same height
Specific to your UI
“YEAR” and “GENRE” feel cramped and misaligned relative to other fields.
Buttons at the bottom need more separation from form fields.

4. Clarify Label vs. Value Relationships
Labels currently compete with their inputs.
Improve readability
Make labels:
Smaller
Lighter (reduced opacity)
Consistent casing (all caps or sentence case, not mixed)
Let input values carry the visual weight.
This is especially important in dense metadata tools like this.

5. Rationalize Color Usage
Your color palette is doing too much work.
Issues
Yellow, green, white, and gray all compete for attention.
“READY [AIR]” glows more than the actual Save action.
Recommendations
Pick one accent color for actions (e.g., Save, Edit Mode).
Use color semantics:
Green = status/valid
Yellow = warning or edit mode
Neutral = default
Critical fix
Decide whether “READY [AIR]” is:
A status indicator → make it passive
An action → make it the primary CTA
It cannot be both.

6. Improve Button Hierarchy
Bottom actions are unclear.
Current problems
“Discard” and “Save” are visually similar.
The status indicator sits between them, breaking flow.
Better structure
Group actions:
Primary: Save
Secondary: Discard
Move status above or below the action bar, not inside it.

7. Unify Typography
Typography consistency will immediately make this feel professional.
If possible:
Use one font family
Define:
Header
Section label
Field label
Input text
Avoid mixing weights and sizes ad hoc.

8. Think in Terms of a Design System
Ask yourself:
What does a “field” look like everywhere?
What does an “action” look like everywhere?
What does a “status” look like everywhere?
If the answer changes per screen, the UI will never feel cohesive.
