# Configuration and Lifecycle

How the plane is governed: capture levels and where their setting lives, the retention cap and baseline protection, the install-time hook registration and duplicate-registration migration, and the source of the known-agent list.

## Three capture levels

Exactly three, mutually exclusive and project-local:

- **Off** — the router exits immediately and records nothing, regardless of project type.
- **Standard** — lifecycle events, failures, subagent results, and pipeline-chokepoint events are recorded; tool-call payloads and prompt text are not.
- **Full** — every event with complete payloads, including tool-call detail and prompt text.

The shipped default inside a Firebreak-managed project is standard. Full requires an explicit operator action; it is never on by default anywhere. Uninstrumented projects are always off regardless of any setting.

## Where the setting lives — capture.cfg

The level is stored in a plain key=value file at `.fbk-capture/capture.cfg`:

```
capture_level=standard
```

Valid values: off, standard, full; any other value is treated as standard with a stderr warning. The file is optional — its absence means "use the default for this project type."

This is a deliberate departure from the existing `.claude/automation/config.yml` surface. The capture gate runs on the hot path in every Claude tool call, and parsing YAML there would add the PyYAML dependency and startup cost to a path that must complete in well under a second. A single-line key=value read is cheap and dependency-free. Collocating the file in `.fbk-capture/` keeps the capture directory self-contained — data, retention locks, and config in one place. The tradeoff: capture level is not discoverable through the existing config loader, so documentation must point operators to `capture.cfg`.

## The explicit capture marker

For a non-Firebreak project to opt into capture, the operator creates `.fbk-capture/capture.cfg` with a valid level. The presence of that file is the explicit marker the capture gate looks for — one file is both the opt-in signal and the level declaration. This resolves the open question about the marker's name, location, and format.

## Retention with operator-lockable baselines

The events file self-prunes when it exceeds a size cap (default ~5MB) by dropping the oldest lines, keeping the file bounded without operator action. But the before/after evaluation use case needs two full cycles retained at once, and a naive cap could prune the baseline before the comparison runs.

The reconciliation: pruning skips any line whose spec is named by an empty file in `.fbk-capture/locked/`. To protect a baseline, the operator drops an empty lock file named after the spec. The retention module checks that directory before pruning and never understands cycle semantics itself. The accepted cost: if the operator forgets to lock a baseline before the cap is reached, it is pruned without warning — so documentation must surface the lock step exactly where an operator sets up a before/after evaluation.

Module: `fbk/capture/retention.py`, exporting `prune_if_needed(events_path, max_bytes, protect_specs)`; fail-silent.

## Stage stamping outside an SDL run

Each event carries the active stage, read from the state engine at write time. When the hook fires outside an SDL run, there is no active stage; the event carries no stage field and is recorded normally. No synthetic stage value is invented.

## The known-Firebreak-agent list

Subagent filtering needs a current list of known agents, or a new agent silently undercounts. The list is derived at module load time by scanning installed persona files under the global Claude directory for an agent-type frontmatter key — so adding an agent persona file updates the filter automatically, with no separate maintenance step. A hardcoded fallback covers the current agents when the scan fails, and a stale-fallback flag surfaces as a warning in the report. The scan is a one-time glob at import, not per-event. An agent installed after a router process started is invisible to that process — acceptable, since router processes are short-lived.

Module: `fbk/capture/known_agents.py`.

## Install-time registration and migration

The hook router needs a hooks entry in the global Claude configuration, placed by the installer. The real installer is `installer/install.sh`, which delegates the settings merge to `installer/merge-settings.py`, merging the template at `assets/settings.json` (there is no `install.sh` under the fbk-scripts tree — a review corrected this). The installer changes are:

- Register the router for the Claude-level hook events (tool use, lifecycle, subagent stop, prompt submit) by adding entries to the `assets/settings.json` template that `merge-settings.py` merges. The entry's command must resolve to the router under the **global** fbk-scripts tree; note that `install.sh`'s `sed` transform rewrites `$HOME/.claude/` to `$CLAUDE_PROJECT_DIR/.claude/` on project-scoped installs, so the router command must be written in a form that resolves to the one global path on both global and project installs — otherwise the project rewrite re-introduces the very project-vs-global divergence the migration removes.
- Gitignore `.fbk-capture/` (data, `capture.cfg`, and `locked/`) so capture never enters version control.
- **Duplicate-registration removal.** A project that ran the earlier capture experiment may carry a project-level router registration. With the global install present, both fire and events double. After merging settings, the installer removes any project-level hook command matching the old router pattern (anchored to the exact old command string, leaving every other hook entry byte-intact, idempotent across re-runs), so no previously-instrumented project is left in a state where duplication is possible. **This removal is net-new logic:** `merge-settings.py`'s `merge_hooks` today is add-only (canonicalize-and-append, no removal path), so the migration is a new capability with its own defined home — either an added removal pass in `merge-settings.py` or a dedicated migration step in `install.sh` — not an extension of the existing merge.

The human operator must apply any configuration change that Claude Code's self-modification gate prevents the agent from applying autonomously.

Per-project sandboxes mount parts of the global configuration directory read-only; the capture layer never writes there. All capture writes go to the project-local `.fbk-capture/` directory. This is enforced by design, not a runtime check.
