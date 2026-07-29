Search the codebase for existing code that overlaps with the proposed feature before writing the technical approach.

Identify established patterns, abstractions, and conventions that the feature must follow. Reference specific files or modules.

For every write, read, or interface call the technical approach specifies against existing code, verify its exact mechanics in the shipped code itself, not in a design page or diagnosis document. Confirm three things. First, whether the target state can already exist — an insert against a table another process may have already populated needs upsert or existence-check semantics, not a plain insert. Second, whether the accessor the technical approach names actually exists on the interface the caller holds — a caller with a wrapped interface cannot reach raw storage access the design assumed. Third, whether a new error or sentinel value collides with an existing one on the same handling path — a new value with the same name or purpose as an existing one needs an explicit reuse or translation, not a fresh declaration.

In the technical approach, distinguish what is new from what extends or modifies existing code.

Before declaring which modules the feature touches, grep for every caller and every interface-implementer — including test doubles — of any function or interface whose contract this feature changes. A caller or implementer outside the modules already named in the PRD or design is still a touched module and needs its own entry in the technical approach.

If the feature replaces existing functionality, include removal or migration of the old path in scope. Partial replacement — new code on the new pattern, old code left on the old pattern — is a defect, not a follow-up.

If the feature duplicates functionality that already exists, stop and reconsider the approach. Prefer extending existing abstractions over introducing parallel ones.
