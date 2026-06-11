# SDL Foundation Hygiene — Project Overview

We learned a lot during the realmind remediation cycle about what makes Firebreak produce cleaner code. Most of those lessons aren't specific to fixing broken codebases — they're about how to do good work in any codebase. This project takes the things that worked in the realmind cycle and folds them into the regular Firebreak workflow so every project benefits, not just remediation work.

This is the parent spec. Each piece of work below gets its own child spec under `ai-docs/sdl-foundation-hygiene/<name>/`. The remediation flow project (for codebases already past the slop-compounding threshold) lives separately at `ai-docs/remediation-flow/`.

Source material this consolidates:
- `.firebreak-wiki/wiki/syntheses/realmind-validation-experiment-lessons.md` — the lessons writeup
- `.firebreak-wiki/wiki/syntheses/validation-experiment-firebreak-postmortem.md` — the three things to audit Firebreak against
- `.firebreak-wiki/wiki/syntheses/intent-alignment-review-pattern.md` — the fresh-eyes review pattern
- `.firebreak-wiki/wiki/syntheses/architectural-review-meeting-pattern.md` — the design-review interaction style
- `ai-docs/remediation-flow/validation-experiment/intent-alignment-instructions.md` — the prompt that worked for intent alignment
- `ai-docs/remediation-flow/validation-experiment/rearchitecture-instructions.md` — the prompt that worked for design review
- Matt Pocock's practice of pulling the top five quality issues at the end of a review cycle

---

## 1. Vision

The realmind cycle produced code that was categorically cleaner than what the same Firebreak SDL would have produced without the firebreak. The lessons that fell out of that experience apply to any project, not just remediation work. Cleaner code is easier to keep clean — clean substrate begets clean additions, and the techniques that produced the clean substrate are the same techniques that maintain it.

The lessons fall into two groups. **How we talk** — to ourselves, to our agents, and between operator and agent during sessions: keep the language plain enough that a less-technical person could follow along, and talk about things by what they are rather than by short codes. **What we do during the work** — pause before spec'ing to make sure the operator and agent agree on what's being built, run design-heavy spec work like a real design-review meeting where the agent presents and defends its choices, and after the bug-finding pass in code review, look at the code with fresh eyes and pick out the top five cleanup opportunities — then fix the most important one before closing the cycle.

This project doesn't invent new practices. It generalizes ones we've already seen work.

---

## 2. Architecture

Four pieces of work, all additive to the existing Firebreak flow. None of them replaces an existing stage.

The Firebreak flow today, with the additions in **bold**:

```
(operator describes a feature)
     │
     ▼
**Intent alignment** ◄── NEW. Pause where operator and agent agree on
     │                    what's being built. Three artifacts: what we
     │                    want at the architectural level, how it talks
     │                    to the outside world, and a list of things
     │                    the system does. A fresh agent then reads
     │                    those and flags anything unclear; we fix it
     │                    and re-run until it comes back clean.
     ▼
/fbk-spec ◄── MODIFIED in two ways.
     │       (a) The asset authoring rules it follows pick up the
     │           realmind lessons on plain language, descriptions over
     │           short codes, loose coupling in design, and the
     │           simplest design that works.
     │       (b) New optional **design-review meeting** interaction
     │           mode for design-heavy specs: operator plays senior
     │           reviewer, agent plays presenter who has to defend
     │           every significant choice.
     ▼
/fbk-spec-review ◄── Unchanged structurally. Benefits from cleaner
     │                inputs above.
     ▼
/fbk-breakdown ◄── Unchanged.
     │
     ▼
/fbk-implement ◄── Unchanged.
     │
     ▼
/fbk-code-review ◄── MODIFIED. After the existing bug-finding pass,
     │                run a **top-five quality scan**: pick the five
     │                biggest cleanup opportunities (not bugs — design
     │                and clarity issues), rank them, fix the most
     │                important one as part of this cycle, note the
     │                other four for later.
     ▼
(retrospective)
```

What's new and what's reused:

| Piece | Status | Existing surface it touches |
|---|---|---|
| Intent alignment | NEW | None — lifts the prompts that worked in realmind |
| Fresh-eyes review of intent artifacts | NEW | Parallel in shape to `/fbk-spec-review` |
| Asset authoring rules update | MODIFIED | `assets/fbk-docs/fbk-context-assets.md` and `assets/fbk-docs/fbk-design-guidelines/` |
| Spec-authoring discipline update | MODIFIED | `/fbk-spec` skill and its referenced spec-authoring guide |
| Design-review meeting mode | MODIFIED | `/fbk-spec` skill (additive interaction mode) |
| Top-five quality scan | MODIFIED | `/fbk-code-review` skill |
| Targeted rewrites of skills below the new threshold | MODIFIED | Whichever existing skills the audit flags |

