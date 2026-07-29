## Search before authoring

Before writing a new function or module, search the codebase for existing implementations of the same concern. Use `grep` for symbol names, function signatures, or domain terms; use `glob` to find files matching the conceptual area. When an existing implementation covers the concern, extend or call it rather than authoring a parallel implementation.

When the search returns ambiguous results — multiple candidates that partially match — read each candidate before deciding. The first match is not necessarily the authoritative implementation.

## Verify external imports exist

When a new external dependency is introduced (an import statement referencing a package not currently in the project), verify the package exists in the project's package manifest (`package.json`, `requirements.txt`, `go.mod`, `Cargo.toml`, or equivalent) or in the registry the project resolves from. Hallucinated package names cause build failures and expose the project to typosquatting.

When the package is not yet declared, add the dependency declaration as part of the same change. Do not add an import line and assume the package is installed.

When code will assert on or branch against a dependency's specific behavior (an error type, a returned value's format, an edge-case result), read that behavior directly in the dependency's source in the module cache or vendor directory before writing the assertion or branch. Do not rely on recollection of how the dependency behaves — dependency internals change between versions, and recollection can be wrong even when the package identity is correct.

## Read callers before changing unfamiliar code

When the planned change modifies a function, struct, or symbol the agent has not previously read in this session, read the symbol's definition and grep for its call sites before proposing the change. Each caller may pass a different combination of arguments or rely on a different invariant; a change that satisfies one caller's expectations may break another.

When the symbol has more than three call sites, read at least the call sites that pass distinct argument shapes. The same shape repeated across many callers needs only one read.
