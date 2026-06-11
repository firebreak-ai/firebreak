# Feature 1 — Validation Experiment

Parent spec: `ai-docs/remediation-flow/remediation-flow-overview.md` (Feature 1 in §Feature map). Commitment-doc fields, outcome classes, and fallback paths are pinned there. This spec is the one-weekend manual workflow.

**Status (2026-05-21)**: completed. Outcome: `rewrite-wins-structurally`. Approval to proceed to Feature 2. See `retrospective.md` for full results; `process-comparison.md` for the quantitative comparison; the retrospective's "New findings" and "Methodology gaps" sections for parent-spec implications.

## 1. Problem

The whole remediation-flow architecture rests on one claim: physically isolating an agent from a slop codebase produces cleaner rewrites than spec-driven generation on top of the slop. The claim is unvalidated. Everything past this feature is conditional on it. Run a cheap experiment to confirm or kill it before any tooling investment.

## 2. Goals / Non-goals

**Goals**:
- Confirm or kill the firebreak hypothesis in one weekend.
- Pin the measurement rubric in writing *before* seeing rewrite results, so classification is mechanical.
- Surface operator-experience signal for Features 2–7 (what worked, what schemas need adjustment).

**Non-goals**:
- No new tooling. Intent extraction, rearchitecture, and sandbox setup are all manual.
- Not validating decomposition / merge moves — that's Feature 1.5.
- Not shipping the rewrite to realmind mainline.
- Single module only.

## 3. User-facing behavior

The operator runs this over a weekend, target ≤16 hours total. Each step ends with a git commit; commit ordering is the audit trail.

1. **Register**. Write `commitment-doc.md`: module path, the 8 fields from the parent spec. Leave the volume-drop threshold and per-category thresholds blank — they get filled in step 4. Commit before any agent reads any code.

2. **Set up the sandbox**. Stand up a container (docker / podman / chroot / separate user — your call). Mount only the artifact directories the rewrite needs; do not mount realmind source. Open a Claude session inside and ask it to `Read` a known realmind path — it must return "file not found." Capture that output for the retrospective.

3. **Author intent** (realmind, on host). Use Claude sessions to draft the three intent artifacts:
   - `intent/architectural-intent.md`, `intent/external-boundary-contract.md`, `intent/behavior-inventory.yaml` (schema in §4)
   
   Paste `intent-alignment-instructions.md` into the session to drive this phase. The instructions include the intent-alignment review step (context-clear subagent simulates downstream comprehension; iterate until clean) before commit. You're the author; agent is the hypothesis-generator.

4. **Author dependency stubs** (host, disciplined). The rewrite has to interface with unrewritten slop neighbors (DB client, session init, etc.) — those neighbors have actual signatures the rewrite must compile/typecheck against. Read **only the slop neighbor signatures** (no function bodies) and produce typed-contract stubs that match them. Output: `rearchitecture/dependency-stubs/<neighbor>.<lang-ext>`.
   
   Discipline rules: this is signature transcription, not design. Do not articulate capability here. Do not let what you see in the slop influence anything downstream beyond the stub files themselves. Audit by diffing each stub against the slop neighbor's actual public surface — the diff should be zero.

5. **Author rearchitecture** (sandbox). First inside-firebreak work. Mount intent artifacts (agent-facing only) + dependency stubs into the sandbox. Open a Claude session inside; re-verify isolation. Author the rearchitecture artifacts purely from intent + the dep stubs as fixed external boundary:
   - `rearchitecture/move-list.yaml`, `rearchitecture/module-graph.yaml`, `rearchitecture/interface-contracts/<module-id>.{md,lang-ext}`, `rearchitecture/decomposition-rationale.md`
   
   Paste `rearchitecture-instructions.md` to drive this phase. The new module's design is derived from what it *should* do (intent), not from what slop *currently* does. The dep stubs constrain the external interface; the internal architecture is free.

6. **Measure the fresh-module floor + pin thresholds** (sandbox). Hand-author ≥3 typed-contract stubs for realmind modules you know are slop-affected. Run `/fbk-implement` on each. Run `/fbk-code-review` on each output. Compute sightings-per-function with `radon` (Python) or `ts-morph` (TS). Floor = mean across the ≥3. Record model version + temperature.
   
   Now go back to `commitment-doc.md`. Fill in the volume-drop threshold and per-category thresholds with rationale tied to the floor. Re-commit. Don't write the rewrite yet.

