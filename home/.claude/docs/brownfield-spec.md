Search the codebase for existing code that overlaps with the proposed feature before writing the technical approach.

Identify established patterns, abstractions, and conventions that the feature must follow. Reference specific files or modules.

In the technical approach, distinguish what is new from what extends or modifies existing code.

If the feature replaces existing functionality, include removal or migration of the old path in scope. Partial replacement — new code on the new pattern, old code left on the old pattern — is a defect, not a follow-up.

If the feature duplicates functionality that already exists, stop and reconsider the approach. Prefer extending existing abstractions over introducing parallel ones.
