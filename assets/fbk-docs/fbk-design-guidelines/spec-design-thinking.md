## Behavior identification

Identify the distinct behaviors the feature introduces or modifies. Name each behavior before describing its implementation.

For each behavior, determine whether it is computation (transforms input to output) or orchestration (calls other behaviors and manages their results). Assign computation and orchestration to separate functions.

## Testability as a design input

Evaluate testability while designing the technical approach, not after. For each behavior: can a test import this function and call it directly with known inputs? If not, the design needs to change — either extract the behavior into a callable function, or explain to the user why extraction is impractical and what the testing tradeoff is.

When a behavior is embedded in an untestable context (a large function, a framework lifecycle method, a browser-only code path), propose extraction. Describe the extraction as a pattern: "pure function that returns typed results; caller handles side effects." Require an importable function for each extractable behavior; integration tests supplement but do not replace direct-call testability.

## Side effect separation

For each behavior in the technical approach, state whether it has side effects. If it does, identify which side effects can be moved to the caller and which are inherent to the behavior. See `fbk-design-guidelines/function-design.md` for the implementation-level principle.

## Composition

After identifying individual behaviors, identify how they interact. Ask:
- Which function calls which?
- What data flows between them — what does each caller receive and what does it do with each possible result?
- Does ordering matter? If behavior A must happen before behavior B, state why.
- What happens when a called function produces an error or an unexpected result?

Describe all composition explicitly — which function calls which, what each caller does with each result, and what ordering or error handling applies. Unspecified composition results in inlining.

When the technical approach threads a value from one component to another (a context, a lifecycle signal, a configuration reference), identify the concrete source of that value at the outermost wiring point. State which component creates or obtains the value and passes it inward.

## Shared conventions check

Before finalizing the technical approach, check every shared contract the feature introduces or consumes — a config shape, a constructor signature, a naming scheme, a shared sentinel set, an event registry that other parts of the project also use — against the project's established convention. Find that convention in this order: prefer an authoritative conventions document if one exists; if none exists, infer the convention from the dominant pattern in the existing code; if neither exists, say plainly that you are setting a new convention, so the choice is visible rather than buried. A technical approach can match the feature's own foundational contract perfectly and still reinvent a shared convention that lives in a separate cross-cutting place nobody opened.

If a conventions document and the live code disagree, surface the conflict to the user with a recommendation: name what the document says, note that the code does something different and roughly how widely, recommend which to align to and why, and ask for confirmation. Do not silently pick a side, and do not hand over the raw conflict without a recommendation.

## Abstraction timing

When the technical approach proposes a shared abstraction (a base class, an interface, a generic helper, a parameterized utility) over fewer than two concrete call sites, justify the abstraction explicitly or defer it until the second call site appears. Name the call sites that would consume the abstraction and state what each call site would lose if the logic were inlined instead.

Single-use abstractions encode predictions; wrong predictions block each call site's evolution. Extract abstractions from observed duplication, not from anticipated cases.

## Brownfield considerations

When the feature modifies existing code, read the existing code before designing. Identify behaviors that are currently embedded in monolithic functions. Design toward the target structure, not the current structure — the target location of a behavior is where it should live after implementation, which may require extraction from where it currently lives.

When proposing extraction from existing monolithic code, describe the extraction boundary: what moves out, what stays, what interface connects them. The implementing agent needs this boundary to be precise enough to execute without re-inlining the logic.

## Establishing ground truth before committing the design

When the technical approach depends on how a dependency or external behavior actually works, establish that truth early — before the design is committed — rather than carrying an unverified assumption forward into implementation, where it surfaces as a late, costly failure.

Find the truth the cheapest way that settles the question, and escalate only when a cheaper check leaves it open: read the dependency's own source directly first; if that does not settle it, run a small experiment script that exercises the real behavior; if the behavior is large or statistical, run a proper evaluation against it. Do the cheap end yourself — reading source or running a quick script needs no permission. When establishing the truth would take non-trivial effort, raise it with the user and agree it is worth the cost before sinking significant effort into it.

## Level of detail

Describe design patterns and behavioral contracts. Let the implementing agent determine file paths, function names, and parameter lists unless the user provides them or existing code constrains them. Be precise about *what* each behavior does and *how behaviors relate to each other*.