7. **Rewrite** (sandbox). Author the new module against the rearchitecture artifacts. Use `/fbk-spec` → `/fbk-breakdown` → `/fbk-implement` or drive it manually — your call. At every session start, re-verify the sandbox blocks realmind reads. At the end, check each `B-NNN` from the inventory: realized in the rewrite, or missed? Record.

8. **Blinded reviews**. Run `/fbk-code-review` once on the original realmind module (host) and once on the rewrite (sandbox). Coin-flip: name the outputs `review-A.md` and `review-B.md`. Write the mapping to `review-mapping.sealed.yaml`. Don't open it.

9. **Count, classify**. Count sightings in A and B without knowing which is which. Commit `measurements.yaml`. *Now* unseal the mapping, label A and B as original/rewrite, compute per-category percent shifts. Apply the decision rule:
   - **rewrite-wins-structurally**: per-capita drops past threshold AND all 3 AI-failure categories meet threshold AND no behavior missed.
   - **wins-but-misses-behavior**: per-capita drops AND ≥2 of 3 categories meet AND some behavior missed → Feature 2 scope expanded.
   - **different-bad-pathology, meaningful volume drop**: per-capita drops AND categories don't meet → Feature 2 scope adjusted.
   - **similar-findings**: per-capita similar AND categories don't meet → **stop the project**.
   - **different-bad-pathology, no volume drop**: per-capita similar/regressed AND categories shift in either direction past threshold → **stop the project**.
   - **can't-tell**: anything else → iterate the experiment design.
   
   Commit `classification.yaml`.

10. **Retrospective**. Write `retrospective.md`: parent's four cycle-retrospective fields (caller-update is N/A — single-module scope), cycle metadata, mental-model check (one paragraph: did slop-shaped expectations leak into intent, the move-list, or your reaction to the rewrite output?), evidence on each parent-spec revisitable decision, methodology gaps for next time.

## 4. Technical approach

The experiment is artifacts crossing a sandbox boundary. The sandbox is the firebreak — physical filesystem absence, not denial. Realmind absolute paths must return "file not found" from inside the sandbox.

**Two-tier behavior inventory** (operator-authored — no skill exists yet):

```yaml
- id: B-001
  type: external-interaction   # or system-invariant | scheduled-routine
  short-handle: persona-receives-context-update   # domain language; no module names; no CamelCase
  agent-facing:
    triggering-event: a context update arrives for an active persona session
    actor: orchestrator   # vocab: external-caller | scheduler | orchestrator | system
    observable-outcome: persona's working memory reflects the update on next reasoning step
    invariants: [updates applied in arrival order, updates older than session start rejected]
    related-domain-concepts: [persona-session, working-memory]
  operator-facing:
    current-impl-trace: src/realmind/personas/persona.py:apply_context_update
    notes: slop conflates context-update with full-session-reset; inventory captures update only
```

Downstream agents see `agent-facing:` only. `operator-facing:` is for your traceability and stays out of prompts that cross into the sandbox.

**Categories that count** for per-category shift: `structural`, `fragile`, `test-integrity` (the three AI-failure-mode Detector types). `behavioral` is reported but doesn't gate — it's a behavior-preservation indicator.

**Why classification is honest**: thresholds are committed to git *before* the rewrite is reviewed. Measurements are committed *before* the blinding is broken. The decision rule is deterministic from those two inputs. You don't get to pick the outcome even with labels visible.

**Artifact paths**: all under `ai-docs/remediation-flow/validation-experiment/`. Subdirs: `intent/`, `rearchitecture/`, `measurement/`, plus `commitment-doc.md` and `retrospective.md` at the root.

## 5. Testing strategy

This feature produces no code; the experiment *is* the test of the hypothesis.

**New tests needed**: none. The measurement instrument is `/fbk-code-review`; its calibration is taken as given.

**Existing tests impacted**: none.

**Test infrastructure changes**: none new. Operator needs `radon` or `ts-morph` and a sandbox container runtime.

**Mocking justifications**: N/A.

**User verification steps**:

- UV-1 (AC-01): `commitment-doc.md` has 8 fields; thresholds blank with "post-floor" comment; git log shows this commit predates any `intent/` or `rearchitecture/` commit.
- UV-2 (AC-02): Inside-sandbox `Read` of a known realmind path returns "file not found." Captured.
- UV-3 (AC-03): `<sandbox>/fixtures/` has ≥3 directories each with stub + `/fbk-implement` output + `/fbk-code-review` output; floor recorded with model + temperature + tool version.
- UV-4 (AC-04): Commitment doc has thresholds filled with rationale tied to floor; second commit predates any commit under `measurement/rewrite/` or `measurement/review-*.md`.
- UV-5 (AC-05): Both `review-A.md` and `review-B.md` exist; sealed mapping exists; `measurements.yaml` blinded commit predates the unseal.
- UV-6 (AC-06): `classification.yaml` has one outcome class; re-running the decision rule against committed measurements + thresholds reproduces it.
- UV-7 (AC-07): `retrospective.md` populated with parent's four fields + cycle metadata + mental-model check + revisitable-decisions evidence + methodology gaps.

