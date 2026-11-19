# Change request: `check` reports every error, each with its line

Today `check` stops at the first fault in a circuit file. Users fix it, run again, and meet the next one. Most errors also carry no line number, so users search the file by hand. `check` must report every fault it can find in one run and say where each one is.

Only `check` changes, and only what it reports when the circuit file has faults.

## The result of a failed `check`

When `check` finds faults in the circuit file (exit code 2 or 3 today), `--json` prints

```json
{"ok": false, "command": "check", "exit_code": <2 or 3>, "errors": [<error>, ...]}
```

- `errors` takes the place of `error`. The `error` key is gone from this result.
- Each entry has the same five fields as today's error object: `type`, `message`, `file`, `line`, `col`. Types and messages are what they are today, including the cycle path in a `CycleError` message and the widths in a width error message.
- A file with one fault gives a list of one.

A "syntax error" below is an error whose type has exit code 2: `CircParseError`, `BenchParseError`, `JsonParseError`. A "validation error" is one whose type has exit code 3.

**Exit code.** 2 if the list holds a syntax error, otherwise 3. The `exit_code` field has the same value.

**Unchanged.** A file that passes `check` gives the same output as today. Failures with exit code 1 (file not found, format not recognised, wrong command line) keep today's single `error` object. This change adds no new kinds of check: a file with one statement per line passes after the change exactly when it passes today.

## `.circ` and `.bench` files

A statement is one line of the file: a declaration line or an assignment line. Line numbers start at 1 and count every line, blank and comment lines included. A statement split over several lines is not part of the format; what the program does with one is not covered by this request.

### Syntax errors

Each line is judged on its own. A line that is not a well-formed statement gives one syntax error with that line's number and a column inside that line, and the next line is read as a fresh statement.

If any line has a syntax error, the list holds the syntax errors and nothing else: one per bad line. Validation errors are reported only for a file that has no syntax errors. This keeps a broken line from producing follow-on errors about the names it would have declared or assigned.

### Validation errors

Every statement is checked on its own, and each faulty statement gives one error with its line number:

| Fault | Line reported |
|---|---|
| A declaration line repeats a name declared earlier, or twice on the line (`DuplicateNameError`) | the line that repeats it |
| A declaration line comes after an assignment line (`DeclarationAfterAssignmentError`) | that declaration line |
| An assignment line has a fault: undeclared name on either side, assignment to an input, wrong number of arguments, width mismatch, index or slice out of bounds | that assignment line |
| A signal is assigned again (`MultipleAssignmentError`, or `RedefinitionError` in `.bench`) | each later assignment line of that signal |
| A `.bench` `OUTPUT(...)` names a signal that is never defined (`UndefinedNameError`) | the `OUTPUT` line |

A faulty statement still counts for the rest of the file, so one fault is reported once:

- A declaration line with a fault still declares its names. A repeated name keeps its first declaration.
- An assignment line with a fault still counts as the assignment of its signal. When a signal is assigned more than once, the first assignment line is its assignment.
- When one line has several faults, report one error for it. Which one is your choice.

Two kinds of error belong to no single assignment:

- **Unassigned signal.** One `UnassignedSignalError` for each wire or output that no assignment line names on its left side. Its line is the line that declares the signal. (`.bench` files have no such error: there a signal is declared by its `INPUT` line or its assignment line, and an output that is never defined is the `UndefinedNameError` in the table.)
- **Cycle.** At most one `CycleError`, however many cycles there are. Its `line` is `null`. Cycles are searched among the assignments of wires and outputs, faulty ones included.

### Order

Ascending line number. On one line, the line's own error comes before the unassigned-signal errors of signals declared there; those may be in any order among themselves. The `CycleError`, which has no line, comes last.

## `.json` files

A file that is not valid JSON, or does not match the schema, gives a list of one: the `JsonParseError` (with its line and column, as today) or the `JsonSchemaError`.

Otherwise each entry of `assignments` is a statement and the rules above apply, with these differences:

