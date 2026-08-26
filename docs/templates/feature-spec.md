# Template — Feature / Step Spec (SDD)

> Copy this for **every feature**. If a feature is large, split it into steps and
> give each step the same template. The filled spec is the Single Source of Truth
> for that feature — to change behavior later, edit the spec, not the code.

```markdown
# Feature: <feature or step name>

## Goal
- [ ] The final outcome in one sentence.
- [ ] Why are we doing it now?

## Scope (In)
- Only what will be done in this feature/step.

## Out of Scope (most important — prevents scope creep)
- ❌ Will NOT be done:
- ❌ Will NOT be done:
- ❌ Any extra improvements outside scope.

## Inputs
- Data / files / params / API payloads.

## Outputs
- Expected result / response shape / UI change.

## Business Rules
- Validation rules and data checks.
- Edge cases.

## Dependencies
- Modules / APIs / DB tables / environment variables required.

## Error Cases
- If the input is wrong → what happens?
- If a dependency is missing → what happens?
- If the process fails → what happens?

## Implementation Steps
- [ ] Small step 1
- [ ] Small step 2
- [ ] Small step 3

## Manual Verification
- Steps to verify by hand (automated tests are deferred — see AGENTS.md §12).

## Verification / Done When
- [ ] I can run ...
- [ ] The result matches the requirement.
- [ ] Lint/format checks pass.

## Notes / Assumptions
- Any assumptions or clarifications for the agent.
```

## For a large feature — split into steps with the same mini-template

```markdown
## Step 1: <step name>
- Goal:
- In Scope:
- Out of Scope:
- Inputs:
- Outputs:
- Dependencies:
- Manual Verification:
- Done When:
```