## 6. Documentation impact

**Project documents to update**: none. Parent overview already pins commitment-doc structure, outcome classes, fallback paths.

**New documentation to create**: artifacts authored during execution (commitment doc, intent files, rearchitecture files, measurement files, retrospective). All under `ai-docs/remediation-flow/validation-experiment/`.

## 7. Acceptance criteria

- **AC-01**: Commitment doc with 8 fields (thresholds blank) committed before any `intent/` or `rearchitecture/` commit.
- **AC-02**: Inside-sandbox `Read` of a known realmind path returns "file not found"; output captured in retrospective.
- **AC-03**: Fresh-module floor computed from ≥3 fixtures with model version, temperature, function-counting tool recorded.
- **AC-04**: Volume-drop threshold and per-category thresholds populated with rationale tied to floor; second commitment-doc commit predates rewrite-review commits.
- **AC-05**: Both blinded reviews exist; sealed mapping written; blinded `measurements.yaml` committed before mapping is unsealed.
- **AC-06**: `classification.yaml` contains one outcome class; reproducible by re-running the decision rule against committed measurements + thresholds.
- **AC-07**: Retrospective covers parent's four cycle-retrospective fields (caller-update N/A), cycle metadata, mental-model contamination check with net judgment, evidence on each parent-spec revisitable decision, methodology gaps.

## 8. Open questions

- **Sandbox technology** (docker / podman / lima / chroot / separate user / remote VM). Operator picks; structural requirement is the AC-02 read-failure. Resolve before step 2.
- **Use `/fbk-council` at intent or rearchitecture?** Default: skip unless stuck; record the choice as evidence on the parent's "council count" revisitable decision. Resolve at step 3.
- **One-file `/fbk-code-review` sanity pass on realmind before step 1?** Cheap check that the skill produces interpretable output on this codebase. Operator's call. Resolve before step 1.

## 9. Dependencies

- Parent: `ai-docs/remediation-flow/remediation-flow-overview.md`, `ai-docs/remediation-flow/remediation-flow-review.md`.
- Realmind on an operator-managed git branch.
- `/fbk-code-review` and `/fbk-implement` (versions recorded in commitment doc).
- `radon` (Python) or `ts-morph` (TypeScript).
- Sandbox container runtime.

No external services, paid APIs, new build tooling, or new skills.

## Decisions resolved during scoping

- **Sandbox container = the firebreak.** Verified by an inside-sandbox `Read` returning "file not found" against a known realmind path. Operator picks the container technology.
- **Rearchitecture inside the firebreak (capability-driven); dependency stubs outside (signature transcription only).** Parent spec puts rearchitecture above the firebreak with structural-analysis-as-meta-analysis as the defense. Experiment evidence (intent extraction) showed that even meta-derived structural facts shape-contaminate downstream. Rearchitecture moves inside; the new module's design is derived from intent, not from slop. The interface to unrewritten slop neighbors is the one place where slop-shape must enter — handled as a separate, disciplined dep-stub authoring step on host (signature transcription, no design). This is evidence to revisit the parent spec's above-firebreak set composition.
- **AI-failure categories = `structural`, `fragile`, `test-integrity`** (Detector taxonomy). `behavioral` is reported but doesn't gate.
- **Blinding through counting; mechanical classification after.** Operator counts blind (sealed mapping). Mapping unseals after `measurements.yaml` is committed. Classification is reproducible from measurements + pre-pinned thresholds, so the operator has no degree of freedom even with labels visible.
- **Floor fixtures = operator-selected slop-affected modules.** Criterion is "slop-affected and needs rearchitecture," not similarity to the experiment module.
- **Threshold-pinning timing = post-floor, pre-rewrite-review.** Git timestamp ordering is the proof.
- **Caller-update = N/A in Feature 1.** Single-module scope.
- **Mental-model contamination check = one paragraph in the retrospective.** Did slop-shaped expectations leak into intent, the move-list, or your reaction to the rewrite? Net judgment: yes / no / can't-tell. If yes or can't-tell, recommends Feature 2 child spec adopt the parent's named structural defenses.
