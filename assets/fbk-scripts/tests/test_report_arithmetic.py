"""Unit tests for fbk.report — exact-value computations.

Covers:
- classify_gate_attempts: pre-park attempts labelled first_try, post-re-entry labelled after_rework
- first_try_pass_rate: exact fractional value from first-try attempts
- kill_rate: (total_raised - total_confirmed) / total_raised
- derive_parks: state-derived park rows, empty reason renders as present entry
- derive_rework: re-entry count from repeated stage timestamps
- subagent count filtering: only known-identity SUBAGENT_STOP events counted
"""

import pytest

try:
    import fbk.report as report
    REPORT_AVAILABLE = True
except ImportError:
    REPORT_AVAILABLE = False

from tests import capture_fixtures

pytestmark = pytest.mark.skipif(
    not REPORT_AVAILABLE,
    reason="fbk.report module not yet implemented",
)


# ---------------------------------------------------------------------------
# classify_gate_attempts
# ---------------------------------------------------------------------------


def test_attempt_before_park_classifies_first_try():
    """classify_gate_attempts labels pre-park attempts phase == "first_try".

    All VERIFICATION_RESULT events occur before the stage's first park, and the
    state carries no re-entry.  Every returned entry must have phase "first_try".
    """
    stage = "VALIDATING"
    spec = "test-spec"

    events = [
        capture_fixtures.build_event(
            "VERIFICATION_RESULT",
            source="fbk-implementer",
            spec=spec,
            stage=stage,
            timestamp="2026-01-01T00:00:01+00:00",
            data={"passed": False},
        ),
        capture_fixtures.build_event(
            "VERIFICATION_RESULT",
            source="fbk-implementer",
            spec=spec,
            stage=stage,
            timestamp="2026-01-01T00:00:02+00:00",
            data={"passed": True},
        ),
    ]

    # State with only the one stage visited — no park, no re-entry.
    state = capture_fixtures.build_state(
        spec=spec,
        stage_timestamps={stage: "2026-01-01T00:00:00+00:00"},
        error_history=[],
    )

    attempts = report.classify_gate_attempts(events, state, stage)

    assert len(attempts) == 2
    for entry in attempts:
        assert entry["phase"] == "first_try", (
            f"expected first_try but got {entry['phase']!r}"
        )


