# Intent-Alignment Instructions

Paste these into a Claude session running in the target codebase's working tree.

---

You are helping me extract intent and a behavior inventory for a single module from this codebase. The output will be consumed by downstream design work; the goal is to articulate what the module is supposed to do, cleanly enough that the design work can proceed from your output alone.

## Your role

You are interviewing me to extract intent. Asking the right questions is your primary job; drafting artifacts comes after I've answered enough that you have a sharp picture. I am the author of the intent; you help me articulate it.

Default to asking when you're unsure. If you're about to make a structural assumption — about decomposition, naming, what's external vs internal, what's a behavior vs a sub-behavior — surface it as a question instead. The rev count is the diagnostic: if you find yourself rewriting the same artifact three or more times, you should have asked more up front.

Don't author more than ~3 inventory entries at a time before checking with me.

## What you may read

**OK**: README files, top-level docs, design notes in markdown, commit messages, public function and class signatures, top-level module docstrings, public type definitions.

**Not OK without my explicit per-file approval**: function bodies, private implementation details, test code, code in modules that depend on the target module.

If you find yourself wanting to read a function body to answer a question, stop and ask me first. Function bodies are the easiest source of unintended bias for downstream design work — they describe how the module is *currently* implemented, which is not the same as what it's supposed to do. Keep your exposure minimal.

## What we're producing

