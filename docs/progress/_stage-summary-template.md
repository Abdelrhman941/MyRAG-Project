# Template — Stage Summary

> The agent **must** fill this after completing a stage and save it as
> `docs/progress/stage-XX-summary.md`, then tick the roadmap checkboxes.

```markdown
# Stage XX Summary — <stage name>

Date: <YYYY-MM-DD>

## What was built
- Bullet list of what now exists (files, endpoints, behaviors).

## Decisions made
- Any choice the spec left open, and why it was resolved this way.

## Deviations from spec
- Anything implemented differently from the stage file, and why.
- "None" if exact.

## Verification evidence
- Paste actual command output: ruff, manual verification steps, smoke run.
- No output = not verified.

## Out-of-scope items flagged
- Things noticed but NOT done (per AGENTS.md §13).

## Follow-ups for later stages
- Suggestions that belong to future stages (add them to the roadmap, don't implement).

## Files touched
- path/to/file — what changed
```
