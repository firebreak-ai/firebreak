# Cross-Model Review Guide

This guide teaches the agent how to compose and run a cross-model review request.
A cross-model review sends the target to an external model (such as GPT via Codex)
for a cold read using Firebreak's review criteria. The output is **candidate findings**,
not verified findings — they feed into the agent's own judgment, not directly into
the report.

---

## (a) Lens mapping

The review type determines which lens to use as the criteria reference. Only two
review types are in scope for v1:

| Target kind | Lens file | Report slug |
|---|---|---|
| Written artifact (PRD, spec, design, or breakdown) | `assets/fbk-docs/fbk-review-lenses/fresh-eyes-lens.md` | `fresh-eyes` |
| Code change (diff or implementation) | `assets/fbk-docs/fbk-review-lenses/code-lens.md` | `code-review` |

The lens is a **criteria reference**, not a script for Codex to follow. The agent
reads the lens to extract the detection targets and severity vocabulary, then writes
a prompt in plain language that conveys those criteria to the external model.

A cross-model code review is a **lighter second opinion** grounded in the code
lens's criteria — not a reproduction of the internal code-review pipeline. The
external model does not run the full detection passes, challenger loop, or
structured sighting format. It gives a cold read against the same behavioral and
structural criteria.

Other review types are out of v1 scope.

---

## (b) Gathering the target

**How the target reaches the model.** The runner passes only the prompt to the
external model, and the model runs sandboxed **read-only under the project root**.
So it can read a file referenced by a path *inside the project root*, but it cannot
read anything outside it (a `/tmp` path is invisible to it). The reliable rule: put
the target's **content inline in the prompt**. Referencing a project-root path also
works for a document, but inlining always works and avoids the sandbox trap.

**Written artifacts**: inline the document text into the prompt (or, if the file is
under the project root, reference its path). Include any source-of-truth context
files the lens calls for (shared interface definitions, convention documents) as
supplemental reading — label them as comparison anchors, not authoring notes.

**Code changes**: produce the diff and **inline the diff text into the prompt** —
do not write it to `/tmp` and pass a path, because the model's sandbox cannot read
`/tmp`. A diff lives outside the repo, so inlining is the only option:

```
git diff <base>..<head>
```

Embed the output under a clear "diff" heading in the prompt. Including source-of-truth
context (the active spec's acceptance criteria, the relevant design section) alongside
the diff is a judgment call — include it when the diff's intent is not self-evident
from the code alone.

---

## (c) Prompt template

The prompt the agent writes to the external model must contain four elements, in
this order:

**1. Cold-reviewer stance** (inline, not a file reference)

> You are a cold reviewer with no prior context on this project. You have not seen
> the authoring history, the internal review, or any prior drafts. Your job is to
> read the target and surface what a careful engineer would notice.

**2. Criteria drawn from the lens in plain language**

Translate the lens's detection targets into plain instructions. Use the lens's own
severity words without redefining them.

For a **fresh-eyes review**:

> Look for: contradictions between sections, places where a stated guarantee
> conflicts with the described behavior, unstated assumptions a reader could
> reasonably miss, missing constraints the described behavior clearly requires,
> and phrases that two implementers could read differently.
>
> Group observations under three headings: Critical, Substantive, Minor.
> — Critical: a flaw that would cause the artifact to fail its stated purpose.
> — Substantive: a real problem that degrades quality but does not make the artifact
>   entirely wrong.
> — Minor: a wording, consistency, or clarity issue with no behavioral consequence.

For a **code review**:

> Look for: behavior that diverges from the stated spec or evident intent, AI failure
> modes (hallucinated logic, over-trusting inputs, missing error handling), security
> issues (injection, trust-boundary violations, improper credential handling), and
> structural problems that make the code harder to maintain correctly.
>
> Use these types: behavioral (incorrect or missing behavior), structural (organization
> that makes future defects more likely), test-integrity (tests that would not catch
> the regression they claim to cover), fragile (correct now but plausible to break
> with a nearby change).
>
> Use these severities: critical (observable under realistic inputs, no configuration
> change required), major (reachable under plausible production conditions), minor
> (narrow or unlikely impact), info (observation only).

**3. Target and any context**

Provide the target **content inline** — the document text or the diff — followed by
any supplemental context labeled as reference material. Do not rely on a `/tmp` path:
the model can only read files under the project root, so a path outside it is invisible.

**4. Request for candidate findings**

> Return concise candidate findings. For each finding, state: the concern (what you
> noticed), why it matters (what could go wrong), where it is (section, line range,
> or function name), and your confidence (high / medium / low). Do not produce a
> formal report — bullet points are fine.

---

## (d) Config-read and skip check

Before composing the prompt or invoking the runner, check whether the project has
opted in:

```
python3 "$HOME"/.claude/fbk-scripts/fbk.py cross-review --check-opt-in --project-root <root>
```

- **`status: skipped`** (block absent or `enabled` not true): skip the cross-model review
  entirely. Emit the skipped outcome (see section e) and stop. Do not invoke the runner.
- **`status: failed`** (e.g. a malformed config block): the opt-in check itself failed.
  Relay the `cause` field (see section e) and stop. Do not invoke the runner.
- **`status: success`** (opted in): the runner reads the model and effort settings from
  config and uses them when calling the external model — do not hard-code a model name in
  the prompt. Proceed to gather the target.

Once the target is gathered and the prompt written, invoke the runner:

```
python3 "$HOME"/.claude/fbk-scripts/fbk.py cross-review --prompt-file <p> --review-type <slug> --report-dir <dir> --project-root <root> --target-label <text>
```

`<slug>` is `fresh-eyes` for a document review or `code-review` for a code change. Branch on
the returned JSON `status` (`success` / `skipped` / `failed`) exactly as in section (e); the
failure message is always carried in the `cause` field.

---

## (e) Outcome wording

**Success**

> Cross-model review complete. Candidate findings saved to `<report-path>`. Review
> the candidates against the internal findings before deciding which to carry forward.
> These are candidate findings, not verified findings — treat them as a second opinion
> that still needs your judgment.

**Skipped**

> Cross-model review skipped: this project has not opted in (cross_model_review not
> set or set to false in config). No external model was called.

**Failed**

> Cross-model review failed: relay the runner's `cause` field verbatim. The runner
> reported a mechanical failure — no output was produced.
>
> If the `cause` mentions `codex login`, run `codex login` to refresh credentials,
> then retry.

**No-false-clean rule**

The runner guarantees that mechanical failures (network error, auth failure, empty
response) surface as a `failed` outcome. The agent additionally checks any `success`
report: if the returned text reads like a refusal or a non-review (e.g., "I cannot
review this" or a policy decline), the agent treats it as a failed run and retries
once. A `success` report that does not contain candidate findings is not a clean
result.

Output from a cross-model review is always **candidate findings**. Candidates become
part of the evidence record only after the agent has read them and decided which, if
any, are worth carrying into the verified findings.
