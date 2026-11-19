# Change request: large circuits inside a time limit

Users now feed `circopt` machine-generated circuits far larger than the ones we planned for. On those, commands run for minutes or stop with an internal failure. The tool must stay usable at these sizes and give exactly the answers it gives today.

## What must hold

"Size" is the number of assignments in a circuit file. Each limit is the wall-clock time of one command, from start to exit, on a typical developer machine.

1. **Up to 100,000 assignments, within 20 seconds:** `check`, `eval` (`--mode 2val` and `--mode 3val`), `stats`, `dot` (with or without `--cone`) and `cone`.
2. **Up to 5,000 assignments and at most 8 input bits in total, within 30 seconds:**
   - `truth-table`, `lint` and `equiv` with `--max-input-bits 8`, so all 256 input rows are covered (for `equiv`, each of the two circuits may be this size);
   - `opt` with any pipeline, pass list, fan-in limit, renaming, output format and `--report`, with or without `--verify --max-input-bits 8`.
3. The limits hold
   - in all three input formats (`.circ`, `.json`, `.bench`);
   - for any shape of circuit, from wide and shallow to one long chain in which every assignment depends on the one before it, as deep as the circuit is large (100,000 deep for the first group, 5,000 for the second);
   - for any order of the assignments in the file, including a signal used before the line that assigns it;
   - for scalar and vector signals and every operator.
4. An invalid circuit of these sizes gets its normal error within the same limits. In particular, a dependency cycle anywhere in a 100,000-assignment circuit is reported as `CycleError` (exit code 3) with the cycle path in the message.

You may assume that no single right-hand side nests more than 8 levels deep or reads more than 16 signals.

## What must not change

- Every result stays exactly what it is today, for every input, small ones included: text and JSON on stdout, written files, error types and messages, exit codes.
- Files and listings that are byte-for-byte reproducible today stay byte-for-byte the same: `cone` and `opt` output files, `dot` files, truth tables, statistics, reports, counterexamples.
- Where today's program fails internally or does not finish on a large circuit, the result must be the one the specification defines for that input.
- Where today's output is not fixed from one run to the next, any output today's program could produce is acceptable.
- The command line stays as it is: no new flags, and none are needed to reach these limits.

## Tests

Keep the existing tests passing and up to date with the code. Add tests for the limits above; size them so the suite stays quick to run.
