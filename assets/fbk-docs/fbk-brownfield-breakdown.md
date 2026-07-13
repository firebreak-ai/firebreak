Search the codebase for related functionality before producing task files. Map each task to specific existing files where possible.

Before a task cites a specific function, method, or constant from another package, open that package's shipped source and confirm the exact name and signature. Confirm the definition sits outside test-only files — a symbol that exists only in a test file is not reachable from another package's production code.

Before a task prescribes a non-trivial query or other engine-specific construct, verify the construct against the actual engine's documented behavior — a construct valid in one engine can be rejected by another.

Each task that modifies existing code must reference files by path. Each task that creates a new file must state why an existing file is not the right location.

When the codebase has an established pattern for the type of work a task describes, include a "follow the pattern in [file/function]" reference.

Do not introduce new dependencies when the project already provides equivalent functionality. Search package manifests and existing imports before specifying new libraries.

If a task would create a function, utility, or abstraction, search for existing equivalents first. Reference the search in the task instructions so the implementing agent inherits the context.
