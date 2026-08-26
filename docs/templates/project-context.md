# Template — Project Context

> Write this **once per project**, then reuse it in every AI conversation.
> Copy this file, fill the placeholders, and paste it with the
> [agent prompt wrapper](agent-prompt.md).

```markdown
# Project: <project name>

## Goal
- One sentence: what problem does this project solve?
- End user / primary use case.

## Tech Stack
- Frontend:
- Backend:
- Database:
- Infra / Deploy:
- Key Libraries:

## Architecture Overview
- Main components and how they relate.
- Key modules/folders and each one's responsibility.

## Current State
- What is actually implemented?
- What is in progress?

## Constraints (very important)
- What is forbidden?
- Any performance / security / dependency limits?
- Hardware limits (VRAM, RAM, CPU)?

## Conventions
- Code style / naming.
- Git workflow.
- Environment variables.

## Dependencies & APIs
- Internal modules we rely on.
- External APIs and their usage terms.

## Known Issues
- Known problems or weak spots right now.
```
