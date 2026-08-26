# Documentation Index

Central hub for all project documentation. Every document links back here.

## Core Documents

| Document | Purpose |
|---|---|
| [../AGENTS.md](../AGENTS.md) | Engineering contract — read first, always |
| [sdd.md](sdd.md) | **Software Design Document — the Single Source of Truth (SST)** |

## Diagrams

| Diagram | Shows |
|---|---|
| [diagrams/architecture.md](diagrams/architecture.md) | System architecture — layers and components |
| [diagrams/component-design.md](diagrams/component-design.md) | Ports & adapters, module communication |
| [diagrams/data-flow-ingestion.md](diagrams/data-flow-ingestion.md) | Ingestion pipeline DFD (upload → indexed) |
| [diagrams/data-flow-query.md](diagrams/data-flow-query.md) | Query pipeline DFD (question → answer) |
| [diagrams/data-schema.md](diagrams/data-schema.md) | Data schema / ERD (SQLite + Qdrant payload) |
| [diagrams/api-interactions.md](diagrams/api-interactions.md) | API & database interaction sequences |

## Templates (copy these, never edit in place)

| Template | Use |
|---|---|
| [templates/project-context.md](templates/project-context.md) | Written once per project; reused in every AI conversation |
| [templates/feature-spec.md](templates/feature-spec.md) | Filled per feature/step (SDD-driven development) |
| [templates/agent-prompt.md](templates/agent-prompt.md) | The prompt wrapper to paste into AI conversations |

## Progress Tracking

| File | Purpose |
|---|---|
| [progress/roadmap.md](progress/roadmap.md) | Master checklist — where we are and what's next |
| `progress/stage-XX-*.md` | One spec file per stage (scope, inputs, outputs, done-when) |
| `progress/stage-XX-summary.md` | Agent-written summary after completing each stage |
| [progress/_stage-summary-template.md](progress/_stage-summary-template.md) | Template for stage summaries |

## How these files work together

```
AGENTS.md (rules)
   └── reads → sdd.md (what the system IS)
                  └── diagrams/* (how it's shaped)
   └── reads → progress/roadmap.md (where we ARE)
                  └── progress/stage-XX-*.md (what to do NOW)

templates/* → copied into AI conversations to scope each task
```
