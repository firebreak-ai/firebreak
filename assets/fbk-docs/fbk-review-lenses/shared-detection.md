# Shared Detection Passes

This file holds detection passes that are referenced by two or more review lenses. Each pass is listed once here; lenses reference it by name rather than re-embedding the body.

## Test-integrity audit

For each modified test: (a) does the test name describe what the test actually asserts? (b) do any mocks, monkeypatches, or fixtures invalidate the assertion (e.g., `time.sleep` patched away)? (c) is the assertion strict enough to catch the behavior it claims to check? (d) are shared mutable defaults avoided? (e) would the test still pass if only the targeted behavior were reverted, given any other code path that could produce the same observable outcome — or does it genuinely isolate the behavior it claims to cover? (f) does the assertion pin only the behavior the surrounding contract requires, or does it also lock in an implementation detail (such as internal cleanup timing) the contract leaves open?
