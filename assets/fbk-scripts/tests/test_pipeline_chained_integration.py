"""Chained integration test: full eight-stage pipeline without live agents.

Proves that successive `fbk.py pipeline` subcommands compose correctly end to end:
  validate --lens | severity-filter | normalize | validate-verdicts | rejoin --verdicts | validate --lens

Each stage feeds the previous stage's stdout as its own stdin (via subprocess.run).
No mocks — this exercises the real CLI contract between stages.

RED PHASE: The new subcommands (validate --lens, normalize, validate-verdicts, rejoin --verdicts)
do not exist yet.  This test will fail until all four are implemented.
"""

import json
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fbk_py() -> Path:
    """Return the absolute path to the fbk.py dispatcher."""
    return Path(__file__).parent.parent / "fbk.py"


def _lens(name: str) -> Path:
    """Return the repo-relative path to the named review lens file.

    name should be the lens stem, e.g. "code-lens" or "test-lens".
    """
    return Path(__file__).parents[3] / "assets" / "fbk-docs" / "fbk-review-lenses" / f"{name}.md"


def _stage(args: list, stdin_text: str):
    """Run one `fbk.py pipeline <args>` stage, feeding stdin_text as input.

    Returns the CompletedProcess so callers can inspect returncode, stdout, stderr.
    Hard timeout: 15 seconds per stage.
    """
    import subprocess
    fbk_py = _fbk_py()
    if not fbk_py.exists():
        pytest.skip("fbk.py dispatcher not found")
    return subprocess.run(
        [sys.executable, str(fbk_py), "pipeline"] + args,
        input=stdin_text,
        capture_output=True,
        text=True,
        timeout=15,
    )


# ---------------------------------------------------------------------------
# Candidate fixture
#
# Three findings that are all valid under the code-lens matrix at or above
# "major" threshold.  Each carries a DISTINCT mechanism sentinel so
# index-to-index position is provable.
#
# code-lens valid combinations at or above major:
#   behavioral+critical, behavioral+major, fragile+major
# ---------------------------------------------------------------------------

_CANDIDATE_FINDINGS = [
    {
        "title": "Sentinel-Alpha finding title long enough",
        "location": {"file": "src/auth.py", "start_line": 10},
        "type": "behavioral",
        "severity": "critical",
        "mechanism": "SENTINEL-ALPHA: token written to world-readable file without umask",
        "consequence": "Any local process can read the token and impersonate the user.",
        "evidence": "auth.py:10 — open('/tmp/tok', 'w') called before umask set",
    },
    {
        "title": "Sentinel-Beta finding title long enough",
        "location": {"file": "src/config.py", "start_line": 42},
        "type": "behavioral",
        "severity": "major",
        "mechanism": "SENTINEL-BETA: hardcoded password literal in config module",
        "consequence": "Password exposed in version control and any readable config dump.",
        "evidence": "config.py:42 — password = 'hunter2' literal in module scope",
    },
    {
        "title": "Sentinel-Gamma finding title long enough",
        "location": {"file": "src/parser.py", "start_line": 77},
        "type": "fragile",
        "severity": "major",
        "mechanism": "SENTINEL-GAMMA: missing length guard before slice assumes non-empty list",
        "consequence": "IndexError on empty input, silently producing wrong state upstream.",
        "evidence": "parser.py:77 — items[0] accessed without prior len() guard",
    },
]

# Severity threshold used across stages 2 and onward.
_MIN_SEVERITY = "major"

# Chosen lens name (stem only; _lens() appends .md).
_LENS_NAME = "code-lens"

# The six neutral keys normalize() must emit.
_NORMALIZE_KEYS = frozenset({
    "mechanism", "consequence", "evidence", "type", "severity", "source_of_truth_ref"
})


# ---------------------------------------------------------------------------
# Test: full chained composition
#
# One test class, six sequential stages.  Stages are driven in order inside
# a single test to keep the shared "kept list" state explicit and linear.
# If any stage exits non-zero the test fails immediately at that stage.
# ---------------------------------------------------------------------------