Where the pieces have to agree on conventions:
- The fresh-eyes review of intent artifacts loops until it comes back clean — same gate-and-iterate shape as `/fbk-spec-review`.
- The plain-language and descriptions-over-short-codes rules apply everywhere the agent talks to humans: prose, summaries, review dialogue. Short codes (like `AC-01`, behavior IDs) stay in artifacts for traceability.
- Touched assets are edited at the installed paths convention, not the source-repo `assets/` paths.

Where artifacts live:
- Intent artifacts for general SDL features: `ai-docs/<feature-name>/intent/` with three files (what we want at the architectural level, how it talks to the outside world, a list of things the system does).
- The top-five quality scan output: `ai-docs/<feature-name>/code-quality-scan.md`, with the five issues ranked and the chosen-for-fix one called out.

---

## 3. Technology decisions

**No new tools or runtime.** All changes are to Markdown files — skill prompts, agent definitions, referenced docs. The lessons are about discipline and interaction, not infrastructure.

**Lift the realmind prompts.** The intent-alignment and design-review prompts from the realmind cycle worked. Use them, adapting only the parts that referred to the firebreak worktree or rearchitecture artifacts. Don't rewrite what worked.

**Update existing rules rather than create parallel ones.** The asset authoring rules already cover some of the same ground (the existing "Objectives over Procedural Steps" rule, for example, is closely related to how realmind talked about output quality). Where the existing rules already cover something, don't duplicate — extend or clarify the existing rule instead.

**The top-five quality scan is not a gate.** A cycle can close with the top-five fix deferred and recorded, the same way open questions in a spec can be deferred with rationale. Making it a gate would create pressure to under-report; leaving it discretionary captures the practice's value without the gating overhead.

**The realmind lessons apply to greenfield and brownfield work the same way.** Cleaner code is easier to keep clean either way; the techniques don't depend on whether you're starting fresh or iterating. We don't write greenfield-only or brownfield-only versions of any of the four pieces.

---

## 4. Feature map

Four pieces, ordered by dependency. The first lays the foundation; the other three each pick up one of the realmind interaction lessons.

### Update the asset authoring rules and audit existing skills

What it does: take what we learned about how to write clear instructions to ourselves and our agents, and fold it into the existing asset authoring rules (`fbk-context-assets.md` and the design guidelines docs). Then walk every existing skill and its referenced docs, score each one against the updated rules, and fix any that fall short.

What goes into the updated rules:
- Plain language — write so a less-technical person could follow what's going on. Avoid jargon where a description would do.
- Descriptions over short codes in dialogue — "the input validation requirement" instead of "AC-01" when talking with the operator or producing prose summaries. Short codes stay in artifacts for traceability.
- Push toward loose coupling in spec authoring — the spec-authoring skill should actively prefer designs with looser coupling, not just allow them.
- Prefer the simplest design that works — when multiple designs are possible, the spec-authoring skill should pick the least complex one that still does the job.

What the audit produces: a per-skill list of "leave alone" (already aligned), "small tweak" (one or two prompt edits), or "real rewrite needed" (the prompt needs significant work). Then the rewrites get done.

What we know we'll be touching: at least `/fbk-spec` (loose coupling and KISS go here) and the asset authoring docs themselves. Other skills may or may not need rewrites depending on what the audit finds.

When it's done:
- The asset authoring rules contain plain-language and descriptions-over-short-codes guidance.
- The spec-authoring skill or its referenced guide actively pushes toward loose coupling and the simplest workable design.
- Every existing skill has been scored; rewrites are in for any that scored "real rewrite needed."

What could go wrong:
- Audit surfaces too many rewrites to do in this cycle. Prioritize by which skills get used most; defer the rest with notes.
- A rule we add doesn't survive contact with real authoring. Pull it, write down why it didn't work.

### Add intent alignment before /fbk-spec

What it does: introduces a pause before `/fbk-spec` starts. In that pause, operator and agent agree on three things: what we want at the architectural level (one to two paragraphs), how this thing talks to the outside world (its external interface), and a list of things the system does. Then a separate fresh agent — one that hasn't seen any of the conversation — reads those three artifacts and flags anything ambiguous or unclear. We close those gaps and re-run the fresh agent until it comes back clean.

The prompts come from realmind — `ai-docs/remediation-flow/validation-experiment/intent-alignment-instructions.md` — adapted to remove the remediation-specific parts.

The skill shape (standalone skill or a phase of `/fbk-spec`) is a child-spec decision.

When it's done:
- Operator can run intent alignment on a new feature and get three useful artifacts.
- Fresh-eyes review produces a list of ambiguities with severity.
- The loop closes in two iterations or fewer on a representative test feature.
- The lifted prompts pass the updated asset authoring rules.

What could go wrong:
- The realmind prompts don't generalize cleanly — the precision that made them work was tied to remediation specifics. If so, keep two variants: one for remediation, one for general SDL.

### Add the design-review meeting interaction mode

What it does: gives `/fbk-spec` a mode where, for design-heavy specs, the conversation runs like a real design-review meeting. Operator plays senior reviewer. Agent plays presenter who has to justify each significant design choice. Operator asks "what would force a redesign?" and "what tradeoff did you make here?" The agent answers or changes its mind.

