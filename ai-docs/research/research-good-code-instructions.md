# Code Authoring Instructions

Apply when writing or modifying code. Justifications and citations: `research-good-code.md`.

## Investigate before authoring

- Search the codebase for existing implementations of the concern before writing new code.
- Verify imports refer to packages that exist; LLMs hallucinate package names.
- Reference existing patterns by file path when authoring code in the same style.

## Limit scope of changes

- Modify only code your task requires; leave unrelated cruft alone.
- When a change touches multiple unrelated places, pause and surface the coupling to the user before continuing.
- When the planned change is hard, refactor the surrounding structure first, then make the now-easy change.

## Verify before reporting done

- Run the project's verification commands (tests, type check, lint, manual run) before claiming a task complete.
- If verification cannot be run, halt and surface what is missing rather than reporting success.
- When a fix masks a symptom rather than removing it, name the root cause in the change description.

## Decompose for cohesion, not size

- Extract a function when it earns a meaningful name or groups cohesive logic.
- Do not extract a function solely to reduce line count.
- Wait until the same logic appears in two places before extracting a shared abstraction.

## Test discipline

- Write tests for code you author.
- Prefer multiple small commits over one large commit when changes are independent.
- Use real collaborators in tests where the test still runs fast; introduce mocks only when a real collaborator is too slow or non-deterministic.

## Document intent, not mechanics

- Add a comment when behavior would surprise a future reader, when a constraint is non-obvious, or when a workaround addresses a specific bug.
- Do not write comments that paraphrase the code.

## Halt on security patterns

- Halt and warn the user when a change combines untrusted input, private data, and external communication (lethal trifecta).
- Halt and warn the user when a change disables, weakens, or bypasses an authentication, authorization, or input-validation control.

## AI context hygiene

- Clear context when switching to an unrelated task.
- Author a plan or specification before code for non-trivial changes; tight bug fixes may go direct.
