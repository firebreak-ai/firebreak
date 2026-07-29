Load condition: loaded by the breakdown skill when a slice's test-discipline is `cross-cutting`.

## cross-cutting shape

The slice describes behavior that spans multiple existing modules or seams. The implementation already exists across other slices; this shape only validates the seam-level behavior.

**Work-unit structure**: produces seam tests only. No paired impl task.

**Test placement**: tests live at the seams — integration tests, contract tests between modules, or end-to-end tests for the flow. They do not live inside any single module.

**Fixture self-containment**: a seam test's fixtures (for example, a config file) are defined in full within the task that uses them, never assembled by paraphrasing or citing another behavioral task's fixture — a cross-reference can silently omit a section the referencing test needs, caught only by re-checking the fixture field-by-field against the real schema. When several tasks genuinely share one fixture, it lives pinned in the shared-infrastructure task (per the pin-once rule) and each consumer names it exactly; what is banned is deriving a fixture from a sibling behavioral task's description.

**No impl task**: the implementation is distributed across the other slices. The cross-cutting slice does not produce a paired implementation task. The breakdown gate enforces this invariant.

**Hash-locking applies to**: the seam tests produced here, once they pass review.

**Coverage-backfill against existing untouched code also maps here.** When a slice exists only to add tests against code no other slice is changing — pure coverage-backfill — declare it as `cross-cutting`. Same structural shape: tests-only, no paired impl task. The implementation already exists; this slice exists to make its behavior testable.
