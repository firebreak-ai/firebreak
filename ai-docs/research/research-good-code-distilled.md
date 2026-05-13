# Good Code Rules (distilled from research-good-code.md)

Goal: code works, code changes cheap.

## Anchor

- Change cost dominates. Optimize for it.
- Coupling = change tax. Cut it.
- Locality = good. One change → one place.
- Code is read more than written. Design for the reader.

## Do

- Small reversible changes. Continuous.
- Make the change easy, then make the easy change.
- Refactor where code changes. Leave stable cruft alone.
- Verify before ship. Can't verify → don't ship.
- Slow feedback loop = slow work. Fix the loop first.
- Address root cause, not symptom.
- Code review = ship gate.

## AI-only

- Long context = lost recall. Keep context minimum-sufficient.
- Plan first. Spec first. Code last.
- Few tools, sharp docs. Tools are part of the prompt.
- Necessity Test every persistent-context line.
- Grep before write. No parallel implementations.
- Verify imports exist. LLMs hallucinate package names.
- Untrusted input + private data + external comms = exfiltration risk (lethal trifecta).
- Evals from observed errors, not imagined ones.
- Many users on an API → all observable behavior is contract (Hyrum).

## Don't dictate (contested) — anchor on outcome instead

- Function size → extract for cohesion and naming, not line count.
- Polymorphism over conditionals → cost is real; choose deliberately.
- Fine-grained encapsulation → encapsulate what changes; over-encapsulation hides state.
- Strict test-first → real signal is tests-at-all + small batches, not ritual order.
- DRY at first repeat → wait for second instance, dedup knowledge not shape.
- "Comments are failure" → intent and rationale are load-bearing for AI.

## Empirics override folk

- Tiny functions = more bugs (U-shape, Hatton 1997).
- Cyclomatic complexity tracks size. Pick one.
- Heavyweight approval gates = worse stability (DORA).
- Mock-heavy tests = ossified, brittle (Google retreat).
- Speed vs. quality tradeoff = low-performer artifact, not law.
- Code review's real value = comprehension > defect detection (Bacchelli & Bird).

## Source

Full citations and reasoning: `research-good-code.md`.
