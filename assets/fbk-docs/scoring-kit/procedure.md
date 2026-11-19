Settle a target's rules and measure its tests against a scoring kit. The kit-writer brief, `kit-writer.md`, is beside this file; the kit runner is `fbk-scripts/run-kit.py` in the same installed Firebreak directory. Fill every `{placeholder}` in the brief before passing it as a subagent's prompt.

## Settle the rules

The rules live in `.fbk/test-cleanup/<target>.md`. When it exists, its rules are the starting draft; check each against the current code and docs. Otherwise write the rules for each entry point of the target in plain words, looking first in Firebreak unit specs (`.fbk/<unit>/spec.md`, archived units included), then the repository's docs, then the code.

Decide every detail the code, tests or specs show, such as message wording, output order and format, file names and limits, from evidence:
- **Rule:** a document states it; code or a skill outside the target depends on it, by parsing it, matching it or finding files by it; or it guards safety or security.
- **Open:** everything else. Tests stop checking it.

Record each rule with its evidence and list each open detail. Ask the operator only when sources conflict, such as a spec stating behavior the code does not have, using the `fbk-grilling` skill one question at a time. Otherwise continue without asking: every other call follows from evidence, and the operator reviews it in the report.

## Build the kit and measure the tests

Start a subagent with `kit-writer.md` as its prompt, giving it the rules, the target's production files and a kit folder in the session's scratch directory, outside the repository, where no subagent working in the repository comes across it. Its result lists each kit file as a wrong version or a correct rewrite, and the details the rules leave unsettled. Settle each unsettled detail from evidence as above, rewording the rule or listing the detail as open.

Read each wrong version against its rule. When the rule's words do not settle that the change is wrong, such as a missing value or a capitalization the rule does not mention, settle the detail from evidence as above: reword the rule when evidence makes it one, otherwise list it as open and drop the kit file.

Run the target's tests against the kit yourself with `python3 <installed Firebreak directory>/fbk-scripts/run-kit.py --root <project> --kit <kit folder> --command "<test command>" --out <log folder>`, with the log folder in the scratch directory. It applies each kit file in a disposable copy and never changes the working tree. Read the logs it writes and record which wrong versions the suite catches and which tests fail each correct rewrite. A test that fails a correct rewrite is a confirmed change detector. Drop a kit file that does not apply and tell the operator.