def test_attempt_after_ready_reentry_classifies_after_rework():
    """classify_gate_attempts uses first-park boundary, not stale READY timestamp.

    Red mechanics: pre-fix, classify_gate_attempts reads stage_timestamps["READY"]
    as the re-entry boundary.  READY is a last-write-wins key — when VALIDATING
    parked and re-entered first, REVIEWING's state still carries READY=T2
    (VALIDATING's re-entry).  T4 >= READY(T2) satisfies the pre-fix condition, so
    the T4 attempt is misclassified as after_rework.  The first-park boundary (T5,
    the first error_history entry for REVIEWING) labels T4 as first_try because
    T4 < T5.

    Fixture shape — two stages visited, each parked once, READY holds VALIDATING's
    re-entry (stale and earlier than REVIEWING's own first park):
      T0 = 2026-01-01T00:00:00  VALIDATING stage start
      T1 = 2026-01-01T00:01:00  VALIDATING parks  (error_history[0])
      T2 = 2026-01-01T00:02:00  READY — VALIDATING's re-entry (stale for REVIEWING)
      T3 = 2026-01-01T00:03:00  REVIEWING stage start
      T4 = 2026-01-01T00:04:00  REVIEWING gate fail — before REVIEWING's own park
      T5 = 2026-01-01T00:05:00  REVIEWING parks  (error_history[1])
      T6 = 2026-01-01T00:06:00  REVIEWING gate pass — after REVIEWING's park
    """
    stage = "REVIEWING"
    spec = "test-spec"

    # Full ISO timestamps for each point in the scenario.
    T0 = "2026-01-01T00:00:00+00:00"  # VALIDATING start
    T1 = "2026-01-01T00:01:00+00:00"  # VALIDATING first park (error_history[0])
    T2 = "2026-01-01T00:02:00+00:00"  # READY — VALIDATING's re-entry; stale for REVIEWING
    T3 = "2026-01-01T00:03:00+00:00"  # REVIEWING stage start
    T4 = "2026-01-01T00:04:00+00:00"  # gate fail — after stale READY(T2), before REVIEWING's park
    T5 = "2026-01-01T00:05:00+00:00"  # REVIEWING first park (error_history[1])
    T6 = "2026-01-01T00:06:00+00:00"  # gate pass — after REVIEWING's park

    # Production VERIFICATION_RESULT shape with task_completed source and tests_passed key.
    events = [
        capture_fixtures.build_event(
            "VERIFICATION_RESULT",
            source="task_completed",       # production source label
            spec=spec,
            stage=stage,
            timestamp=T4,                  # after stale READY, before REVIEWING's park
            data={"tests_passed": False, "out_of_scope_files": []},
        ),
        capture_fixtures.build_event(
            "VERIFICATION_RESULT",
            source="task_completed",
            spec=spec,
            stage=stage,
            timestamp=T6,                  # after REVIEWING's park
            data={"tests_passed": True, "out_of_scope_files": []},
        ),
    ]

    # Production state shape after two stages and two parks.
    state = capture_fixtures.build_state(
        spec=spec,
        stage_timestamps={
            "VALIDATING": T0,  # VALIDATING started
            "READY": T2,       # READY holds VALIDATING's re-entry — stale and earlier than REVIEWING's park (T5)
            "REVIEWING": T3,   # REVIEWING started
            "PARKED": T5,      # last PARKED timestamp (REVIEWING's park)
        },
        error_history=[
            # VALIDATING's park — stage matches "VALIDATING", not "REVIEWING".
            {"stage": "VALIDATING", "error": "early park", "timestamp": T1},
            # REVIEWING's park — this is the first-park boundary for the stage under test.
            {"stage": "REVIEWING", "error": "gate failed", "timestamp": T5},
        ],
        current_state="REVIEWING",
    )

    attempts = report.classify_gate_attempts(events, state, stage)

    # Exact assertion: T4 is first_try (before REVIEWING's first park at T5);
    # T6 is after_rework (at or after that boundary).
    assert [a["phase"] for a in attempts] == ["first_try", "after_rework"], (
        f"expected phases ['first_try', 'after_rework'] but got "
        f"{[a['phase'] for a in attempts]!r}; "
        "pre-fix: T4 >= READY(T2) misclassifies T4 as after_rework"
    )
    assert [a["passed"] for a in attempts] == [False, True], (
        f"expected passed [False, True] but got {[a['passed'] for a in attempts]!r}"
    )


# ---------------------------------------------------------------------------
# first_try_pass_rate
# ---------------------------------------------------------------------------


def test_first_try_pass_rate_is_exact_fraction():
    """first_try_pass_rate of fail/fail/pass returns exactly 1/3.

    Three first-try attempts with outcomes False, False, True.  The rate must
    equal pytest.approx(1/3).  The attempt list must be non-empty so the
    presence assertion guards against a trivially-passing empty input.
    """
    attempts = [
        {"phase": "first_try", "passed": False},
        {"phase": "first_try", "passed": False},
        {"phase": "first_try", "passed": True},
    ]

    assert len(attempts) > 0, "fixture must be non-empty"

    rate = report.first_try_pass_rate(attempts)

    assert rate == pytest.approx(1 / 3)


# ---------------------------------------------------------------------------
# kill_rate
# ---------------------------------------------------------------------------


def test_kill_rate_is_exact_value():
    """kill_rate for total_raised=10 and total_survived=3 returns exactly 0.7.

    Builds a rounds list (the producer's total_raised/total_survived shape)
    where the summed totals are known.  (10 - 3) / 10 == 0.7.
    """
    rounds = [
        {"raised": 6, "survived": 2},
        {"raised": 4, "survived": 1},
    ]

    rate = report.kill_rate(rounds)

    assert rate == pytest.approx(0.7)


# ---------------------------------------------------------------------------
# derive_parks
# ---------------------------------------------------------------------------


def test_park_with_empty_reason_renders_no_reason_row():
    """derive_parks keeps an empty-reason park as a present entry.

    A park whose error string is empty must not be silently dropped; the
    returned list must contain one entry for it, and the entry's reason must
    be empty or None so the renderer can surface "(no reason recorded)".
    """
    stage = "VALIDATING"
    spec = "test-spec"

    state = capture_fixtures.build_state(
        spec=spec,
        stage_timestamps={stage: "2026-01-01T00:00:00+00:00"},
        error_history=[
            {"stage": stage, "error": "", "timestamp": "2026-01-01T00:01:00+00:00"},
        ],
    )

    parks = report.derive_parks(state, stage)

    assert len(parks) >= 1, "empty-reason park must not be dropped"

    empty_reason_entries = [
        p for p in parks if p.get("reason") in (None, "")
    ]
    assert len(empty_reason_entries) >= 1, (
        "expected at least one entry with empty/None reason for the empty-error park"
    )

    # Confirm the renderer would surface "(no reason recorded)" rather than
    # silently omitting the row — the entry must be present (asserted above).
    # The rendering check is a structural presence assertion, not a re-implementation.
    assert any(p.get("reason") in (None, "") for p in parks), (
        "entry with empty reason must be present so renderer shows '(no reason recorded)'"
    )