class TestChainedIntegration:
    """End-to-end composition across all six pipeline stages.

    Covers:
    - AC-07: validate --lens | severity-filter composes (stages 1–2)
    - AC-08: normalize feeds cleanly between filter and challenge (stage 3)
    - AC-09: rejoin --verdicts lands verdicts index-to-index (stage 5)
    """

    def test_full_pipeline_chain(self, tmp_path):
        """validate --lens | severity-filter | normalize all exit zero with well-formed output;
        validate-verdicts exits zero over the per-kept-finding fixture; rejoin --verdicts lands
        each verdict on the correct finding by position; final validate --lens exits zero and
        yields re-validated well-formed records with S-NN ids.

        Sentinel mechanism strings (SENTINEL-ALPHA, SENTINEL-BETA, SENTINEL-GAMMA) and distinct
        status+evidence sentinels make index-to-index correctness observable in the assertions.
        """
        lens_path = _lens(_LENS_NAME)
        if not lens_path.exists():
            pytest.skip(f"lens file not found: {lens_path}")

        # ------------------------------------------------------------------
        # Stage 1: validate --lens <lens> over the candidate findings.
        # Assigns S-NN ids and validates each finding against the lens matrix.
        # ------------------------------------------------------------------
        stage1 = _stage(
            ["validate", "--lens", str(lens_path)],
            json.dumps(_CANDIDATE_FINDINGS),
        )
        assert stage1.returncode == 0, (
            f"Stage 1 (validate --lens) exited {stage1.returncode}. "
            f"stderr: {stage1.stderr!r}"
        )

        kept_list = json.loads(stage1.stdout)
        assert isinstance(kept_list, list), (
            f"Stage 1 stdout must be a JSON list, got: {type(kept_list)}"
        )
        assert len(kept_list) == len(_CANDIDATE_FINDINGS), (
            f"Stage 1 should keep all {len(_CANDIDATE_FINDINGS)} valid candidates, "
            f"got {len(kept_list)}"
        )
        # Each kept record must carry an S-NN id after validate.
        for i, record in enumerate(kept_list):
            assert "id" in record and record["id"].startswith("S-"), (
                f"Stage 1 record {i} must have an S-NN id, got: {record.get('id')!r}"
            )

        # ------------------------------------------------------------------
        # Stage 2: severity-filter --min-severity major over kept_list.
        # All three candidates are at major or above — all should survive.
        # ------------------------------------------------------------------
        stage2 = _stage(
            ["severity-filter", "--min-severity", _MIN_SEVERITY],
            json.dumps(kept_list),
        )
        assert stage2.returncode == 0, (
            f"Stage 2 (severity-filter) exited {stage2.returncode}. "
            f"stderr: {stage2.stderr!r}"
        )

        survivors = json.loads(stage2.stdout)
        assert isinstance(survivors, list), (
            f"Stage 2 stdout must be a JSON list, got: {type(survivors)}"
        )
        # All three candidates are at major or critical — expect all to survive.
        assert len(survivors) == len(_CANDIDATE_FINDINGS), (
            f"Stage 2 should retain all {len(_CANDIDATE_FINDINGS)} above-threshold "
            f"candidates, got {len(survivors)}"
        )
        # Sentinels must survive in original order.
        expected_sentinels = [
            "SENTINEL-ALPHA",
            "SENTINEL-BETA",
            "SENTINEL-GAMMA",
        ]
        for i, record in enumerate(survivors):
            assert expected_sentinels[i] in record["mechanism"], (
                f"Stage 2 record {i} mechanism should contain {expected_sentinels[i]!r}, "
                f"got: {record['mechanism']!r}"
            )

        # ------------------------------------------------------------------
        # Stage 3: normalize over survivors.
        # Each normalized record must carry exactly the six neutral keys.
        # ------------------------------------------------------------------
        stage3 = _stage(
            ["normalize"],
            json.dumps(survivors),
        )
        assert stage3.returncode == 0, (
            f"Stage 3 (normalize) exited {stage3.returncode}. "
            f"stderr: {stage3.stderr!r}"
        )

        normalized = json.loads(stage3.stdout)
        assert isinstance(normalized, list), (
            f"Stage 3 stdout must be a JSON list, got: {type(normalized)}"
        )
        assert len(normalized) == len(survivors), (
            f"Stage 3 must emit one record per input, got {len(normalized)} for "
            f"{len(survivors)} survivors"
        )
        for i, record in enumerate(normalized):
            # Upper bound: exactly six keys, no extra fields.
            assert len(record) == 6, (
                f"Stage 3 record {i} must have exactly 6 keys, got {len(record)}: "
                f"{set(record.keys())}"
            )
            # Lower bound: every required key is present.
            assert set(record.keys()) == _NORMALIZE_KEYS, (
                f"Stage 3 record {i} keys {set(record.keys())} != expected {_NORMALIZE_KEYS}"
            )

        # ------------------------------------------------------------------
        # Stage 4: build verdict fixture; run validate-verdicts over it.
        #
        # One verdict per kept finding (survivors), same order.  Each verdict
        # carries a distinct status + ≥10-char sentinel to make position
        # traceable.
        #
        # The orchestrator retains the survivors (with id fields) as its kept
        # record store; the normalized records are what the challenger received.
        # We attach verdicts keyed back to the survivors order.
        # ------------------------------------------------------------------
        verdict_sentinels = [
            {
                "status": "verified",
                "verification_evidence": "VERDICT-ALPHA-EVIDENCE: independently confirmed via log trace at auth.py:10",
            },
            {
                "status": "verified",
                "verification_evidence": "VERDICT-BETA-EVIDENCE: password literal confirmed in git blame config.py:42",
            },
            {
                "status": "rejected",
                "rejection_reason": "VERDICT-GAMMA-REJECTION: guard added in adjacent commit, not present in diff",
            },
        ]

        verdict_fixture_path = tmp_path / "verdicts.json"
        verdict_fixture_path.write_text(json.dumps(verdict_sentinels))

        stage4 = _stage(
            ["validate-verdicts"],
            json.dumps(verdict_sentinels),
        )
        assert stage4.returncode == 0, (
            f"Stage 4 (validate-verdicts) exited {stage4.returncode}. "
            f"stderr: {stage4.stderr!r}"
        )

        # validate-verdicts passes the fixture through unchanged.
        validated_verdicts = json.loads(stage4.stdout)
        assert isinstance(validated_verdicts, list), (
            f"Stage 4 stdout must be a JSON list, got: {type(validated_verdicts)}"
        )
        assert len(validated_verdicts) == len(verdict_sentinels), (
            f"Stage 4 must pass through all {len(verdict_sentinels)} verdicts, "
            f"got {len(validated_verdicts)}"
        )

        # ------------------------------------------------------------------
        # Stage 5: rejoin --verdicts <fixture> with kept findings on stdin.
        # Output length must equal kept count; each merged record i must carry
        # finding i's sentinel mechanism AND verdict i's sentinel evidence.
        # ------------------------------------------------------------------
        stage5 = _stage(
            ["rejoin", "--verdicts", str(verdict_fixture_path)],
            json.dumps(survivors),
        )
        assert stage5.returncode == 0, (
            f"Stage 5 (rejoin --verdicts) exited {stage5.returncode}. "
            f"stderr: {stage5.stderr!r}"
        )

        merged = json.loads(stage5.stdout)
        assert isinstance(merged, list), (
            f"Stage 5 stdout must be a JSON list, got: {type(merged)}"
        )
        # Output length equals kept count.
        assert len(merged) == len(survivors), (
            f"Stage 5 must emit one merged record per kept finding, got {len(merged)} "
            f"for {len(survivors)} kept findings"
        )

        # Index-to-index landing: merged[i] carries finding[i]'s mechanism sentinel
        # AND verdict[i]'s sentinel (evidence or rejection_reason).
        finding_sentinels = ["SENTINEL-ALPHA", "SENTINEL-BETA", "SENTINEL-GAMMA"]
        verdict_evidence_sentinels = [
            "VERDICT-ALPHA-EVIDENCE",
            "VERDICT-BETA-EVIDENCE",
            "VERDICT-GAMMA-REJECTION",
        ]
        for i, record in enumerate(merged):
            # Finding sentinel present in mechanism.
            assert finding_sentinels[i] in record.get("mechanism", ""), (
                f"Stage 5 merged record {i} mechanism must contain "
                f"{finding_sentinels[i]!r}, got: {record.get('mechanism')!r}"
            )
            # Verdict sentinel present in verification_evidence or rejection_reason.
            combined_verdict_text = (
                record.get("verification_evidence", "")
                + record.get("rejection_reason", "")
            )
            assert verdict_evidence_sentinels[i] in combined_verdict_text, (
                f"Stage 5 merged record {i} must carry verdict sentinel "
                f"{verdict_evidence_sentinels[i]!r} in verification_evidence or "
                f"rejection_reason, got: {combined_verdict_text!r}"
            )

        # ------------------------------------------------------------------
        # Stage 6: validate --lens <lens> over merged records.
        # Expects exit zero; output is a well-formed list of re-validated
        # records each carrying an S-NN id and lens-required fields.
        # ------------------------------------------------------------------
        stage6 = _stage(
            ["validate", "--lens", str(lens_path)],
            json.dumps(merged),
        )
        assert stage6.returncode == 0, (
            f"Stage 6 (final validate --lens) exited {stage6.returncode}. "
            f"stderr: {stage6.stderr!r}"
        )

        final_output = json.loads(stage6.stdout)
        assert isinstance(final_output, list), (
            f"Stage 6 stdout must be a JSON list, got: {type(final_output)}"
        )
        # Upper bound: non-empty (at least the verified findings survived).
        assert len(final_output) >= 1, (
            f"Stage 6 must produce at least one re-validated finding, got 0"
        )
        # Lower bound: well-formed — each record has S-NN id and lens-required fields.
        lens_required = {"title", "location", "type", "severity", "mechanism", "consequence", "evidence"}
        for i, record in enumerate(final_output):
            assert "id" in record and record["id"].startswith("S-"), (
                f"Stage 6 record {i} must carry an S-NN id, got: {record.get('id')!r}"
            )
            for field in lens_required:
                assert field in record, (
                    f"Stage 6 record {i} must carry lens-required field '{field}'"
                )
