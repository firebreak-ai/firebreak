"""Robustness tests for pipeline subcommands — malformed input handling.

Covers the six confirmed defects from the code-review-exec-path feature review:
  F-01  cmd_rejoin: missing or malformed verdicts file raises clean error, not traceback
  F-02  _check_verdict: null/non-string verification_evidence or rejection_reason
  F-03  _merge_finding_with_verdict: reclassified_from set but verdict missing type or severity
  F-04  cmd_normalize, cmd_validate_verdicts, cmd_rejoin: non-dict element in array

All assertions follow the binding contract from the feature spec (AC-03/04/09/15 and
IF-S-01/IF-S-03):
  - Exit code non-zero (not a crash)
  - Stderr names the offending path/record/index
  - No Python traceback in stderr ("Traceback" must not appear)
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _fbk_py():
    """Return the absolute path to the fbk.py dispatcher."""
    return Path(__file__).parent.parent / "fbk.py"


def _run(subcommand_args, stdin_text="[]", timeout=15):
    """Run `fbk.py pipeline <subcommand_args>` with stdin_text as input.

    Returns the CompletedProcess so callers can inspect returncode, stdout, stderr.
    """
    fbk_py = _fbk_py()
    if not fbk_py.exists():
        pytest.skip("fbk.py dispatcher not found")

    cmd = [sys.executable, str(fbk_py), "pipeline"] + subcommand_args
    return subprocess.run(
        cmd,
        input=stdin_text,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _run_rejoin(kept_list, verdicts_list_or_path, tmp_path=None):
    """Run `fbk.py pipeline rejoin` with kept_list on stdin.

    Pass a list for verdicts_list_or_path to write it to a temp file.
    Pass a string path to use that path directly (e.g., a nonexistent path).
    """
    fbk_py = _fbk_py()
    if not fbk_py.exists():
        pytest.skip("fbk.py dispatcher not found")

    if isinstance(verdicts_list_or_path, list):
        assert tmp_path is not None, "tmp_path required when passing a verdicts list"
        verdicts_file = tmp_path / "verdicts.json"
        verdicts_file.write_text(json.dumps(verdicts_list_or_path))
        verdicts_path = str(verdicts_file)
    else:
        verdicts_path = verdicts_list_or_path

    return subprocess.run(
        [sys.executable, str(fbk_py), "pipeline", "rejoin", "--verdicts", verdicts_path],
        input=json.dumps(kept_list),
        capture_output=True,
        text=True,
        timeout=15,
    )


def _kept_finding(index=0):
    """Return a minimal well-formed kept finding."""
    return {
        "id": f"F-0{index + 1}",
        "title": f"Kept finding {index} with sufficient title text",
        "location": {"file": f"src/module_{index}.py", "start_line": 10 + index},
        "type": "behavioral",
        "severity": "major",
        "mechanism": f"MECHANISM-KEPT-{index}-AAAAAAAAAA",
        "consequence": f"CONSEQUENCE-KEPT-{index}-AAAAAAAAAA",
        "evidence": f"EVIDENCE-KEPT-{index}-AAAAAAAAAA",
        "source_of_truth_ref": "",
    }


def _assert_clean_error(result, offending_label):
    """Assert a clean in-band error: exit 1, offending label in stderr, no traceback."""
    assert result.returncode != 0, (
        f"Expected non-zero exit; got {result.returncode}. stderr: {result.stderr!r}"
    )
    assert offending_label in result.stderr, (
        f"Expected stderr to name {offending_label!r}; got: {result.stderr!r}"
    )
    assert "Traceback" not in result.stderr, (
        f"Expected no Python traceback in stderr; got: {result.stderr!r}"
    )


# ---------------------------------------------------------------------------
# F-01: cmd_rejoin — missing or malformed verdicts file
# ---------------------------------------------------------------------------


class TestRejoinVerdictFileErrors:
    """cmd_rejoin produces a clean named error for missing or malformed verdicts files."""

    def test_nonexistent_verdicts_file_exits_cleanly_naming_path(self, tmp_path):
        """A nonexistent verdicts file path produces a named stderr message, not a traceback.

        Reproduces: FileNotFoundError traceback from json.loads(Path(...).read_text())
        Contract: exit 1, path named in stderr, no Traceback
        """
        missing_path = str(tmp_path / "does_not_exist.json")
        kept = [_kept_finding(0)]

        result = _run_rejoin(kept, missing_path)

        _assert_clean_error(result, missing_path)

    def test_malformed_json_in_verdicts_file_exits_cleanly_naming_path(self, tmp_path):
        """Malformed JSON in the verdicts file produces a named stderr message, not a traceback.

        Reproduces: json.JSONDecodeError traceback from json.loads(...)
        Contract: exit 1, path named in stderr, no Traceback
        """
        bad_json_file = tmp_path / "bad.json"
        bad_json_file.write_text("this is not valid json {{{")
        kept = [_kept_finding(0)]

        result = _run_rejoin(kept, str(bad_json_file))

        _assert_clean_error(result, str(bad_json_file))


# ---------------------------------------------------------------------------
# F-02: _check_verdict — null/non-string evidence or reason
# ---------------------------------------------------------------------------


class TestCheckVerdictNullStringFields:
    """_check_verdict produces a named error when evidence or reason is null or non-string."""

    def test_null_verification_evidence_exits_naming_index(self):
        """A verified verdict with null verification_evidence exits 1 naming position 0.

        Reproduces: TypeError: object of type 'NoneType' has no len()
        Contract: exit 1, index named in stderr, no Traceback
        """
        verdicts = [{"status": "verified", "verification_evidence": None}]
        result = _run(["validate-verdicts"], stdin_text=json.dumps(verdicts))

        _assert_clean_error(result, "0")

    def test_non_string_verification_evidence_exits_naming_index(self):
        """A verified verdict with an integer verification_evidence exits 1 naming position 0.

        Guards against non-string (e.g. integer) verification_evidence bypassing the check.
        Contract: exit 1, index named in stderr, no Traceback
        """
        verdicts = [{"status": "verified", "verification_evidence": 42}]
        result = _run(["validate-verdicts"], stdin_text=json.dumps(verdicts))

        _assert_clean_error(result, "0")

    def test_null_rejection_reason_exits_naming_index(self):
        """A rejected verdict with null rejection_reason exits 1 naming position 0.

        Reproduces: TypeError on len(None) when rejection_reason is explicitly null.
        Contract: exit 1, index named in stderr, no Traceback
        """
        verdicts = [{"status": "rejected", "rejection_reason": None}]
        result = _run(["validate-verdicts"], stdin_text=json.dumps(verdicts))

        _assert_clean_error(result, "0")

    def test_non_string_rejection_reason_exits_naming_index(self):
        """A rejected verdict with an integer rejection_reason exits 1 naming position 0.

        Contract: exit 1, index named in stderr, no Traceback
        """
        verdicts = [{"status": "rejected", "rejection_reason": 99}]
        result = _run(["validate-verdicts"], stdin_text=json.dumps(verdicts))

        _assert_clean_error(result, "0")

    def test_second_verdict_null_evidence_names_index_1(self):
        """When the second verdict has null evidence, stderr names index 1 (not 0).

        Confirms the error names the actual offending position, not always 0.
        Contract: exit 1, "1" in stderr (the offending index), no Traceback
        """
        verdicts = [
            {"status": "verified", "verification_evidence": "sufficient evidence text"},
            {"status": "verified", "verification_evidence": None},
        ]
        result = _run(["validate-verdicts"], stdin_text=json.dumps(verdicts))

        _assert_clean_error(result, "1")


# ---------------------------------------------------------------------------
# F-03: _merge_finding_with_verdict — reclassified_from set but missing type/severity
# ---------------------------------------------------------------------------


class TestMergeReclassificationMissingFields:
    """cmd_rejoin produces a named error when reclassified_from is set but type or severity is absent."""

    def test_reclassified_from_set_but_type_missing_exits_naming_index(self, tmp_path):
        """A verdict with reclassified_from set but no 'type' key exits 1 naming index 0.

        Reproduces: KeyError: 'type' inside _merge_finding_with_verdict
        Contract: exit 1, "0" in stderr, no Traceback
        """
        kept = [_kept_finding(0)]
        verdicts = [
            {
                "status": "verified",
                "verification_evidence": "sufficient evidence text here",
                "reclassified_from": {"type": "behavioral", "severity": "major"},
                # "type" key is intentionally absent from the verdict
                "severity": "minor",
            }
        ]

        result = _run_rejoin(kept, verdicts, tmp_path)

        _assert_clean_error(result, "0")

    def test_reclassified_from_set_but_severity_missing_exits_naming_index(self, tmp_path):
        """A verdict with reclassified_from set but no 'severity' key exits 1 naming index 0.

        Reproduces: KeyError: 'severity' inside _merge_finding_with_verdict
        Contract: exit 1, "0" in stderr, no Traceback
        """
        kept = [_kept_finding(0)]
        verdicts = [
            {
                "status": "verified",
                "verification_evidence": "sufficient evidence text here",
                "reclassified_from": {"type": "behavioral", "severity": "major"},
                "type": "structural",
                # "severity" key is intentionally absent from the verdict
            }
        ]

        result = _run_rejoin(kept, verdicts, tmp_path)

        _assert_clean_error(result, "0")

    def test_reclassified_from_second_verdict_names_index_1(self, tmp_path):
        """When the second verdict triggers the reclassification error, stderr names index 1.

        Confirms the error names the actual offending position, not always 0.
        Contract: exit 1, "1" in stderr, no Traceback
        """
        kept = [_kept_finding(i) for i in range(2)]
        verdicts = [
            {
                "status": "verified",
                "verification_evidence": "sufficient evidence text here",
            },
            {
                "status": "verified",
                "verification_evidence": "sufficient evidence text here",
                "reclassified_from": {"type": "behavioral", "severity": "major"},
                # "type" and "severity" intentionally absent from this verdict
            },
        ]

        result = _run_rejoin(kept, verdicts, tmp_path)

        _assert_clean_error(result, "1")


# ---------------------------------------------------------------------------
# F-04: non-dict element in array — normalize, validate-verdicts, rejoin
# ---------------------------------------------------------------------------


class TestNonDictElementInArray:
    """Each iterable command produces a clean named error for a non-dict element."""

    # --- cmd_normalize ---

    def test_normalize_null_element_exits_naming_index(self):
        """cmd_normalize with null element at index 0 exits 1 naming position 0.

        Reproduces: AttributeError: 'NoneType' object has no attribute 'get'
        Contract: exit 1, "0" in stderr, no Traceback
        """
        findings = [None]
        result = _run(["normalize"], stdin_text=json.dumps(findings))

        _assert_clean_error(result, "0")

    def test_normalize_non_dict_at_second_position_names_index_1(self):
        """cmd_normalize with null element at index 1 exits 1 naming position 1.

        Confirms the error names the actual offending position, not always 0.
        Contract: exit 1, "1" in stderr, no Traceback
        """
        finding = {
            "mechanism": "Token written to world-readable file path",
            "consequence": "Any process can read the token",
            "evidence": "auth.py:42 — open call",
            "type": "behavioral",
            "severity": "critical",
            "source_of_truth_ref": "",
            "location": {"file": "auth.py", "start_line": 42},
        }
        findings = [finding, None]
        result = _run(["normalize"], stdin_text=json.dumps(findings))

        _assert_clean_error(result, "1")

    # --- cmd_validate_verdicts ---

    def test_validate_verdicts_null_element_exits_naming_index(self):
        """cmd_validate_verdicts with null element at index 0 exits 1 naming position 0.

        Reproduces: AttributeError: 'NoneType' object has no attribute 'get' in _check_verdict
        Contract: exit 1, "0" in stderr, no Traceback
        """
        verdicts = [None]
        result = _run(["validate-verdicts"], stdin_text=json.dumps(verdicts))

        _assert_clean_error(result, "0")

    def test_validate_verdicts_integer_element_exits_naming_index(self):
        """cmd_validate_verdicts with an integer element exits 1 naming position 0.

        Integers are also non-dict: guards that the check is not None-specific.
        Contract: exit 1, "0" in stderr, no Traceback
        """
        verdicts = [42]
        result = _run(["validate-verdicts"], stdin_text=json.dumps(verdicts))

        _assert_clean_error(result, "0")

    def test_validate_verdicts_non_dict_at_second_position_names_index_1(self):
        """cmd_validate_verdicts with null at index 1 exits 1 naming position 1.

        Confirms the error names the actual offending position, not always 0.
        Contract: exit 1, "1" in stderr, no Traceback
        """
        verdicts = [
            {"status": "verified", "verification_evidence": "sufficient evidence text here"},
            None,
        ]
        result = _run(["validate-verdicts"], stdin_text=json.dumps(verdicts))

        _assert_clean_error(result, "1")

    # --- cmd_rejoin (kept side) ---

    def test_rejoin_null_in_kept_exits_naming_index(self, tmp_path):
        """cmd_rejoin with null in kept findings exits 1 naming position 0.

        Reproduces: TypeError: 'NoneType' object is not iterable in dict(kept)
        Contract: exit 1, "0" in stderr, no Traceback
        """
        kept = [None]
        verdicts = [
            {"status": "verified", "verification_evidence": "sufficient evidence here"}
        ]

        result = _run_rejoin(kept, verdicts, tmp_path)

        _assert_clean_error(result, "0")

    def test_rejoin_null_in_verdicts_file_exits_naming_index(self, tmp_path):
        """cmd_rejoin with null in the verdicts file exits 1 naming position 0.

        Guards that the verdicts array is also element-type-checked.
        Contract: exit 1, "0" in stderr, no Traceback
        """
        verdicts_file = tmp_path / "verdicts.json"
        verdicts_file.write_text(json.dumps([None]))
        kept = [_kept_finding(0)]

        result = _run_rejoin(kept, str(verdicts_file))

        _assert_clean_error(result, "0")


# ---------------------------------------------------------------------------
# F-06: adjacent_observations rendered by pipeline to-markdown
# ---------------------------------------------------------------------------


class TestToMarkdownAdjacentObservations:
    """pipeline to-markdown renders adjacent_observations when present, omits it when absent."""

    def _make_finding(self, **extra):
        """Return a minimal finding suitable for to-markdown rendering."""
        base = {
            "id": "F-01",
            "title": "Test finding title text here",
            "location": {"file": "src/module.py", "start_line": 10},
            "type": "behavioral",
            "severity": "major",
            "mechanism": "Mechanism description for the finding",
            "consequence": "Consequence description for the finding",
            "evidence": "Evidence text for the finding",
            "status": "verified",
            "verification_evidence": "Verification evidence text here",
        }
        base.update(extra)
        return base

    def test_adjacent_observations_rendered_when_present(self):
        """A finding with adjacent_observations renders the field under the finding.

        Asserts the structural marker 'Adjacent observations' appears in stdout
        and the observation text is present. The field is absent from the input
        when not set (existing tests must stay green).
        """
        obs_text = "Observed related issue in sibling module suggesting broader pattern"
        finding = self._make_finding(adjacent_observations=obs_text)

        result = _run(["to-markdown"], stdin_text=json.dumps([finding]))

        assert result.returncode == 0, (
            f"Expected exit 0; got {result.returncode}. stderr: {result.stderr!r}"
        )
        assert "Adjacent observations" in result.stdout, (
            f"Expected 'Adjacent observations' in stdout; got: {result.stdout!r}"
        )
        assert obs_text in result.stdout, (
            f"Expected observation text in stdout; got: {result.stdout!r}"
        )

    def test_adjacent_observations_absent_when_field_not_set(self):
        """A finding without adjacent_observations does not produce the field in output.

        Validates that adding adjacent_observations support does not alter output
        for findings that do not carry the field — existing tests stay green.
        """
        finding = self._make_finding()  # no adjacent_observations key

        result = _run(["to-markdown"], stdin_text=json.dumps([finding]))

        assert result.returncode == 0, (
            f"Expected exit 0; got {result.returncode}. stderr: {result.stderr!r}"
        )
        assert "Adjacent observations" not in result.stdout, (
            f"Expected no 'Adjacent observations' section in stdout for finding "
            f"without that field; got: {result.stdout!r}"
        )