# ---------------------------------------------------------------------------
# derive_rework
# ---------------------------------------------------------------------------


def test_rework_derived_from_repeated_stage_entry():
    """derive_rework counts exactly 1 park; classify_gate_attempts labels T4 first_try.

    Uses the same stale-READY fixture as test_attempt_after_ready_reentry_classifies_after_rework
    (fresh state per test).  Guards two contracts together:
      1. derive_rework returns exactly 1 (one error_history entry for REVIEWING).
      2. classify_gate_attempts uses the first-park boundary from error_history —
         the T4 attempt (before REVIEWING's park at T5) is first_try, not after_rework.

    The first_try-at-T4 assertion is intentionally duplicated here because this
    test guards the derive+classify pairing: if either function misreads the
    stale READY timestamp instead of the first error_history entry, the paired
    assertion catches it.
    """
    stage = "REVIEWING"
    spec = "test-spec"

    # Same timestamps as the stale-READY rebuild above.
    T0 = "2026-01-01T00:00:00+00:00"  # VALIDATING start
    T1 = "2026-01-01T00:01:00+00:00"  # VALIDATING first park (error_history[0])
    T2 = "2026-01-01T00:02:00+00:00"  # READY — VALIDATING's re-entry; stale for REVIEWING
    T3 = "2026-01-01T00:03:00+00:00"  # REVIEWING stage start
    T4 = "2026-01-01T00:04:00+00:00"  # gate fail — after stale READY(T2), before REVIEWING's park
    T5 = "2026-01-01T00:05:00+00:00"  # REVIEWING first park (error_history[1])
    T6 = "2026-01-01T00:06:00+00:00"  # gate pass — after REVIEWING's park

    state = capture_fixtures.build_state(
        spec=spec,
        stage_timestamps={
            "VALIDATING": T0,
            "READY": T2,       # stale — holds VALIDATING's re-entry, not REVIEWING's
            "REVIEWING": T3,
            "PARKED": T5,
        },
        error_history=[
            {"stage": "VALIDATING", "error": "early park", "timestamp": T1},
            {"stage": "REVIEWING", "error": "gate failed", "timestamp": T5},
        ],
        current_state="REVIEWING",
    )

    # Exact count: one error_history entry for REVIEWING.
    rework_count = report.derive_rework(state, stage)
    assert rework_count == 1, (
        f"expected derive_rework == 1 for one REVIEWING park entry, got {rework_count}"
    )

    # Same two events as the stale-READY rebuild.
    events = [
        capture_fixtures.build_event(
            "VERIFICATION_RESULT",
            source="task_completed",
            spec=spec,
            stage=stage,
            timestamp=T4,
            data={"tests_passed": False, "out_of_scope_files": []},
        ),
        capture_fixtures.build_event(
            "VERIFICATION_RESULT",
            source="task_completed",
            spec=spec,
            stage=stage,
            timestamp=T6,
            data={"tests_passed": True, "out_of_scope_files": []},
        ),
    ]

    attempts = report.classify_gate_attempts(events, state, stage)

    # Load-bearing first_try-at-T4 assertion: T4 < first-park(T5) → first_try.
    assert [a["phase"] for a in attempts] == ["first_try", "after_rework"], (
        f"expected phases ['first_try', 'after_rework'] but got "
        f"{[a['phase'] for a in attempts]!r}; "
        "pre-fix: stale READY(T2) < T4 misclassifies T4 as after_rework"
    )
    assert [a["passed"] for a in attempts] == [False, True], (
        f"expected passed [False, True] but got {[a['passed'] for a in attempts]!r}"
    )


