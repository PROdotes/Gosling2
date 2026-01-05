# Architecture Improvement Suggestions

## Context
While planning the ID3Registry and tag category refactoring, we identified some architectural patterns that could be improved. This document captures suggestions for future consideration.

---

## 1. ✅ **Current Good Practices**

Your codebase already follows solid patterns:
- **3-tier architecture** (Presentation → Business → Data)
- **Repository pattern** for data access
- **Service layer** for business logic
- **Dependency injection** (services inject repositories)
- **Type hints** throughout

---

## 2. 🔧 **Suggested Improvements**

### **A. Consolidate "Core" vs "Business/Services"**

**Current State:**
- `src/core/` contains: `yellberus.py`, `logger.py`, `audit_logger.py`
- `src/business/services/` contains: 16 service files

**Issue:**
The distinction between "core" and "business/services" is unclear. Some things in `core/` are actually utilities/registries, not business logic.

**Suggestion:**
```
src/
├── core/                    # Core domain logic & registries
│   ├── registries/          # NEW: Data registries (read-only)
│   │   ├── id3_registry.py      # ID3 frame mappings
│   │   └── field_registry.py    # Yellberus field definitions
│   ├── domain/              # NEW: Domain models & validation
│   │   └── yellberus.py         # Field definitions & validation
│   └── utils/               # NEW: Cross-cutting utilities
│       ├── logger.py
│       └── audit_logger.py
│
├── business/
│   └── services/            # Business operations (read/write)
│       ├── metadata_service.py
│       ├── tag_service.py
│       └── ...
```

**Benefits:**
- Clear separation: Registries (read-only config) vs Services (operations)
- Easier to find things
- Better testability (mock registries separately from services)

---

### **B. Introduce a "Config" Layer**

**Current State:**
- `id3_frames.json` loaded in multiple places
- Settings scattered across `SettingsManager` and constants
- No centralized configuration management

**Suggestion:**
```
src/
├── config/                  # NEW: Configuration layer
│   ├── __init__.py
│   ├── app_config.py        # Application settings
│   ├── id3_config.py        # ID3 frame definitions (loads JSON)
│   └── constants.py         # Moved from resources/
│
├── resources/               # Static data files only
│   ├── id3_frames.json
│   └── styles.qss
```

**Benefits:**
- Single source of truth for configuration
- Easier to add environment-specific configs (dev/prod)
- Clearer separation of code vs data

---

### **C. Add a "Shared" or "Common" Module**

**Current State:**
- Some utilities might be duplicated
- No clear place for cross-cutting concerns

**Suggestion:**
```
src/
├── shared/                  # NEW: Shared utilities
│   ├── validators.py        # Common validation logic
│   ├── formatters.py        # String/date formatting
│   ├── exceptions.py        # Custom exceptions
│   └── decorators.py        # Common decorators (caching, logging)
```

**Benefits:**
- Avoid duplication
- Clear place for reusable utilities
- Better organization

---

### **D. Consider Event-Driven Communication**

**Current State:**
- Direct service-to-service calls
- Tight coupling in some areas

**Future Enhancement:**
```python
# src/core/events.py
class EventBus:
    """Simple pub/sub for decoupling components."""
    
    @classmethod
    def publish(cls, event_type: str, data: dict):
        """Publish an event."""
        
    @classmethod
    def subscribe(cls, event_type: str, handler: Callable):
        """Subscribe to an event."""

# Example usage:
# When a tag is created:
EventBus.publish("tag_created", {"category": "Genre", "name": "Rock"})

# UI can subscribe:
EventBus.subscribe("tag_created", self.refresh_tag_list)
```

**Benefits:**
- Loose coupling between components
- Easier to add features without modifying existing code
- Better for undo/redo, audit logging

**Trade-offs:**
- More complexity
- Harder to trace execution flow
- **Only add if you need it** (YAGNI principle)

---

### **E. Standardize Service Interfaces**

**Current State:**
- Services have inconsistent method signatures
- Some use class methods, some use instance methods

**Suggestion:**
Create a base service class:

```python
# src/business/services/base_service.py
from abc import ABC
from typing import TypeVar, Generic

T = TypeVar('T')

class BaseService(ABC, Generic[T]):
    """Base class for all business services."""
    
    def __init__(self, repository=None):
        self.repository = repository
    
    def get_by_id(self, id: int) -> T:
        """Standard get by ID."""
        return self.repository.get_by_id(id)
    
    # ... other common methods
```

**Benefits:**
- Consistent API across services
- Easier to understand and maintain
- Better for testing (mock base class)

---

## 3. 📋 **Specific to ID3Registry Refactoring**

### **Recommended Placement:**

**Option A: Core/Registries (Recommended)**
```
src/core/registries/id3_registry.py
```
- Treats it as a read-only data registry
- Clear separation from business services
- Aligns with "single responsibility"

**Option B: Config**
```
src/config/id3_config.py
```
- Treats it as configuration
- Good if you plan to add more config loaders

**Option C: Business/Services (Not Recommended)**
```
src/business/services/id3_service.py
```
- Mixes read-only registry with business operations
- Less clear separation of concerns

---

## 4. 🎯 **Priority Recommendations**

### **High Priority (Do Now):**
1. ✅ Create `ID3Registry` in `src/core/` (as planned)
2. ✅ Refactor tag categories to be data-driven

### **Medium Priority (Next Refactor):**
3. Consider moving `yellberus.py` to `src/core/domain/`
4. Create `src/core/registries/` folder for future registries
5. Update `ARCHITECTURE.md` to reflect current state

### **Low Priority (Future):**
6. Add `src/shared/` for common utilities
7. Standardize service interfaces
8. Consider event bus (only if needed)

---

## 5. 🚫 **Things to Avoid**

1. **Over-engineering**: Don't add layers you don't need
2. **Microservices**: This is a desktop app, not a distributed system
3. **Too many abstractions**: Keep it simple and readable
4. **Premature optimization**: Solve real problems, not theoretical ones

---

## 6. 📝 **Action Items**

- [ ] Proceed with ID3Registry in `src/core/id3_registry.py`
- [ ] After refactoring, update `ARCHITECTURE.md` (currently marked outdated)
- [ ] Consider creating `src/core/registries/` folder structure
- [ ] Document the registry pattern in architecture docs

---

## Summary

Your architecture is already solid! The main suggestions are:
1. **Better organization** of core utilities vs business services
2. **Centralized configuration** management
3. **Consistent patterns** across services

The ID3Registry refactoring is a good step in this direction. Keep it simple, and only add complexity when you have a real need.
