Search the codebase for related functionality before producing task files. Map each task to specific existing files where possible.

Each task that modifies existing code must reference files by path. Each task that creates a new file must state why an existing file is not the right location.

When the codebase has an established pattern for the type of work a task describes, include a "follow the pattern in [file/function]" reference.

Do not introduce new dependencies when the project already provides equivalent functionality. Search package manifests and existing imports before specifying new libraries.

If a task would create a function, utility, or abstraction, search for existing equivalents first. Reference the search in the task instructions so the implementing agent inherits the context.
