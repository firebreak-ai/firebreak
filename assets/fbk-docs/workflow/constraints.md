# Rules the runtime enforces on reviewer responses

A reviewer session returns a structured response. The runtime checks that response
with deterministic rules: the properties it must carry, the size of each string and
list, the shape of the context declaration, the shape of an investigation request,
what makes an external check runnable, and what a verifier's verdict does. A rule the
reviewer is held to is a rule the reviewer is told, and the telling is generated, never
hand-written into prompt prose.

## One registry, one block, two tests

Every enforced rule is registered exactly once in
`fbk-scripts/fbk/workflow/constraints.py`. An entry names the rule (a stable kebab-case
id), the session kinds it applies to, a grouping key used only for rendering, the
validator function that rejects a response breaking it, and its sentence. Sentences
whose numbers come from configuration or a schema (length budgets, the required file
list, the session time limit and turn ceiling, investigation attempt and second
budgets, the response property names) are callables that read the same source the
validator reads, so the prompt and the check cannot drift.

The registry renders into a `rules` block: a one-line preamble, then groups of
`{id, rule}` entries. A phase reviewer finds it in the review packet directly after
`required_files`. Sessions assembled elsewhere carry the same block as JSON under a
`rules:` line: council turns, closing stances and the final session, and the second
reader's assessor (which restate their own rules in place of the packet's, because they
answer a different schema), the
contradiction-repair verifier, the remediation verifier, and standalone review-round
contributors. Prompt prose keeps only guidance: how to review, what counts as a
blocker, how to classify a supporting file.

The session kinds are `review`, `council-member`, `council-turn`, `council-stance`,
`council-final`, `adjudication`, `contributor`, `repair-verifier`, and `remediation-verifier`. An investigation request
is a response of a managed session rather than a session, so its rules render in every
managed kind and never in a standalone one.

Two tests in `fbk-scripts/tests/test_workflow_constraints.py` hold the registry to the
code:

- **Every entry is stated.** For each session kind the test drives the real assembler
  and asserts that every applicable entry's rendered sentence appears in the prompt, and
  that rendered numbers follow a non-default configuration.
- **Every rejection site is registered.** Each `raise` inside a validator function
  carries a `# constraint: <id>` comment on the same or the preceding line; the test
  parses those functions and checks that every marker names a registry entry and that
  every entry is named at a site in the validator it claims. A rejection that judges
  something other than model output (a configuration error, a host process failure, a
  transport bound) is marked `# constraint: n/a <reason>`, and the test pins how many of
  those exist so a new one is a review question.

An entry may record `enforced_by: None` with a note when the runtime states a rule it
cannot enforce; the sentence then says what actually happens instead of claiming a
rejection.

## Adding a rule

1. Add the check in the validator, with `# constraint: <new-id>` on the line before the
   `raise`.
2. Add one entry to the registry: id, session kinds, group, the validator's dotted
   reference, and the sentence (a callable if it carries a number the validator reads
   from configuration or a schema).
3. Run the tests. The first fails until the sentence appears in every applicable prompt;
   the second fails until the marker and the entry agree.

Do not add the sentence to prompt prose. Host-side JSON schema limits are covered by the
schema walker that renders the length-budget sentence, not by markers.
