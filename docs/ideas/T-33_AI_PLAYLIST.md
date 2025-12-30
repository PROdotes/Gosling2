---
tags:
  - type/idea
  - status/future
  - scope/post-1.0
---

# T-33: AI Playlist Generation

**Status**: 💡 Idea (Post-1.0)  
**Logged by**: Vesper (2025-12-23)  
**Complexity**: 5 (High)  
**Priority**: 2 (Low — nice-to-have)

---

## 🎯 Problem Statement

User wants to create a playlist using natural language:
> "Hey, how about a playlist that's upbeat oldies?"

Current state: User must manually construct filter queries (`genre:oldies mood:upbeat`) and browse results.

---

## 💡 Proposed Solution: Feedback Loop Architecture

The LLM does **not** access the database directly. Instead, it acts as a **world-knowledge song recommendation engine**, and the app *grounds* its suggestions against the local library.

### Flow Diagram

```
┌─────────┐     "upbeat oldies"      ┌─────────┐
│  User   │ ────────────────────────►│   App   │
└─────────┘                          └────┬────┘
                                          │
                                          ▼
                                    ┌─────────┐
                                    │   LLM   │ ◄── System prompt + "Give me artist#title#"
                                    └────┬────┘
                                         │
                   song list (guesses)   ▼
                                    ┌─────────┐
                                    │   App   │ ──► fuzzy match against local DB
                                    └────┬────┘
                                         │
                   "I have X, Y, Z       ▼
                    but not A, B, C" ┌─────────┐
                                     │   LLM   │ ──► refines suggestions
                                     └─────────┘
                                          │
                              (repeat 2-3 times)
                                          │
                                          ▼
                              ┌──────────────────┐
                              │ Final ~10 songs  │ ──► user reviews & approves
                              └──────────────────┘
```

### Key Design Decisions

1. **LLM as Suggestion Engine, Not Query Builder**
   - LLM uses its world knowledge to suggest songs that match the vibe.
   - App validates suggestions exist in local library.
   - No database schema exposure to LLM = no security/privacy concerns.

2. **Fuzzy Matching Required**
   - LLM says: `"Black Sabbath#Paranoid#"`
   - Library has: `"Black Sabbath#Paranoid (Remastered)#"`
   - Need Levenshtein/fuzzy matching (e.g., `rapidfuzz` or `fuzzywuzzy`).

3. **Graceful Degradation**
   - If LLM suggests obscure songs, feedback loop adapts.
   - After 3 rounds, return best available matches even if < 10 songs.

4. **User Stays in Control**
   - Final playlist is a *suggestion*, not auto-played.
   - User can edit/reorder/reject before committing.

---

## 🛠️ Implementation Sketch (Alpha)

### Dependencies
- External LLM API (Gemini, OpenAI, local Ollama, etc.)
- Fuzzy string matching library (`rapidfuzz` recommended)

### New Components

| Component | Responsibility |
|-----------|----------------|
| `PlaylistGeneratorService` | Orchestrates LLM ↔ App loop |
| `SongMatcher` | Fuzzy match `artist#title` against `SongRepository` |
| `LLMClient` | Abstract interface for LLM API calls |

### Pseudocode

```python
class PlaylistGeneratorService:
    def __init__(self, llm_client: LLMClient, song_matcher: SongMatcher):
        self.llm = llm_client
        self.matcher = song_matcher

    async def generate(self, user_prompt: str, target_count: int = 10) -> List[Song]:
        playlist = []
        feedback = ""
        
        for round in range(3):  # max 3 refinement rounds
            response = await self.llm.suggest_songs(
                user_prompt=user_prompt,
                feedback=feedback,
                needed=target_count - len(playlist)
            )
            
            suggestions = self._parse_response(response)  # List[Tuple[artist, title]]
            
            for artist, title in suggestions:
                match = self.matcher.find_best_match(artist, title)
                if match and match not in playlist:
                    playlist.append(match)
            
            if len(playlist) >= target_count:
                break
            
            # Build feedback for next round
            found = [f"{s.artist}#{s.title}" for s in playlist]
            not_found = [f"{a}#{t}" for a, t in suggestions if not self.matcher.find_best_match(a, t)]
            feedback = f"Found: {found}. Not in library: {not_found}. Need {target_count - len(playlist)} more."
        
        return playlist[:target_count]
```

---

## ⚠️ Prerequisites

Before this feature makes sense:

1. **Rich Metadata** — Songs need `mood`, `energy`, `era` tags to inform LLM prompts.
2. **Stable Library** — 1.0 core features (import, tagging, playback) must be solid.
3. **LLM API Strategy** — Decide: cloud API (cost), local model (complexity), or user-provided key.

---

## 🔮 Future Enhancements (Post-Alpha)

- **Learning from Rejections**: If user removes songs from suggested playlist, feed that back to refine future suggestions.
- **Hybrid Mode**: Combine LLM suggestions with local tag-based filtering.
- **Offline Fallback**: If no API available, fall back to tag-based "vibe" matching.

---

## 📋 Open Questions

1. Which LLM provider? User-supplied API key vs. bundled?
2. Rate limiting / cost management for API calls?
3. Should the LLM prompt include any metadata about the library (genres available, era range)?