- Every error has `line: null`. This includes a syntax error in an `rhs` string, which is the one place a syntax error has no line.
- Order: the errors of faulty `assignments` entries in the order of the entries, then the unassigned-signal errors in any order, then the `CycleError`.

## Text mode

Without `--json`, a failed `check` prints one line per error, in the same order, and nothing else. Each line contains the error's type name and, when the error has a line, the text `<file>:<line>` with the file path as given on the command line. The exit code follows the same rule.

## Other commands

`eval`, `stats`, `lint`, `dot`, `cone`, `truth-table`, `equiv` and `opt` do not change in any way. On a faulty file each still stops at one error and reports it as a single `error` object with that error's exit code, exactly as today. When a file has several faults, the one they report is the one they report today; it need not be the first entry of `check`'s list.

## Examples

`adder.circ`

```text
input a b
output y z
wire t1 spare

t1 = NOT(a, b)
y = AND(t1, ghost)
z = OR(a, b)
z = XOR(a, b)
```

```bash
$ circopt check adder.circ --json
{"ok":false,"command":"check","exit_code":3,"errors":[{"type":"UnassignedSignalError","message":"...","file":"adder.circ","line":3,"col":null},{"type":"ArityError","message":"...","file":"adder.circ","line":5,"col":null},{"type":"UndefinedNameError","message":"...","file":"adder.circ","line":6,"col":null},{"type":"MultipleAssignmentError","message":"...","file":"adder.circ","line":8,"col":null}]}
# exit 3
```

`t1` is not reported as unassigned and line 6 gets no error for using it: line 5 is faulty but still assigns `t1`.

`broken.circ` is the same file with a parenthesis missing on line 7:

```text
input a b
output y z
wire t1 spare

t1 = NOT(a, b)
y = AND(t1, ghost)
z = OR(a, b
z = XOR(a, b)
```

```bash
$ circopt check broken.circ --json
{"ok":false,"command":"check","exit_code":2,"errors":[{"type":"CircParseError","message":"...","file":"broken.circ","line":7,"col":11}]}
# exit 2
```

The file has a syntax error, so only syntax errors are listed. Line 8 is read as a fresh statement and is well formed.

`loop.json`

```json
{
  "format_version": 1,
  "inputs": [{"name": "a", "msb": 0, "lsb": 0}],
  "outputs": [{"name": "y", "msb": 0, "lsb": 0}, {"name": "z", "msb": 0, "lsb": 0}],
  "wires": [{"name": "t1", "msb": 0, "lsb": 0}, {"name": "t2", "msb": 0, "lsb": 0}],
  "assignments": [
    {"lhs": "t1", "rhs": "NOT(t2)"},
    {"lhs": "t2", "rhs": "AND(a, t1)"},
    {"lhs": "y", "rhs": "OR(t1)"}
  ]
}
```

```bash
$ circopt check loop.json --json
{"ok":false,"command":"check","exit_code":3,"errors":[{"type":"ArityError","message":"...","file":"loop.json","line":null,"col":null},{"type":"UnassignedSignalError","message":"...","file":"loop.json","line":null,"col":null},{"type":"CycleError","message":"...","file":"loop.json","line":null,"col":null}]}
# exit 3
```

The `CycleError` message names the cycle, for example `t1 -> t2 -> t1`. The columns of validation errors and the exact messages are yours to choose, as they are today.

In text mode the first example prints four lines, for example:

```text
error: adder.circ:3: UnassignedSignalError: signal 'spare' is never assigned
error: adder.circ:5: ArityError: NOT requires exactly 1 argument, got 2
error: adder.circ:6: UndefinedNameError: undefined signal: ghost
error: adder.circ:8: MultipleAssignmentError: signal 'z' assigned multiple times
```

## Tests

Keep the existing tests passing and up to date with the code; tests that assert the old single-error shape of `check` must be updated to the new shape. Add tests for the behavior above.
