Use during intent authoring. Write `prd.md` with the human problem, desired behavior, scope boundaries, acceptance examples, unresolved decisions, and confirmed answers.
Read existing project context and applicable human decisions before asking unresolved questions. Preserve explicit human code preferences as requirements with their sources, including answers elicited through grilling. Carry conventions settled here into design and spec; spec completes any remaining convention resolution.
When recording settled decisions or corrections, read `decisions.md` beside this file.

List what the unit commits to in a `Commitments` section of `prd.md`: one heading per commitment, one level below the section heading, with a plain-language name. Everything else in `prd.md` stays free-form. Design choices (or requirements, when the unit skips design) link these headings by anchor, and design close (spec close without design) refuses a missing or empty section and any commitment nothing links. Remove a commitment the unit deliberately leaves out of scope, or move it to an out-of-scope note outside the section, rather than leaving it uncovered. Write the section in the Markdown that `linked-sections.md` beside this file describes; Firebreak refuses anything else and names the file, the line and the item.

Keep a small feature brief small. Commit to what the user needs or an established consumer requires. A commitment is any promise the unit makes: a user story, a constraint the unit must respect, or a quality target. Label illustrative examples as examples. When offering a consequential choice, state the concrete benefit and cost without presenting optional strictness as necessary for safety. Distinguish the original human instruction from your interpretation. Preserve an explicit correction and its source so subsequent agents can verify intent independently of the PRD.

Challenge requirements that impose consequential implementation or maintenance
cost while the scope is still cheap to change. Explain the concrete cost, propose
a simpler way to meet the user's intent, and ask the operator to resolve the
tradeoff. Record their decision as authority.
