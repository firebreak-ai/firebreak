"""Structural asset tests for the coherence-review wiring in fbk-breakdown and fbk-implement (AC-12, AC-19, AC-20 wiring half).

Parses the literal text of two skill files to assert that the Wave 3
orchestrator-wiring tasks (task-40 / task-41) have landed three structural
contracts:

AC-12 (wiring half):
  fbk-breakdown/SKILL.md spawns the coherence review as a separate subagent
  after the task-reviewer checkpoint and before the breakdown gate.

AC-19:
  fbk-implement/SKILL.md runs coherence-gate as a prerequisite alongside the
  existing breakdown-gate check, so a direct /fbk-implement cannot start
  without an accepted coherence verdict.

AC-20 (wiring half):
  fbk-breakdown/SKILL.md invokes the task-review preset (not the old
  test-reviewer agent directly), reads task-review.md between the
  task-reviewer-gate and breakdown-gate calls, and names needs-revision as
  the blocking outcome.

All assertions are RED before task-40 / task-41 land the coherence-review and
task-review-wiring migrations. They pass after.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Asset paths
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parents[3]

_BREAKDOWN_SKILL = _REPO_ROOT / "assets" / "skills" / "fbk-breakdown" / "SKILL.md"
_IMPLEMENT_SKILL = _REPO_ROOT / "assets" / "skills" / "fbk-implement" / "SKILL.md"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_skill(path: Path) -> str:
    """Return the text of a skill file.

    Raises FileNotFoundError (red-phase failure) when the asset does not exist.
    """
    return path.read_text(encoding="utf-8")


def _offset(text: str, token: str) -> int:
    """Return the character offset of the first occurrence of token in text.

    Returns -1 when the token is not found, which causes ordering assertions
    to fail in a readable way (negative offset cannot satisfy < comparisons
    against a found positive offset without an explicit check).
    """
    return text.find(token)


def _first_of(text: str, *tokens: str) -> tuple[str, int]:
    """Return the first token found in text and its offset.

    Iterates tokens in order and returns (token, offset) for the first match.
    Returns ('', -1) when none of the tokens are found.
    """
    for token in tokens:
        idx = text.find(token)
        if idx != -1:
            return token, idx
    return "", -1


# ---------------------------------------------------------------------------
# AC-12 wiring half: coherence spawned after task-reviewer-gate, before breakdown-gate
# ---------------------------------------------------------------------------


class TestBreakdownSpawnsCoherenceAfterTaskReviewerBeforeGate:
    """fbk-breakdown/SKILL.md orders coherence between the two deterministic gate calls (AC-12 wiring half).

    Token ordering: offset(task-reviewer-gate) < offset(coherence token) < offset(breakdown-gate).
    RED before task-40 adds the coherence-review spawn to the breakdown skill.
    """

    def test_breakdown_spawns_coherence_after_task_reviewer_before_gate(self):
        """The coherence token appears after task-reviewer-gate and before breakdown-gate in the breakdown skill.

        Uses character offsets to verify the relative position of the coherence
        spawn instruction between the two deterministic gate anchors.
        """
        text = _read_skill(_BREAKDOWN_SKILL)

        off_task_reviewer_gate = _offset(text, "task-reviewer-gate")
        coherence_token, off_coherence = _first_of(text, "coherence-review", "coherence-gate")
        off_breakdown_gate = _offset(text, "breakdown-gate")

        assert off_task_reviewer_gate != -1, (
            "fbk-breakdown/SKILL.md must contain the token 'task-reviewer-gate'; "
            "it is the upstream anchor for the coherence spawn ordering check"
        )
        assert off_coherence != -1, (
            f"fbk-breakdown/SKILL.md must contain a coherence token "
            f"('coherence-review' or 'coherence-gate') to prove the coherence "
            f"spawn is present; neither token was found"
        )
        assert off_breakdown_gate != -1, (
            "fbk-breakdown/SKILL.md must contain the token 'breakdown-gate'; "
            "it is the downstream anchor for the coherence spawn ordering check"
        )

        assert off_task_reviewer_gate < off_coherence, (
            f"The coherence token ('{coherence_token}' at offset {off_coherence}) "
            f"must appear after 'task-reviewer-gate' (offset {off_task_reviewer_gate}); "
            f"coherence review must be positioned after the task-reviewer checkpoint"
        )
        assert off_coherence < off_breakdown_gate, (
            f"The coherence token ('{coherence_token}' at offset {off_coherence}) "
            f"must appear before 'breakdown-gate' (offset {off_breakdown_gate}); "
            f"coherence review must be positioned before the breakdown gate"
        )


# ---------------------------------------------------------------------------
# AC-12 wiring half: coherence is a separate subagent spawn, not an inline call
# ---------------------------------------------------------------------------


class TestBreakdownCoherenceIsASeparateSpawn:
    """fbk-breakdown/SKILL.md pairs the coherence token with a separate-subagent spawn instruction (AC-12 wiring half).

    The coherence region (within 600 characters of the coherence token) must
    contain both a spawn/subagent vocabulary token and a freshness/separation
    token.  Together they prove the coherence review runs in its own agent, not
    as an inline gate call within the breakdown agent's own context.

    RED before task-40 adds the spawn instruction.
    """

    _SPAWN_TOKENS = ("spawn", "subagent", "teammate")
    _FRESH_TOKENS = ("fresh", "separate", "cleared")
    _WINDOW = 600

    def test_breakdown_coherence_is_a_separate_spawn(self):
        """The coherence region in the breakdown skill contains a spawn token and a freshness/separation token.

        Both assertions together prove the wiring records a fresh spawn, not a
        bare gate call that could execute inline in the breakdown agent's context.
        """
        text = _read_skill(_BREAKDOWN_SKILL)

        coherence_token, off_coherence = _first_of(text, "coherence-review", "coherence-gate")
        assert off_coherence != -1, (
            "fbk-breakdown/SKILL.md must contain 'coherence-review' or 'coherence-gate' "
            "before the separate-spawn check can be evaluated; "
            "add the coherence spawn instruction (task-40)"
        )

        start = max(0, off_coherence - self._WINDOW)
        end = min(len(text), off_coherence + len(coherence_token) + self._WINDOW)
        region = text[start:end].lower()

        has_spawn_token = any(tok in region for tok in self._SPAWN_TOKENS)
        has_fresh_token = any(tok in region for tok in self._FRESH_TOKENS)

        assert has_spawn_token, (
            f"The coherence region (±{self._WINDOW} chars around '{coherence_token}') "
            f"must contain a spawn/subagent vocabulary token "
            f"(one of: {', '.join(self._SPAWN_TOKENS)}) to prove a subagent is spawned; "
            f"region: {region!r}"
        )
        assert has_fresh_token, (
            f"The coherence region (±{self._WINDOW} chars around '{coherence_token}') "
            f"must contain a freshness/separation token "
            f"(one of: {', '.join(self._FRESH_TOKENS)}) to prove the subagent is separate; "
            f"region: {region!r}"
        )


# ---------------------------------------------------------------------------
# AC-19: fbk-implement runs coherence-gate alongside breakdown-gate
# ---------------------------------------------------------------------------


class TestImplementRunsCoherenceGatePrerequisite:
    """fbk-implement/SKILL.md names coherence-gate as a prerequisite alongside breakdown-gate (AC-19).

    Both tokens must be present, proving the implement skill enforces coherence
    on its entry path, not only breakdown.

    RED before task-41 adds coherence-gate to the implement skill.
    """

    def test_implement_runs_coherence_gate_prerequisite(self):
        """fbk-implement/SKILL.md contains both 'coherence-gate' and 'breakdown-gate'.

        Their co-presence pins that the implement skill enforces both gates,
        not just the pre-existing breakdown gate.
        """
        text = _read_skill(_IMPLEMENT_SKILL)

        assert "coherence-gate" in text, (
            "fbk-implement/SKILL.md must contain the token 'coherence-gate' — "
            "the implement entry path must enforce a coherence verdict check "
            "alongside the existing breakdown-gate (task-41)"
        )
        assert "breakdown-gate" in text, (
            "fbk-implement/SKILL.md must contain the token 'breakdown-gate'; "
            "this is the existing prerequisite that coherence-gate must join"
        )


# ---------------------------------------------------------------------------
# AC-19: coherence-gate sits in the prerequisite region, not as a stray mention
# ---------------------------------------------------------------------------


class TestImplementCoherenceGateIsAPrerequisiteNotAMention:
    """The coherence-gate token in fbk-implement/SKILL.md sits near breakdown-gate in the prerequisite region (AC-19).

    The absolute character-offset distance between coherence-gate and
    breakdown-gate must be at most 600 characters.  A stray mention elsewhere
    in the document (e.g. in a narrative explanation) would not satisfy this
    proximity check.

    RED before task-41 adds coherence-gate adjacent to breakdown-gate.
    """

    _MAX_DISTANCE = 600

    def test_implement_coherence_gate_is_a_prerequisite_not_a_mention(self):
        """'coherence-gate' and 'breakdown-gate' are within 600 characters of each other in the implement skill.

        Proximity to the existing breakdown-gate anchor pins that coherence-gate
        appears in the same prerequisite block, not as an incidental mention.
        """
        text = _read_skill(_IMPLEMENT_SKILL)

        off_coherence_gate = _offset(text, "coherence-gate")
        off_breakdown_gate = _offset(text, "breakdown-gate")

        assert off_coherence_gate != -1, (
            "fbk-implement/SKILL.md must contain 'coherence-gate' "
            "before the proximity check can be evaluated; add it (task-41)"
        )
        assert off_breakdown_gate != -1, (
            "fbk-implement/SKILL.md must contain 'breakdown-gate'; "
            "this is the anchor for the prerequisite proximity check"
        )

        distance = abs(off_coherence_gate - off_breakdown_gate)
        assert distance <= self._MAX_DISTANCE, (
            f"'coherence-gate' (offset {off_coherence_gate}) and 'breakdown-gate' "
            f"(offset {off_breakdown_gate}) are {distance} characters apart; "
            f"they must be within {self._MAX_DISTANCE} characters so the check pins "
            f"the prerequisite block, not a stray mention elsewhere in the document"
        )


# ---------------------------------------------------------------------------
# AC-20 wiring half: breakdown invokes the task-review preset
# ---------------------------------------------------------------------------


class TestBreakdownInvokesTaskReviewPreset:
    """fbk-breakdown/SKILL.md invokes the task-review preset and names task-review.md (AC-20 wiring half).

    RED before task-40 swaps the old direct test-reviewer invocation for the
    unified task-review preset call.
    """

    def test_breakdown_invokes_task_review_preset(self):
        """fbk-breakdown/SKILL.md contains both the 'task-review' preset token and 'task-review.md'.

        Together they prove the breakdown skill invokes the named preset (not the
        old test-reviewer agent directly) and names the artifact that downstream
        gates read for the verdict.
        """
        text = _read_skill(_BREAKDOWN_SKILL)

        assert "task-review" in text, (
            "fbk-breakdown/SKILL.md must reference the 'task-review' preset — "
            "the breakdown wiring must invoke the unified preset, "
            "not the old test-reviewer agent directly (task-40)"
        )
        assert "task-review.md" in text, (
            "fbk-breakdown/SKILL.md must name 'task-review.md' as the artifact "
            "produced by the task-review preset — downstream gates read the verdict "
            "from this file (task-40)"
        )


# ---------------------------------------------------------------------------
# AC-20 wiring half: task-review.md is read between the two deterministic gate calls
# ---------------------------------------------------------------------------


class TestTaskReviewReadBetweenTaskReviewerGateAndBreakdownGate:
    """task-review.md is read after task-reviewer-gate and before breakdown-gate in the breakdown skill (AC-20 wiring half).

    Token ordering: offset(task-reviewer-gate) < offset(task-review.md) < offset(breakdown-gate).
    Shares the two gate anchors with the coherence ordering check; adds the
    task-review.md read position between them.

    RED before task-40 adds the task-review.md read step.
    """

    def test_task_review_read_between_task_reviewer_gate_and_breakdown_gate(self):
        """'task-review.md' appears after 'task-reviewer-gate' and before 'breakdown-gate' in the breakdown skill.

        This pins the position of the task-review.md read step: it happens
        after the deterministic gate succeeds and before the breakdown gate is run.
        """
        text = _read_skill(_BREAKDOWN_SKILL)

        off_task_reviewer_gate = _offset(text, "task-reviewer-gate")
        off_task_review_md = _offset(text, "task-review.md")
        off_breakdown_gate = _offset(text, "breakdown-gate")

        assert off_task_reviewer_gate != -1, (
            "fbk-breakdown/SKILL.md must contain 'task-reviewer-gate'; "
            "it is the upstream anchor for the task-review.md position check"
        )
        assert off_task_review_md != -1, (
            "fbk-breakdown/SKILL.md must contain 'task-review.md' — "
            "the breakdown wiring must name the artifact to read after the "
            "task-reviewer-gate checkpoint (task-40)"
        )
        assert off_breakdown_gate != -1, (
            "fbk-breakdown/SKILL.md must contain 'breakdown-gate'; "
            "it is the downstream anchor for the task-review.md position check"
        )

        assert off_task_reviewer_gate < off_task_review_md, (
            f"'task-review.md' (offset {off_task_review_md}) must appear after "
            f"'task-reviewer-gate' (offset {off_task_reviewer_gate}); "
            f"the artifact is read after the deterministic gate succeeds"
        )
        assert off_task_review_md < off_breakdown_gate, (
            f"'task-review.md' (offset {off_task_review_md}) must appear before "
            f"'breakdown-gate' (offset {off_breakdown_gate}); "
            f"the artifact is read before the breakdown gate is run"
        )


# ---------------------------------------------------------------------------
# AC-20 wiring half: needs-revision is named as blocking in the task-review region
# ---------------------------------------------------------------------------


class TestBreakdownNamesNeedsRevisionAsBlocking:
    """fbk-breakdown/SKILL.md names needs-revision as a blocking outcome in the task-review region (AC-20 wiring half).

    In the region between task-review.md and breakdown-gate, both 'needs-revision'
    and a blocking/return token ('block' or 'return') must co-occur.  This pins
    that a needs-revision verdict causes the breakdown to stop and return to the
    test task agent, not silently continue.

    RED before task-40 adds the needs-revision blocking instruction.
    """

    _BLOCK_TOKENS = ("block", "return")

    def test_breakdown_names_needs_revision_as_blocking(self):
        """'needs-revision' and a block/return token co-occur between 'task-review.md' and 'breakdown-gate'.

        The region is the slice of text from the first occurrence of
        'task-review.md' to the first occurrence of 'breakdown-gate'.  Both
        tokens must appear in that slice to prove needs-revision blocks the
        breakdown flow and returns to the test task agent.
        """
        text = _read_skill(_BREAKDOWN_SKILL)

        off_task_review_md = _offset(text, "task-review.md")
        off_breakdown_gate = _offset(text, "breakdown-gate")

        assert off_task_review_md != -1, (
            "fbk-breakdown/SKILL.md must contain 'task-review.md'; "
            "it is the start anchor for the needs-revision blocking region check"
        )
        assert off_breakdown_gate != -1, (
            "fbk-breakdown/SKILL.md must contain 'breakdown-gate'; "
            "it is the end anchor for the needs-revision blocking region check"
        )
        assert off_task_review_md < off_breakdown_gate, (
            f"'task-review.md' (offset {off_task_review_md}) must appear before "
            f"'breakdown-gate' (offset {off_breakdown_gate}); "
            f"the region between them cannot be extracted for the blocking check"
        )

        region = text[off_task_review_md:off_breakdown_gate].lower()

        assert "needs-revision" in region, (
            "The region between 'task-review.md' and 'breakdown-gate' in "
            "fbk-breakdown/SKILL.md must contain 'needs-revision'; "
            "the breakdown skill must name the blocking verdict value (task-40)"
        )

        has_block_token = any(tok in region for tok in self._BLOCK_TOKENS)
        assert has_block_token, (
            f"The region between 'task-review.md' and 'breakdown-gate' in "
            f"fbk-breakdown/SKILL.md must contain a blocking/return token "
            f"(one of: {', '.join(self._BLOCK_TOKENS)}) co-occurring with "
            f"'needs-revision'; this pins that needs-revision blocks the "
            f"breakdown flow and returns to the test task agent (task-40)"
        )