The prompts come from realmind — `ai-docs/remediation-flow/validation-experiment/rearchitecture-instructions.md` — adapted to the general SDL.

Where the mode lives (new skill, mode inside `/fbk-spec`, operator-invocable flag) is a child-spec decision. What "design-heavy" means and how the mode gets triggered is also a child-spec decision.

When it's done:
- The mode is reachable for an operator who wants it.
- On a representative design-heavy spec trial, the agent surfaces and defends at least three significant design choices that would otherwise have gone undefended.
- The conversation reads like a meeting (defense and tradeoff articulation), not like Q&A.

What could go wrong:
- The trigger condition is too unreliable to gate automatically — fall back to operator-invoked only.

### Add the top-five quality scan to /fbk-code-review

What it does: after the bug-finding pass in `/fbk-code-review`, the skill takes another pass over the code looking for cleanup opportunities — design, maintainability, clarity issues. It surfaces the top five, ranks them, and picks the most important one to fix as part of this cycle. The chosen fix becomes a normal task in the post-review fix wave. The other four get recorded as quality work to consider later.

The framing is opportunity-shaped, not failure-shaped. The five-item cap forces prioritization; the rank-and-fix-one pattern ensures the practice produces quality improvements every cycle without unbounded scope creep.

When it's done:
- `/fbk-code-review` produces a `code-quality-scan.md` artifact with exactly five ranked issues.
- The ranking is reproducible — two reviewers running the same logic on the same code produce comparable orderings.
- The top-ranked fix lands as a task and gets verified before the cycle closes.

What could go wrong:
- Top-five framing produces over-reporting (the cycle surfaces five issues even when nothing significant is wrong). Reduce to top-three, or switch to a quality-floor model where the cycle reports any issues above a threshold (could be zero).
- The top-ranked fix is too large for the cycle. Defer with rationale; log it for the next cycle.

### Order

```
Update asset authoring rules + audit
                │
       ┌────────┼────────┐
       ▼        ▼        ▼
   Intent    Design   Top-five
  alignment  review   quality scan
              mode
```

The asset authoring update lands first because the lifted realmind prompts in the other three pieces need to score clean against the updated rules. After that, the other three may run in parallel.

---

## 5. Cross-cutting concerns

**The updated asset authoring rules are the spine.** All four pieces tie back to them. The first piece writes them; the other three carry assets that have to satisfy them.

**Same lessons, greenfield or brownfield.** Nothing about the realmind techniques depends on whether the codebase is new or being iterated. We don't write separate versions. The same intent-alignment phase, the same design-review mode, the same top-five quality scan apply to any feature in any codebase.

**Backward compatibility.** We don't bulk-rewrite working assets just because they would score below the updated rules. The audit's rewrite scope is bounded to assets actively used by the SDL. The new rules apply going forward and to any asset we touch.

**Glossary.** New terms introduced by this project get entries in `GLOSSARY.md`.

**Wiki backlinks.** Child specs reference the firebreak wiki syntheses they lift from; the wiki pages get backlinks pointing to the implementing child specs.

**Sequencing with the remediation flow project.** This project doesn't interfere with the remediation flow work (which is hypothesis-gated past its validation experiment). It does touch some of the same skills (`/fbk-spec`, `/fbk-code-review`); coordinate by finishing the asset authoring update before any remediation-flow feature past the validation experiment starts, so the lifted prompts land in a clean substrate.

---

## 6. Open questions

- **Intent alignment shape.** Is it a separate skill, a pre-phase of `/fbk-spec`, or an operator-invocable mode? Each shape has implications for how downstream skills consume the intent artifacts. Resolve in the intent-alignment child spec.
- **Design-review meeting host and trigger.** Where the mode lives (new skill, mode inside an existing skill, flag) and what triggers it (a tier check, an explicit operator flag, both) — resolve in the design-review-mode child spec.
- **Spec redundancy implication.** The realmind work surfaced a broader finding: intent and design artifacts may cover most of what `/fbk-spec` produces, even in greenfield. That's a separate question with its own project, but it's directly implied by installing intent alignment in the general SDL. Keep deferred to a separate project, or pull into this project's scope? Resolve by user decision before the asset-authoring child spec begins.
- **Priority ranking for the top-five quality scan.** Pocock describes the practice but the operative ranking rubric (severity? blast radius? frequency of pattern? compounding risk?) needs a definition for the Firebreak context. Resolve in the top-five quality scan child spec.
- **Where lifted prompts live.** Inside the skill SKILL.md, or as a referenced `fbk-docs/` doc the skill points to? Existing Firebreak pattern favors the referenced doc when the prompt is substantial. Resolve in the intent-alignment and design-review-mode child specs.
- **Re-audit cadence.** The audit walks every existing skill once. Should there be a periodic re-audit to catch drift, or is this a one-shot exercise? Resolve by user decision before the asset-authoring child spec begins.
