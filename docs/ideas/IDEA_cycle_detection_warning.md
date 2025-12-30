---
tags:
  - layer/core
  - domain/tags
  - status/future
  - type/feature
  - size/small
  - value/medium
  - risk/low
  - scope/local
  - skill/python
links:
  - "[[IDEA_rule_graph_visualization]]"
---
# Cycle Detection Warning

UI alerts when auto-tag rules create infinite loops.

## Concept
- Detect circular dependencies in rules
- Show warning before saving
- Suggest which rule to break

## Example
"Tag A adds Tag B" + "Tag B adds Tag A" = cycle
