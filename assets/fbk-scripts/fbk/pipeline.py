import json
import re
import sys
import argparse
import pathlib

VALID_COMBINATIONS = {
    "behavioral": {"critical", "major"},
    "structural": {"minor", "info"},
    "test-integrity": {"critical", "major", "minor"},
    "fragile": {"major", "minor"},
}

VALID_TYPES = set(VALID_COMBINATIONS.keys())
VALID_SEVERITIES = {"critical", "major", "minor", "info"}
SEVERITY_ORDER = {"info": 0, "minor": 1, "major": 2, "critical": 3}

REQUIRED_FIELDS = ["id", "title", "location", "type", "severity", "mechanism", "consequence", "evidence"]
MIN_LENGTH_FIELDS = {"title": 10, "mechanism": 10, "consequence": 10}

DEFAULTS = {
    "origin": "unknown",
    "detection_source": "intent",
    "source_of_truth_ref": "",
    "pattern": "",
    "remediation": "",
}


class LensVocabulary:
    """Parsed vocabulary for a review lens: types, severities, matrix, and required fields."""

    def __init__(self, types, severities, matrix, required):
        self.types = types
        self.severities = severities
        self.matrix = matrix
        self.required = required


def load_lens_matrix(lens_path):
    """Parse the fenced lens-matrix block from a lens file and return a LensVocabulary.

    Raises FileNotFoundError (message contains lens_path) when the file does not exist.
    Never falls back silently to a default vocabulary.
    """
    path = pathlib.Path(lens_path)
    if not path.exists():
        raise FileNotFoundError(f"lens not found: {lens_path}")

    content = path.read_text()

    # Extract lines between ```lens-matrix and closing ```
    match = re.search(r"```lens-matrix\n(.*?)```", content, re.DOTALL)
    if not match:
        raise ValueError(f"no lens-matrix block found in: {lens_path}")
    block = match.group(1)

    def _parse_bracketed_list(line_text):
        """Parse 'key: [a, b, c]' value portion into a set of stripped strings."""
        inner = re.search(r"\[([^\]]+)\]", line_text)
        if not inner:
            return set()
        return {item.strip() for item in inner.group(1).split(",")}

    types = set()
    severities = set()
    matrix = {}
    required = set()

    lines = block.splitlines()
    in_matrix = False
    for line in lines:
        if re.match(r"^types:", line):
            types = _parse_bracketed_list(line)
            in_matrix = False
        elif re.match(r"^severities:", line):
            severities = _parse_bracketed_list(line)
            in_matrix = False
        elif re.match(r"^matrix:", line):
            in_matrix = True
        elif re.match(r"^required:", line):
            required = _parse_bracketed_list(line)
            in_matrix = False
        elif in_matrix and re.match(r"^\s+\w", line):
            # Indented matrix entry: "  type_name: [sev1, sev2]"
            key_match = re.match(r"^\s+(\w[\w-]*):", line)
            if key_match:
                type_name = key_match.group(1)
                matrix[type_name] = _parse_bracketed_list(line)

    return LensVocabulary(types=types, severities=severities, matrix=matrix, required=required)


def load_presets():
    preset_path = pathlib.Path(__file__).parent / "data" / "fbk-presets.json"
    with open(preset_path) as f:
        return json.load(f)


def read_stdin_json():
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"ERROR: malformed JSON input: {e}", file=sys.stderr)
        sys.exit(1)


def write_json(data):
    json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write('\n')


def validate_sighting(finding, vocab=None):
    """Validate a finding dict against the given vocabulary.

    When vocab is None, falls back to module constants (REQUIRED_FIELDS, VALID_TYPES,
    VALID_SEVERITIES, VALID_COMBINATIONS) — identical behavior to the previous
    single-argument form.  When vocab is a LensVocabulary, validates against that
    lens's types/severities/matrix/required.

    Returns None on success, or an error string describing the first rejection reason.
    """
    if vocab is None:
        required_fields = REQUIRED_FIELDS
        valid_types = VALID_TYPES
        valid_severities = VALID_SEVERITIES
        combinations = VALID_COMBINATIONS
    else:
        required_fields = vocab.required
        valid_types = vocab.types
        valid_severities = vocab.severities
        combinations = vocab.matrix

    s = finding

    # Check required fields
    for field in required_fields:
        if field == "location":
            loc = s.get("location")
            if not isinstance(loc, dict) or not loc.get("file") or "start_line" not in loc:
                return f"missing or invalid 'location' (need 'file' and 'start_line')"
            continue
        val = s.get(field)
        if val is None or (isinstance(val, str) and val.strip() == ""):
            return f"missing field '{field}'"

    # Check min lengths (always against module constants — these are structural quality gates
    # that do not vary per lens)
    for field, min_len in MIN_LENGTH_FIELDS.items():
        val = s.get(field, "")
        if len(str(val)) < min_len:
            return f"field '{field}' below minimum length {min_len}"

    # Check enums
    t = s.get("type")
    sev = s.get("severity")
    if t not in valid_types:
        return f"invalid type '{t}'"
    if sev not in valid_severities:
        return f"invalid severity '{sev}'"

    # Check type-severity matrix
    if sev not in combinations.get(t, set()):
        return f"invalid type-severity combination '{t}+{sev}'"

    return None


