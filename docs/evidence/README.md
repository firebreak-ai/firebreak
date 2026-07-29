# Evidence

The source material behind the claims in [`results.md`](../../results.md). These are
the working research notes, retrospectives, and comparisons produced while building and
validating Firebreak — preserved here so the public results are auditable rather than
asserted. They are working documents, written during the work, not polished reports.

| Group | What's here |
|-------|-------------|
| [`research/`](research/) | Background research: AI code-failure modes, harness-pattern analysis, benchmark research, and the quality-quantification method used to measure pipeline output. |
| [`detection-accuracy/`](detection-accuracy/) | Detection-accuracy evaluation on a TypeScript project, including the three-way comparison against independently filed issues and the post-hygiene review. |
| [`brownfield-validation/`](brownfield-validation/) | The primary validation: remediating a private Go project dense with AI failure modes. Cross-phase analysis plus the security and test-infrastructure retrospectives. |
| [`self-improvement/`](self-improvement/) | Pipeline self-improvement across v0.3.4–v0.3.5: the self-improvement report and the per-phase remediation retrospectives that fed it. |

The code-review detection benchmark (precision/recall/F1 against the Martian Code
Review Benchmark) lives separately under [`benchmark/code-review/`](../../benchmark/code-review/),
with its own harness and per-release results.

> **Note.** A few of these documents link onward to architecture specs that are no
> longer in the repository — historical references from when the documents were
> written. The evidence above stands on its own; those onward links are not maintained.
