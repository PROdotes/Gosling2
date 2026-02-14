# Code Dependency Explorer

A WYSIWYG visual tool for exploring Python code dependencies and identifying dead code.

## Overview

This tool parses your Python codebase and creates an interactive graph showing:
- **Method call chains** (who calls what)
- **Dead code detection** (unused methods highlighted in red)
- **CRUD audit tracking** (which database operations have audit logging)
- **Cross-file dependencies** (navigate across the entire codebase)

## Features

### Visual Graph View
- **Nodes** represent methods, classes, and functions
- **Edges** show call relationships
- **Color coding**:
  - 🟢 Green: Actively used methods
  - 🔴 Red: Dead code (unused)
  - 🟡 Yellow: Only called by dead code (cascading unused)
  - 🔵 Blue: Entry points (called from UI/main)

### Interactive Navigation
- **Click any node** to see its details
- **Double-click** to jump to source code
- **Ctrl+Click** to trace the full call chain
- **Right-click** for context menu (find callers, find callees)
- **Zoom and pan** the graph freely

### Dead Code Detection
The tool uses static analysis to find:
1. Methods never called
2. Methods only called by other dead code
3. Repository methods without service callers
4. Service methods without UI callers

### CRUD Audit Overlay
Database operations are flagged:
- ✅ Green border: Has AuditLogger with batch_id
- ⚠️ Yellow border: Has AuditLogger but missing batch_id
- ❌ Red border: No audit logging found

## Usage

```bash
# Run the explorer
python tools/code_explorer/code_explorer.py

# Or specify a different source directory
python tools/code_explorer/code_explorer.py --src /path/to/code
```

## Controls

| Action | Shortcut |
|--------|----------|
| Zoom in | Ctrl + Plus |
| Zoom out | Ctrl + Minus |
| Reset view | Ctrl + 0 |
| Find method | Ctrl + F |
| Toggle dead code | Ctrl + D |
| Refresh graph | F5 |
| Export to PNG | Ctrl + E |

## Architecture

### Components

1. **ASTParser** (`parser/`)
   - Walks Python AST
   - Extracts method definitions
   - Finds call sites
   - Builds dependency graph

2. **GraphEngine** (`graph/`)
   - Force-directed layout
   - Node positioning
   - Edge routing
   - Collision detection

3. **UI Layer** (`ui/`)
   - PyQt6 graphics view
   - Interactive nodes
   - Pan/zoom controls
   - Property panels

### Data Flow

```
Source Code → AST Parser → Dependency Graph → Layout Engine → Qt Graphics View
                ↓
            Dead Code Analysis
                ↓
            CRUD Audit Check
```

## Future Enhancements

- [ ] **Diff mode**: Compare two commits, see what changed
- [ ] **Filter by module**: Only show specific packages
- [ ] **Metrics overlay**: Show complexity, line count
- [ ] **Export formats**: SVG, GraphML, DOT
- [ ] **Team annotations**: Mark methods with comments
- [ ] **Test coverage**: Show which dead code has tests

## Integration with Existing Tools

The tool can read:
- **vulture** output for dead code hints
- **pytest** coverage for test status
- **mypy** types for better node labels
- **git** history for change frequency

## Why This Exists

Traditional IDEs show code hierarchies (classes, methods) but not **usage hierarchies** (who calls what). This tool fills that gap by visualizing the runtime call graph as a static dependency map.

Perfect for:
- **Refactoring**: See the impact of changes before making them
- **Code reviews**: Understand dependencies at a glance
- **Onboarding**: Visualize codebase structure
- **Cleanup**: Find and remove dead code safely

## Contributing

Add new analysis modules to `analyzer/`:
- `dead_code.py` - Current implementation
- `circular_deps.py` - Find import cycles
- `complexity.py` - Calculate cyclomatic complexity

Add new visualizations to `ui/views/`:
- `circular_view.py` - Radial layout
- `timeline_view.py` - Show code evolution

## License

Part of the Gosling project.