def validate_against_mode(record, vocab, output_mode):
    """Route record validation based on the lens output mode.

    When output_mode is "scan", returns None (accept; skip finding-validation).
    When output_mode is "finding", delegates to validate_sighting(record, vocab).
    """
    if output_mode == "scan":
        return None
    return validate_sighting(record, vocab)


def normalize(finding):
    """Strip researcher framing from a finding and return the six allowlisted handoff fields.

    Folds the structured location object into the evidence string.
    Returns a dict with exactly the keys: mechanism, consequence, evidence, type,
    severity, source_of_truth_ref.
    """
    loc = finding.get("location", {})
    base_evidence = finding.get("evidence", "")
    if isinstance(loc, dict) and loc.get("file") is not None:
        loc_str = f"{loc.get('file', '')}:{loc.get('start_line', '')}"
        evidence = f"{base_evidence} ({loc_str})"
    else:
        evidence = base_evidence

    return {
        "mechanism": finding.get("mechanism", ""),
        "consequence": finding.get("consequence", ""),
        "evidence": evidence,
        "type": finding.get("type", ""),
        "severity": finding.get("severity", ""),
        "source_of_truth_ref": finding.get("source_of_truth_ref", ""),
    }


def cmd_validate(args):
    vocab = None
    if args.lens is not None:
        try:
            vocab = load_lens_matrix(args.lens)
        except (FileNotFoundError, ValueError) as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)

    sightings = read_stdin_json()
    valid = []
    rejected = 0
    total = len(sightings)

    for s in sightings:
        reason = validate_sighting(s, vocab)
        if reason:
            rejected += 1
            print(f"REJECTED: {reason}: {json.dumps(s, ensure_ascii=False)}", file=sys.stderr)
            continue
        # Fill defaults
        for key, default in DEFAULTS.items():
            if key not in s or s[key] is None:
                s[key] = default
        valid.append(s)

    # Assign sequential IDs
    for i, s in enumerate(valid, 1):
        s["id"] = f"S-{i:02d}"

    if total > 0 and rejected / total > 0.30:
        pct = rejected / total * 100
        print(f"WARNING: {rejected}/{total} sightings rejected ({pct:.0f}%) — check prompt compliance", file=sys.stderr)

    write_json(valid)


def cmd_domain_filter(args):
    presets = load_presets()
    preset_name = args.preset
    if preset_name not in presets:
        print(f"ERROR: unknown preset '{preset_name}'. Available: {', '.join(sorted(presets.keys()))}", file=sys.stderr)
        sys.exit(1)

    allowed = set(presets[preset_name]["allowed_types"])
    sightings = read_stdin_json()
    filtered = []

    for s in sightings:
        if s.get("type") in allowed:
            filtered.append(s)
        else:
            print(f"DROPPED (domain): type={s.get('type')} id={s.get('id')} title={s.get('title', '')}", file=sys.stderr)

    write_json(filtered)


def cmd_severity_filter(args):
    min_sev = args.min_severity
    if min_sev not in VALID_SEVERITIES:
        print(f"ERROR: invalid severity '{min_sev}'. Valid: {', '.join(sorted(VALID_SEVERITIES, key=lambda x: SEVERITY_ORDER[x]))}", file=sys.stderr)
        sys.exit(1)

    threshold = SEVERITY_ORDER[min_sev]
    sightings = read_stdin_json()
    filtered = []

    for s in sightings:
        sev = s.get("severity", "info")
        if SEVERITY_ORDER.get(sev, 0) >= threshold:
            filtered.append(s)
        else:
            print(f"DROPPED (severity): severity={sev} id={s.get('id')} title={s.get('title', '')}", file=sys.stderr)

    write_json(filtered)