def test_two_parks_boundary_is_first_park():
    """First-park boundary is stable across a second park and later transitions.

    A stage that parks twice still uses its FIRST park timestamp as the
    after_rework boundary.  Any attempt that falls between the second park and
    the first park is after_rework (the re-entry after the first park already
    crossed the boundary), and the boundary does not advance to the second park.

    Boundary-stability note: this test may be green at the pre-fix commit because
    the pre-fix READY-based fallback also labels post-park attempts after_rework
    in the straightforward single-stage case.  The red demonstration for AC-06
    is carried by the two stale-READY rebuilds above.  This test pins the
    first-park boundary-stability contract independently.

    Fixture shape — three error_history entries across two stages:
      T0 = 2026-01-01T00:00:00  VALIDATING start
      T1 = 2026-01-01T00:01:00  VALIDATING first park   (error_history[0])
      T2 = 2026-01-01T00:02:00  IMPLEMENTING stage start
      T2.5=2026-01-01T00:02:30  gate pass — before IMPLEMENTING's first park
      T3 = 2026-01-01T00:03:00  IMPLEMENTING first park (error_history[1]) — boundary
      T5 = 2026-01-01T00:05:00  gate fail — after first park, before second park
      T7 = 2026-01-01T00:07:00  IMPLEMENTING second park (error_history[2])
      T8 = 2026-01-01T00:08:00  READY — re-entry after second park
      T9 = 2026-01-01T00:09:00  gate pass — after second park
    """
    stage = "IMPLEMENTING"
    spec = "test-spec"

    T0  = "2026-01-01T00:00:00+00:00"  # VALIDATING start
    T1  = "2026-01-01T00:01:00+00:00"  # VALIDATING first park (error_history[0])
    T2  = "2026-01-01T00:02:00+00:00"  # IMPLEMENTING stage start
    T2h = "2026-01-01T00:02:30+00:00"  # gate pass — before IMPLEMENTING's first park
    T3  = "2026-01-01T00:03:00+00:00"  # IMPLEMENTING first park (error_history[1]) — boundary
    T5  = "2026-01-01T00:05:00+00:00"  # gate fail — between re-entry and second park
    T7  = "2026-01-01T00:07:00+00:00"  # IMPLEMENTING second park (error_history[2])
    T8  = "2026-01-01T00:08:00+00:00"  # READY — re-entry after second park
    T9  = "2026-01-01T00:09:00+00:00"  # gate pass — after second park

    events = [
        capture_fixtures.build_event(
            "VERIFICATION_RESULT",
            source="task_completed",
            spec=spec,
            stage=stage,
            timestamp=T2h,   # before IMPLEMENTING's first park — first_try
            data={"tests_passed": True, "out_of_scope_files": []},
        ),
        capture_fixtures.build_event(
            "VERIFICATION_RESULT",
            source="task_completed",
            spec=spec,
            stage=stage,
            timestamp=T5,    # between re-entry and second park — after_rework
            data={"tests_passed": False, "out_of_scope_files": []},
        ),
        capture_fixtures.build_event(
            "VERIFICATION_RESULT",
            source="task_completed",
            spec=spec,
            stage=stage,
            timestamp=T9,    # after second park — still after_rework (boundary did not advance)
            data={"tests_passed": True, "out_of_scope_files": []},
        ),
    ]

    state = capture_fixtures.build_state(
        spec=spec,
        stage_timestamps={
            "VALIDATING":   T0,  # VALIDATING visited
            "IMPLEMENTING": T2,  # IMPLEMENTING started
            "PARKED":       T7,  # last PARKED timestamp (second park)
            "READY":        T8,  # READY — re-entry after second park
        },
        error_history=[
            # VALIDATING's park — does not affect IMPLEMENTING boundary.
            {"stage": "VALIDATING",  "error": "early park",   "timestamp": T1},
            # IMPLEMENTING's first park — this is the boundary.
            {"stage": "IMPLEMENTING","error": "first park",   "timestamp": T3},
            # IMPLEMENTING's second park — must NOT advance the boundary.
            {"stage": "IMPLEMENTING","error": "second park",  "timestamp": T7},
        ],
        current_state="IMPLEMENTING",
    )

    # Exact phase order: first_try at T2.5, after_rework at T5, after_rework at T9.
    attempts = report.classify_gate_attempts(events, state, stage)
    assert [a["phase"] for a in attempts] == ["first_try", "after_rework", "after_rework"], (
        f"expected ['first_try', 'after_rework', 'after_rework'] but got "
        f"{[a['phase'] for a in attempts]!r}; "
        "boundary must be the first park (T3) and must not advance to the second park (T7)"
    )

    # Exact rework count: two error_history entries for IMPLEMENTING.
    rework_count = report.derive_rework(state, stage)
    assert rework_count == 2, (
        f"expected derive_rework == 2 for two IMPLEMENTING park entries, got {rework_count}"
    )


