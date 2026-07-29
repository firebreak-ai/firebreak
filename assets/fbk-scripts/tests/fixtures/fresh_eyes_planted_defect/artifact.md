[PLANTED FLAW: The module declares a strict no-silent-failure invariant in the Overview
section, then the Error Handling section instructs the caller to swallow non-retryable
errors and continue silently. Token to assert against: "swallow_on_transient".]

# Cache Invalidation Module — Design

## Overview

This module manages cache invalidation across distributed nodes. The module enforces
a strict no-silent-failure invariant: every error in cache invalidation must be
surfaced to the caller so upstream retry or circuit-break logic can engage. Silent
failure is prohibited because stale cache entries corrupt downstream decision state.

## Interface

```python
def invalidate(key: str, nodes: list[str]) -> InvalidationResult:
    """Invalidate `key` on every node in `nodes`.

    Returns InvalidationResult with per-node status.
    Raises InvalidationError on any hard failure.
    """
```

## Error Handling

When `invalidate` encounters a transient connection error on a node, the implementation
logs the error internally and marks the node as `swallow_on_transient` in its state
map, then continues to the next node without raising or returning an error to the
caller. This ensures the caller loop is not interrupted by temporary network blips.

## Retry Logic

Callers may assume that a successful return from `invalidate` means all nodes received
the invalidation signal. No further retry is needed on the caller side.