def _render_markdown(items):
    output = []
    for item in items:
        status = item.get("status")
        if status in ("rejected", "rejected-as-nit"):
            continue

        display_id = item.get("finding_id", item.get("id", "?"))
        title = item.get("title", "")

        loc = item.get("location", {})
        loc_file = loc.get("file", "")
        start = loc.get("start_line", "")
        end = loc.get("end_line")
        loc_str = f"{loc_file}:{start}" + (f"-{end}" if end else "")

        sev = item.get("severity", "")
        typ = item.get("type", "")
        origin = item.get("origin", "")
        det_source = item.get("detection_source", "")
        pattern = item.get("pattern", "")

        lines = []
        lines.append(f"### {display_id}: {title}")
        lines.append("")
        lines.append(f"- **Location**: `{loc_str}`")
        lines.append(f"- **Type**: {typ} | **Severity**: {sev} | **Origin**: {origin}")
        if det_source or pattern:
            parts = []
            if det_source:
                parts.append(f"**Detection source**: {det_source}")
            if pattern:
                parts.append(f"**Pattern**: `{pattern}`")
            lines.append(f"- {' | '.join(parts)}")
        lines.append("")
        lines.append(f"**Mechanism**: {item.get('mechanism', '')}")
        lines.append("")
        lines.append(f"**Consequence**: {item.get('consequence', '')}")
        lines.append("")
        lines.append(f"**Evidence**: {item.get('evidence', '')}")

        ve = item.get("verification_evidence")
        if ve:
            lines.append("")
            lines.append(f"**Verification**: {ve}")

        rc = item.get("reclassified_from", {})
        if rc and isinstance(rc, dict) and rc.get("type"):
            lines.append("")
            lines.append(f"*Reclassified from {rc['type']}/{rc.get('severity', '')}*")

        rem = item.get("remediation", "")
        if rem:
            lines.append("")
            lines.append(f"**Remediation**: {rem}")

        output.append("\n".join(lines))

    sys.stdout.write("\n\n".join(output))
    if output:
        sys.stdout.write("\n")


def cmd_to_markdown(args):
    items = read_stdin_json()
    _render_markdown(items)


def cmd_run(args):
    vocab = None
    if args.lens is not None:
        try:
            vocab = load_lens_matrix(args.lens)
        except (FileNotFoundError, ValueError) as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)

    # Step 1: Validate
    sightings = read_stdin_json()
    valid = []
    rejected = 0
    total = len(sightings)

    for s in sightings:
        reason = validate_sighting(s, vocab)
        if reason:
            rejected += 1
            print(f"REJECTED: {reason}: {json.dumps(s, ensure_ascii=False)}", file=sys.stderr)
            continue
        for key, default in DEFAULTS.items():
            if key not in s or s[key] is None:
                s[key] = default
        valid.append(s)

    for i, s in enumerate(valid, 1):
        s["id"] = f"S-{i:02d}"

    if total > 0 and rejected / total > 0.30:
        pct = rejected / total * 100
        print(f"WARNING: {rejected}/{total} sightings rejected ({pct:.0f}%) — check prompt compliance", file=sys.stderr)

    # Step 2: Domain filter
    presets = load_presets()
    preset_name = args.preset
    if preset_name not in presets:
        print(f"ERROR: unknown preset '{preset_name}'. Available: {', '.join(sorted(presets.keys()))}", file=sys.stderr)
        sys.exit(1)

    allowed = set(presets[preset_name]["allowed_types"])
    domain_filtered = []
    for s in valid:
        if s.get("type") in allowed:
            domain_filtered.append(s)
        else:
            print(f"DROPPED (domain): type={s.get('type')} id={s.get('id')} title={s.get('title', '')}", file=sys.stderr)

    # Step 3: Severity filter
    min_sev = args.min_severity
    if min_sev not in VALID_SEVERITIES:
        print(f"ERROR: invalid severity '{min_sev}'. Valid: {', '.join(sorted(VALID_SEVERITIES, key=lambda x: SEVERITY_ORDER[x]))}", file=sys.stderr)
        sys.exit(1)
    threshold = SEVERITY_ORDER[min_sev]
    severity_filtered = []
    for s in domain_filtered:
        sev = s.get("severity", "info")
        if SEVERITY_ORDER.get(sev, 0) >= threshold:
            severity_filtered.append(s)
        else:
            print(f"DROPPED (severity): severity={sev} id={s.get('id')} title={s.get('title', '')}", file=sys.stderr)

    # Reassign IDs after filtering
    for i, s in enumerate(severity_filtered, 1):
        s["id"] = f"S-{i:02d}"

    # Step 4: Output
    if args.output_markdown:
        _render_markdown(severity_filtered)
    else:
        write_json(severity_filtered)


def cmd_normalize(args):
    findings = read_stdin_json()
    write_json([normalize(f) for f in findings])


def main():
    parser = argparse.ArgumentParser(description="Code review sighting pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_validate = subparsers.add_parser("validate")
    p_validate.add_argument("--lens", default=None)

    p_domain = subparsers.add_parser("domain-filter")
    p_domain.add_argument("--preset", required=True)

    p_severity = subparsers.add_parser("severity-filter")
    p_severity.add_argument("--min-severity", required=True)

    subparsers.add_parser("to-markdown")

    p_run = subparsers.add_parser("run")
    p_run.add_argument("--preset", required=True)
    p_run.add_argument("--min-severity", required=True)
    p_run.add_argument("--output-markdown", action="store_true")
    p_run.add_argument("--lens", default=None)

    subparsers.add_parser("normalize")

    args = parser.parse_args()

    commands = {
        "validate": cmd_validate,
        "domain-filter": cmd_domain_filter,
        "severity-filter": cmd_severity_filter,
        "to-markdown": cmd_to_markdown,
        "run": cmd_run,
        "normalize": cmd_normalize,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
