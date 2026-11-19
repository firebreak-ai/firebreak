Review the bodies of the planned tests once, reading only. The request is in `.fbk/testplan/request.md`; set `FBK_TESTPLAN_ALL=1` to run tests that are still switched off.

For each test carrying a `planned` mark, judge:

- **Does the body check what the docstring says?** Name a plausible wrong implementation and ask whether this test, or another in the plan, fails on it. Ask also whether a different correct implementation would pass.
- **Does it go through the owner its mark names,** using the real interface?
- **Do the request's words or the recorded answer support the example?** An example neither supports is a finding, whatever its merit.
- **Does it assert only what the example states?** An assertion on a detail the request leaves open is a finding.

Check too that the production changes made alongside the tests add no behaviour.

Return each finding as the test's id, what is wrong, and the correction. When nothing is wrong, say so.
