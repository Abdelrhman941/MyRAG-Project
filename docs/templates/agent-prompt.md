# Template — Agent Prompt Wrapper

> Paste this wrapper around your task whenever you start an AI coding session.
> The rule: **the agent doesn't work on an "idea" — it works on a written Scope.**

```text
Context:
read /AGENTS.md + docs/sdd.md

Task:
<paste the current stage file from docs/progress/stage-XX-*.md
 or a filled docs/templates/feature-spec.md>

Rules:
1. Stick to the written Scope only — nothing more.
2. If anything is missing or ambiguous, ask before writing code.
3. Before implementing, summarize your understanding in 3–5 bullet points.
4. If you believe something outside the Scope is necessary, flag it — do not do it yourself.
5. When done: run the verification commands, write docs/progress/stage-XX-summary.md,
   and tick the roadmap checkboxes. Then STOP — do not start the next stage.
```

## Why this works (SDD — Spec-Driven Development)

- The spec is the **Single Source of Truth**; code is a projection of it.
- Changing a feature = editing the spec → re-implementing from it.
- This **eliminates hallucinations**, **maintains context** across sessions, and
  keeps velocity high: you review and verify, the agent implements.
