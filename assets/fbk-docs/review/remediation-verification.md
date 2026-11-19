# Remediation verification

When assessing a material fix, independently establish both the corrected behavior and the regression test's ability to reject the defect against the accepted requirement.

Read the affected source, assertions, related paths and recorded execution evidence. Use Read, Grep and Glob to investigate the mechanism and any claimed safeguards. A useful regression and a green suite do not by themselves establish correctness of related behavior such as error precedence.

Use evidence from running the regression against the corrected code and the original defect or a representative incorrect implementation in a disposable copy. Establish that the incorrect implementation fails at the intended behavioral assertion; imports, setup errors and unrelated failures do not demonstrate regression coverage. When execution is unavailable, distinguish source inspection from observed results and identify the missing check.

Interacting safeguards and inseparable changes need evidence-backed judgment. Removing one guard may leave the promised observable behavior protected by another guard. Demonstrate which prohibited behavior the test rejects using the original defect or a representative combined incorrect implementation, and state any narrower assurance. A test that only asserts its setup or passes against the demonstrated unprotected defect does not verify the correction. Check a claim that a test cannot fail against its actual assertions and execution evidence before ruling.

Ground the assessment in source and test revisions, the tested requirement, commands, environment prerequisites, actual outcomes and limitations available in the evidence. Cite exact excerpts from recorded output when quotations are required; label summaries as summaries. A remediator's confidence or recollection does not establish an observed result.