# ---------------------------------------------------------------------------
# Subagent identity filtering
# ---------------------------------------------------------------------------


def _write_persona(base_dir, filename, name_value):
    """Write a minimal .md persona file with a name: frontmatter key.

    Mirrors the canonical fixture shape used in tests/test_capture_known_agents.py:
    a *.md file whose leading frontmatter carries a ``name:`` value, which is
    exactly what known_agents.derive_known_agents reads.
    """
    import os

    path = os.path.join(str(base_dir), filename)
    with open(path, "w") as f:
        f.write(f"---\nname: {name_value}\n---\n\nPersona body.\n")
    return path


def test_subagent_count_excludes_unknown_identity(tmp_path, monkeypatch):
    """Subagent aggregate counts only SUBAGENT_STOP events with a known identity.

    The hook router writes SUBAGENT_STOP envelopes where `source` is always the
    literal "hook_router" (the writer name) and the agent identity lives in
    `data["agent_type"]` / `data["is_known_agent"]`.  The pre-fix implementation
    reads `ev.get("source") or ev.get("data", {}).get("agent_type")` — on a
    production envelope the truthy `source` ("hook_router") always wins and the
    identity fallback never fires, so the count is always 0.  This test pins the
    production envelope shape so it can only pass when the implementation reads
    the identity from `data`, not from `source`.

    The events are: one with a known identity in data (counted), one with an
    empty identity in data (excluded), and one with an unrecognised identity in
    data (excluded).  The aggregated count must equal 1, and the scan must report
    a live result (STALE_FALLBACK is False) rather than the hardcoded fallback.
    """
    from fbk.capture import known_agents

    # Sanity guard: the probe name must NOT be in the hardcoded fallback set,
    # otherwise the test could pass on the fallback path and prove nothing.
    scanned_identity = "fbk-scan-probe"
    assert scanned_identity not in known_agents.FALLBACK_AGENTS, (
        "probe identity must be absent from the fallback set so the test "
        "exercises the real scan, not the hardcoded fallback"
    )

    # Build a temporary persona directory and point the scan root at it.
    persona_dir = tmp_path / "agents"
    persona_dir.mkdir()
    _write_persona(persona_dir, "fbk-scan-probe.md", scanned_identity)
    monkeypatch.setenv("FBK_AGENTS_DIR", str(persona_dir))

    stage = "VALIDATING"
    spec = "test-spec"

    events = [
        # source is the router writer name; identity is only in data — counted.
        capture_fixtures.build_event(
            "SUBAGENT_STOP",
            source="hook_router",
            spec=spec,
            stage=stage,
            data={"agent_type": "fbk-scan-probe", "is_known_agent": True},
        ),
        # empty identity in data — excluded.
        capture_fixtures.build_event(
            "SUBAGENT_STOP",
            source="hook_router",
            spec=spec,
            stage=stage,
            data={"agent_type": "", "is_known_agent": False},
        ),
        # unrecognised identity in data — excluded.
        capture_fixtures.build_event(
            "SUBAGENT_STOP",
            source="hook_router",
            spec=spec,
            stage=stage,
            data={"agent_type": "random-unknown-bot", "is_known_agent": False},
        ),
    ]

    count = report.count_known_subagents(events)

    assert count == 1, (
        f"expected count 1 (only the scanned probe identity is known), got {count}"
    )

    # The count must have come from the live directory scan, not the fallback.
    assert known_agents.STALE_FALLBACK is False, (
        "count_known_subagents must derive the known set from the configured "
        "FBK_AGENTS_DIR scan, not the hardcoded fallback"
    )


