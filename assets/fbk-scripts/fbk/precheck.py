"""Capability-entry prerequisite probe — returns structured missing-artifact info without blocking."""

import argparse
import json
from pathlib import Path


def check_prerequisites(phase: str, feature_dir: str) -> dict:
    feature_path = Path(feature_dir)
    feature_name = feature_path.name
    missing = []

    if phase == "design":
        if not (feature_path / "prd.md").exists():
            missing.append({"artifact": "prd.md", "upstream_phase": "intent"})
    elif phase == "spec":
        if not (feature_path / "design-manifest.md").exists():
            missing.append({"artifact": "design-manifest.md", "upstream_phase": "design"})
    elif phase == "breakdown":
        if not (feature_path / f"{feature_name}-spec.md").exists():
            missing.append({"artifact": f"{feature_name}-spec.md", "upstream_phase": "spec"})
    elif phase == "code-review":
        if not (feature_path / "implementation").is_dir():
            missing.append({"artifact": "implementation/", "upstream_phase": "implement"})

    return {"phase": phase, "ready": len(missing) == 0, "missing": missing}


def main() -> None:
    parser = argparse.ArgumentParser(description="Check prerequisites for an SDL phase.")
    parser.add_argument("phase", help="SDL phase name (e.g. design, spec, breakdown, code-review).")
    parser.add_argument("feature_dir", help="Path to the feature directory.")
    args = parser.parse_args()
    print(json.dumps(check_prerequisites(args.phase, args.feature_dir)))


if __name__ == "__main__":
    main()
