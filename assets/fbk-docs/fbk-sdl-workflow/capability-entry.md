Load condition: routed by a phase skill's mid-pipeline-entry step when the phase is invoked directly.

## Capability entry model

Each phase in the SDL pipeline is independently invocable. A user or skill may call any phase directly without running prior phases in sequence.

When a phase is invoked directly, it checks whether its upstream prerequisites are satisfied before proceeding. The check is performed by `fbk.precheck.check_prerequisites(phase, feature_dir)` (installed at `.claude/fbk-scripts/fbk/precheck.py`).

If the probe returns `ready=True`, the phase proceeds normally.

If the probe returns `ready=False`, the phase **does not hard-block**. Instead it:

1. Names the specific missing artifact and the upstream phase that produces it.
2. Offers to run that upstream phase now, so the user can proceed without manually re-invoking.

## Upstream-missing cases

| Phase invoked | Missing artifact | Upstream phase to offer |
|---|---|---|
| Design | `prd.md` | Intent |
| Spec | `design-manifest.md` | Design |
| Breakdown | `<feature>-spec.md` | Spec |
| Code Review | `implementation/` | Implement |

## Non-blocking contract

The name-and-offer behavior must not call `sys.exit` or raise an unhandled exception. The phase presents the missing prerequisite and the offer, then waits for the user's choice. If the user declines to run the upstream phase, the phase may proceed with a warning or stop gracefully — but the decision belongs to the user, not the phase.