def test_subagent_count_is_exact_over_production_envelopes(tmp_path, monkeypatch):
    """count_known_subagents returns the exact count of known-identity events.

    Two known personas (fbk-scan-probe-a and fbk-scan-probe-b) are written into
    a temp agents directory, which is then set as the scan root.  Three
    SUBAGENT_STOP events are built — all with source="hook_router" matching the
    production envelope shape — two with known identities and one with an
    unrecognised identity.  The function must return exactly 2.

    Red mechanics: the pre-fix implementation reads
    `ev.get("source") or ev.get("data", {}).get("agent_type")`.  On every
    production envelope source is the truthy literal "hook_router", so it always
    wins and the data fallback never fires.  "hook_router" is not a known agent,
    so the pre-fix count is exactly 0 and this test fails red as 0 != 2.
    """
    from fbk.capture import known_agents

    persona_dir = tmp_path / "agents"
    persona_dir.mkdir()
    _write_persona(persona_dir, "fbk-scan-probe-a.md", "fbk-scan-probe-a")
    _write_persona(persona_dir, "fbk-scan-probe-b.md", "fbk-scan-probe-b")
    monkeypatch.setenv("FBK_AGENTS_DIR", str(persona_dir))

    stage = "VALIDATING"
    spec = "test-spec"

    events = [
        capture_fixtures.build_event(
            "SUBAGENT_STOP",
            source="hook_router",
            spec=spec,
            stage=stage,
            data={"agent_type": "fbk-scan-probe-a", "is_known_agent": True},
        ),
        capture_fixtures.build_event(
            "SUBAGENT_STOP",
            source="hook_router",
            spec=spec,
            stage=stage,
            data={"agent_type": "fbk-scan-probe-b", "is_known_agent": True},
        ),
        capture_fixtures.build_event(
            "SUBAGENT_STOP",
            source="hook_router",
            spec=spec,
            stage=stage,
            data={"agent_type": "random-unknown-bot", "is_known_agent": False},
        ),
    ]

    count = report.count_known_subagents(events)

    assert count == 2, (
        f"expected exactly 2 known-agent events (probe-a and probe-b), got {count}"
    )


def test_stale_fallback_warning_fires_with_zero_subagent_events(
    tmp_path, monkeypatch, capsys
):
    """The stale-fallback warning fires even when no subagent events exist.

    The flag that drives this warning is set as a side effect of scanning the
    persona directory.  The per-event subagent count only triggers that scan
    while iterating SUBAGENT_STOP events, so a session with zero such events
    would otherwise never refresh the flag — it would keep whatever value the
    import-time scan left behind.

    This test reproduces that gap: it first drives a *healthy* scan (a real
    persona directory) so the flag reads non-stale, then repoints the scan root
    at a directory that does not exist and renders a table whose events contain
    no SUBAGENT_STOP entries.  The render path must perform its own scan so the
    now-stale flag is current and the warning is surfaced.  Without an explicit
    scan in the render path this assertion fails, because the flag stays at its
    healthy import-time value and the warning is wrongly omitted.
    """
    from fbk.capture import known_agents

    # 1. Drive a healthy scan so the flag starts out non-stale, mirroring a
    #    process whose import-time scan found a populated persona directory.
    healthy_dir = tmp_path / "agents"
    healthy_dir.mkdir()
    _write_persona(healthy_dir, "fbk-scan-probe.md", "fbk-scan-probe")
    monkeypatch.setenv("FBK_AGENTS_DIR", str(healthy_dir))
    assert known_agents.is_known_agent("fbk-scan-probe") is True
    assert known_agents.STALE_FALLBACK is False, (
        "precondition: the healthy scan must leave the flag non-stale"
    )

    # 2. Repoint the scan root at a directory that does not exist, so any fresh
    #    scan yields nothing and falls back to the hardcoded set (stale=True).
    nonexistent_dir = tmp_path / "no-such-agents-dir"
    monkeypatch.setenv("FBK_AGENTS_DIR", str(nonexistent_dir))

    # 3. Render a table whose events contain ZERO SUBAGENT_STOP entries, so the
    #    per-event count never triggers a scan on its own.
    spec = "test-spec"
    stage = "IMPLEMENTING"
    events = [
        capture_fixtures.build_event(
            "PIPELINE_COMMAND",
            source="chokepoint",
            spec=spec,
            stage=stage,
            data={
                "command_name": "task-completed",
                "args": ["task-01"],
                "outcome": "pass",
                "exit_code": 0,
                "duration": 0.1,
                "output": "",
            },
        ),
    ]
    assert not any(e.get("event_type") == "SUBAGENT_STOP" for e in events), (
        "the fixture must contain no SUBAGENT_STOP events for this test to "
        "exercise the zero-subagent path"
    )

    st = capture_fixtures.build_state(
        spec=spec,
        stage_timestamps={stage: "2026-01-01T00:00:00+00:00"},
        error_history=[],
        current_state=stage,
    )

    report._render_table(spec, events, st, {}, str(tmp_path))

    out = capsys.readouterr().out
    assert "stale agent fallback" in out, (
        "the stale-fallback warning must be surfaced in a zero-subagent "
        "session whose live scan root yields nothing; the render path must "
        "scan once unconditionally so the flag is current"
    )