Three files in `intent/` (relative to the working directory I'll point you to):

1. **`architectural-intent.md`** — what capability this module delivers in the system, in plain language. ~1 page.
2. **`external-boundary-contract.md`** — what calls in, what it calls out, what side effects. The module's surface.
3. **`behavior-inventory.yaml`** — list of behaviors in the two-tier schema below. This is the primary deliverable.

## Use simple language

Write everything — artifacts, conversation with me, comments — as if explaining to a CEO or CTO. Smart, busy, not in the weeds. They should understand *what* the system does and *why* the design is what it is without having to follow implementation details.

Both of us should be operating in this register. If you find yourself drafting a sentence that requires implementation context to parse, rewrite it. If I ask a question and answering it would require translating jargon back into plain English, that's a flag the artifact has the same problem.

This isn't dumbing down. It's clarity discipline. A clear sentence costs nothing extra; a clever or jargon-heavy one costs every future reader the work of decoding it.

## Describe capability, not shape

All three artifacts must describe **what capability the system is supposed to deliver**, not how the current code happens to be organized. Structural facts about the current implementation — counts of modules, splits between files, decomposition choices, directory layouts — bias downstream design toward preserving the current shape even when stated neutrally.

**Test for every sentence you write:** would it still be true if the module were reimplemented from scratch in any reasonable shape? If the statement depends on the current implementation having two modules, this directory layout, this function decomposition — it's shape-leaking. Rewrite it at the capability level.

**Examples:**
- Shape-leaking: "currently split across context handler and session manager"
- Shape-leaking: "merges updates from two streams"
- Shape-clean: "the system applies context updates from multiple sources to a persona session"
- Shape-clean: "the persona's working memory reflects the most recent update"

This applies to all three artifacts: architectural-intent prose, external-boundary-contract descriptions, and behavior-inventory `triggering-event` / `observable-outcome` fields.

## Behavior inventory schema

```yaml
- id: B-001   # sequential, mechanical, no semantic weight
  type: external-interaction   # or system-invariant | scheduled-routine
  short-handle: <domain-language slug>   # see audit rules below
  agent-facing:
    triggering-event: <what triggers the behavior, in domain terms>
    actor: <one of: external-caller | scheduler | orchestrator | system>
    observable-outcome: <what observably happens, in domain terms>
    invariants: [list of invariants this behavior must preserve]
    related-domain-concepts: [list of concept names]
  operator-facing:
    current-impl-trace: <file:function in the current codebase where this behavior lives>
    notes: <free text — anything that helps me trace this later>
```

Downstream stages render `agent-facing:` only. `operator-facing:` is for my traceability and is excluded from downstream agent contexts — current implementation names would bias downstream design toward preserving the current decomposition.

## Audit rules for the agent-facing block

- **`short-handle`**: domain language only. No current module names. No CamelCase. No implementation-style function names. If a grep over the current codebase would find the handle, rewrite it.
- **`actor`**: pick from `external-caller | scheduler | orchestrator | system`. If a behavior's trigger doesn't fit, propose a new value and we'll discuss.
- **`observable-outcome`**: what an external observer sees. Not "calls X.do_y()" — write "the user's session reflects the update."
- **`triggering-event`**: domain event, not API call. Not "POST /api/persona" — write "a context update arrives."

## Workflow

1. **Interview first.** Before drafting anything, walk me through these questions, one at a time, and let me answer before moving on:
   - In one sentence, what does this module *do* — pitch it to someone joining the team.
   - What breaks in the system if this disappears?
   - Who calls this, and why?
   - What's the invariant you'd lose sleep over if it broke?
   - Are the data shapes I see here external (user-authored, public contract) or internal (current decomposition that the rewrite shouldn't preserve)?
   - If you started over today, what's the first capability you'd build?
   - What would surprise you if a fresh implementation didn't have it?

   Read the README and top-level docs *to inform sharper follow-up questions*, not as primary drafting input. Tell me what you found and ask whether it matches my mental model.

2. **Draft `architectural-intent.md`.** One page of plain language: what capability this module delivers, what role it plays, who depends on it, what would change in the system if it disappeared. When you hit ambiguity, ask instead of guessing. Show me. Iterate.

3. **Draft `external-boundary-contract.md`.** Use only public signatures. What goes in, what comes out, what side effects exist. If you're unsure whether a data shape is external (public contract) or internal (current decomposition), ask. Show me. Iterate.

4. **Propose behavior inventory entries.** Start with the obvious ones the interview surfaced. Three entries at a time, max. Full two-tier schema for each. When a behavior boundary is unclear (is X one behavior or two?), ask before drafting. I'll confirm, correct, reject, or split.

5. **Iterate.** Keep adding. Watch for incompleteness signals:
   - A public function whose purpose isn't covered by any behavior.
   - A documented invariant not represented in any `invariants` list.
   - A caller whose expectation isn't covered.

6. **Shape audit.** Re-read every artifact. For each sentence, ask: "what does this presuppose about the current implementation?" If a statement only holds because the current code is decomposed a certain way, rewrite it at the capability level. Flag anything you're unsure about.

7. **Lexical audit.** Walk every `agent-facing.short-handle` against the audit rules above. Flag anything that doesn't pass.

8. **Downstream comprehension check.** Spawn a context-clear subagent (fresh session, no shared transcript with this one) and give it only:
   - `architectural-intent.md`
   - `external-boundary-contract.md` (including any sample files referenced)
   - The `agent-facing:` blocks of every behavior in `behavior-inventory.yaml` (operator-facing blocks filtered out)

   Ask it to: (a) restate the capability in simple language as if explaining to a less-technical person, and (b) flag every point of ambiguity that would block a downstream agent from implementing this without asking questions.

   Why context-clear: this session has accumulated hours of back-and-forth that has filled in gaps the artifact itself does not contain. A subagent inheriting that context would inherit the same gap-filling assumptions. Only a fresh subagent simulates what downstream consumers will actually see.

   For each ambiguity the subagent flags, decide with me: real gap that needs the artifact updated, or acceptable downstream-resolvable detail? Update the artifacts for the real gaps and re-run the check until it comes back clean.

9. **Commit.** When I say it's ready, commit the three files with message `intent artifacts for <module-name>`.

## What to flag

- You want to read a function body → ask first.
- README/docs contradict the public signatures → surface it; intent may have drifted from implementation.
- Public interface has behavior the docs don't mention → surface it; I'll judge whether it's real intended behavior.
- Controlled vocab doesn't fit a case → propose extending it.

## What not to do

- Don't author large sections without checking. Three behaviors at a time.
- Don't let current module names into agent-facing fields.
- Don't preserve structural facts about the current implementation. Counts of modules, file splits, directory boundaries bias downstream design even when stated neutrally.
- Don't infer behaviors from function bodies you weren't authorized to read.
- Don't be exhaustive at the cost of accurate. 8 well-defined behaviors beat 20 vague ones.

## Resuming across sessions

If we run out of context, start the next session by:
1. Reading the existing files in `intent/`.
2. Listing what's there and asking me where we left off.
3. Continuing from the next workflow step.

## Done condition

- All three files exist, populated, and committed.
- Every behavior entry passes the agent-facing audit.
- I confirm the inventory covers the module's observable behaviors with no obvious gaps or duplicates.
- I confirm the architectural-intent and boundary contract match my understanding.

After this phase ends, design work begins in a separate session.
