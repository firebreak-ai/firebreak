"""Compose the existing sighting/verdict pipeline for explicitly bound readers."""

import copy
import hashlib
import json
import sys
from pathlib import Path

from .. import pipeline
from . import review
from .store import WorkflowError, atomic_json, confined, digest, read_json


def capture(binding, contributors):
    if binding is None:
        return None
    binding = dict(binding)
    if (
        binding.get("detector") not in contributors
        or binding.get("challenger") not in contributors
        or binding["detector"] == binding["challenger"]
    ):
        raise WorkflowError(
            "Bind distinct declared detector and challenger contributors."
        )
    if not binding.get("lens"):
        raise WorkflowError("Code-review binding requires a captured lens file.")
    lens = Path(binding["lens"]).resolve()
    pipeline.load_lens_matrix(lens)
    if binding.get("preset") is not None and binding["preset"] not in pipeline.load_presets():
        raise WorkflowError("Unknown code-review preset.")
    if binding.get("min_severity") not in pipeline.VALID_SEVERITIES:
        raise WorkflowError("Unknown code-review severity threshold.")
    return {
        key: binding[key]
        for key in ("detector", "challenger", "preset", "min_severity")
    } | {
        "lens_text": lens.read_text(),
        "pipeline_digest": hashlib.sha256(
            Path(pipeline.__file__).read_bytes()
        ).hexdigest(),
        "presets_digest": digest(pipeline.load_presets()),
    }


def check(binding):
    if binding and (
        binding["pipeline_digest"]
        != hashlib.sha256(Path(pipeline.__file__).read_bytes()).hexdigest()
        or binding["presets_digest"] != digest(pipeline.load_presets())
    ):
        raise WorkflowError("Code-review pipeline contract changed; start a new round.")


def _call(root, directory, execution, name, data, *args):
    """Run existing CLI with full output on disk, never a truncated stdout tail."""
    output = directory / (name + ".json")
    driver = (
        "import contextlib,runpy,sys; output=sys.argv.pop(1); "
        "target=sys.argv.pop(1); sys.argv[0]=target; "
        'stream=open(output,"w"); '
        'sys.stdout=stream; runpy.run_path(target,run_name="__main__")'
    )
    with review.command_scope(root):
        result = review.run_command(
            [
                sys.executable,
                "-c",
                driver,
                str(output),
                str(Path(pipeline.__file__).resolve()),
                *args,
            ],
            directory,
            execution.remaining(),
            json.dumps(data),
        )
    if result["exit_code"] != 0:
        raise WorkflowError(f"Code-review pipeline {name} failed: {result['stderr']}")
    value = read_json(output)
    if "REJECTED:" in result["stderr"] and (name != "kept" or not value):
        raise WorkflowError(
            f"Code-review pipeline {name} rejected invalid output: {result['stderr']}"
        )
    if not isinstance(value, list):
        raise WorkflowError(f"Code-review pipeline {name} did not produce an array.")
    return value, result["stderr"]


def detector_findings(binding, result):
    """Validate the test lens's evidence account without exposing it to challenge."""
    if "output_contract: test-findings-and-coverage" not in binding["lens_text"]:
        return result
    if not isinstance(result, dict) or set(result) != {"findings", "coverage"}:
        raise WorkflowError(
            "Test detector result requires findings (array) and coverage (nonempty array); "
            "an empty finding list alone does not document inspection."
        )
    coverage = result["coverage"]
    if not isinstance(coverage, list) or not coverage:
        raise WorkflowError("Test detector coverage must be a nonempty array of inspected obligations/checks.")
    for index, row in enumerate(coverage):
        if not isinstance(row, dict) or any(
            not isinstance(row.get(key), str) or not row[key].strip()
            for key in ("obligation", "evidence", "status")
        ) or row["status"] not in {"covered", "gap", "unknown", "not-applicable"}:
            raise WorkflowError(
                f"Test detector coverage[{index}] requires nonempty obligation and evidence "
                "strings and status: covered, gap, unknown, or not-applicable."
            )
    if not isinstance(result["findings"], list):
        raise WorkflowError("Test detector findings must be an array, including [] when none are found.")
    return result["findings"]


def prepare(root, record, directory, execution):
    binding = record["code_review"]
    check(binding)
    detector = record["contributors"][binding["detector"]]
    raw = read_json(confined(root, detector["result_path"]))["result"]
    raw = detector_findings(binding, raw)
    if not isinstance(raw, list) or any(not isinstance(item, dict) for item in raw):
        raise WorkflowError(
            "Code-review detector must return a complete sighting array."
        )
    # Coordinator-only pipeline artifacts live outside the challenger source copy.
    coordinator = directory.parent / (directory.name + "-pipeline")
    coordinator.mkdir()
    lens = coordinator / "lens.md"
    lens.write_text(binding["lens_text"])
    if binding["preset"] is None:
        kept, diagnostics = _call(
            root, coordinator, execution, "kept", raw, "validate", "--lens", str(lens)
        )
        kept, filtered = _call(
            root, coordinator, execution, "filtered", kept, "severity-filter",
            "--min-severity", binding["min_severity"]
        )
        diagnostics += filtered
    else:
        kept, diagnostics = _call(
            root, coordinator, execution, "kept", raw, "run", "--preset",
            binding["preset"], "--min-severity", binding["min_severity"],
            "--lens", str(lens)
        )
    normalized, _ = _call(root, coordinator, execution, "normalized", kept, "normalize")
    path = directory / "_review_inputs/normalized.json"
    path.parent.mkdir(exist_ok=True)
    atomic_json(path, normalized)
    required = ["_review_inputs/normalized.json", "_review_inputs/lens.md"]
    for item in normalized:
        ref = item.get("source_of_truth_ref", "")
        source = ref.split("#", 1)[0] if isinstance(ref, str) else ""
        if source in record["snapshot_files"]:
            required.append(source)
    return {
        "kept": kept,
        "normalized": normalized,
        "diagnostics": diagnostics,
        "detector_artifact_digest": detector["artifact_digest"],
        "directory": coordinator,
        "lens": lens,
        "required": required,
    }


def compose(root, directory, execution, prepared, response):
    verdicts = response["review"]["result"]
    if not isinstance(verdicts, list):
        raise WorkflowError(
            "Code-review challenger must return a complete verdict array."
        )
    verdicts, _ = _call(
        root,
        prepared["directory"],
        execution,
        "verdicts",
        verdicts,
        "validate-verdicts",
    )
    merged, _ = _call(
        root,
        prepared["directory"],
        execution,
        "merged",
        prepared["kept"],
        "rejoin",
        "--verdicts",
        str(prepared["directory"] / "verdicts.json"),
    )
    merged, _ = _call(
        root,
        prepared["directory"],
        execution,
        "validated",
        merged,
        "validate",
        "--lens",
        str(prepared["lens"]),
    )
    confirmed, diagnostics = _call(
        root, prepared["directory"], execution, "confirmed", merged, "keep-confirmed"
    )
    return {
        **response,
        "review": {**response["review"], "result": merged},
        "pipeline": {
            "native_response": copy.deepcopy(response),
            "kept": prepared["kept"],
            "normalized": prepared["normalized"],
            "confirmed": confirmed,
            "detector_artifact_digest": prepared["detector_artifact_digest"],
            "diagnostics": prepared["diagnostics"] + diagnostics,
        },
    }
