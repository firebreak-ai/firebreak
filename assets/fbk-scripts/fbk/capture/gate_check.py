"""Per-project capture gate: instrumentation detection and capture-level resolution.

All three security hardenings live here because they are one decision — "is capture
allowed in this project, and at what level?" — and share the same realpath-confinement
and bounded-read machinery.  Splitting them would scatter a single security boundary
across modules.

Out-of-tree corroboration for the ``full`` level
-------------------------------------------------
An in-tree ``capture.cfg`` requesting ``full`` is honored only when an out-of-tree
signal corroborates it.  Two signals are accepted (either suffices):

1. Env var ``FBK_CAPTURE_LEVEL=full`` (case-insensitive).

2. A marker file in the operator's global Claude dir keyed to the project path.
   Shape:
     directory : ``<CLAUDE_CONFIG_DIR>/fbk-capture-level/``
     filename  : any (the implementation scans all files in that directory)
     line 1    : the ``os.path.realpath`` of the project root
     line 2    : ``capture_level=full``

   Example:  ``~/.claude/fbk-capture-level/project.cfg``
   with content::

       /home/user/my-project
       capture_level=full

   The gate reads that directory, checks each file for a matching realpath on line 1
   and ``capture_level=full`` on line 2, and returns True on the first match.

Imports
-------
Only ``os``, ``os.path``, and bounded file I/O are used.  This module must not
import the state engine, YAML, or any Firebreak internals.
"""

import os
import sys

# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------

FBK_MARKER_SENTINEL = ".fbk-managed"

_AUTOMATION_DIR = ".claude/automation"
_CAPTURE_DIR_NAME = ".fbk-capture"
_CAPTURE_CFG_NAME = "capture.cfg"

_VALID_LEVELS = {"off", "standard", "full"}


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _real_capture_dir(cwd):
    """Return the realpath-confined capture dir path, or None if absent/unsafe.

    A ``.fbk-capture/`` that is a symlink, or whose realpath escapes the
    project root, is refused and None is returned.
    """
    candidate = os.path.join(cwd, _CAPTURE_DIR_NAME)
    if not os.path.exists(candidate):
        return None

    # Refuse symlinks that point outside the tree.
    if os.path.islink(candidate):
        return None

    real_candidate = os.path.realpath(candidate)
    real_cwd = os.path.realpath(cwd)

    # The resolved dir must be under (or equal to) the resolved project root.
    if not real_candidate.startswith(real_cwd + os.sep) and real_candidate != real_cwd:
        return None

    if not os.path.isdir(real_candidate):
        return None

    return real_candidate


def _read_cfg_level(real_capture_dir):
    """Read the first line of capture.cfg and return the level value, or None.

    Refuses a symlinked ``capture.cfg``.  Only the first 256 bytes of the first
    line are read; a giant newline-less file cannot stall the hot path.  A window
    with no parseable ``capture_level=`` token yields None, falling back to the
    caller's safe default.
    """
    cfg_path = os.path.join(real_capture_dir, _CAPTURE_CFG_NAME)

    # Refuse symlinks.
    if os.path.islink(cfg_path):
        return None

    if not os.path.isfile(cfg_path):
        return None

    try:
        with open(cfg_path, "r") as f:
            line = f.readline(256).strip()
    except OSError:
        return None

    if "=" not in line:
        return None

    key, _, value = line.partition("=")
    if key.strip() != "capture_level":
        return None

    return value.strip()


def _full_corroborated(cwd):
    """Return True when an out-of-tree signal corroborates an in-tree full request.

    Accepts either:
    - env ``FBK_CAPTURE_LEVEL=full`` (case-insensitive), or
    - a marker file in ``<CLAUDE_CONFIG_DIR>/fbk-capture-level/`` whose first
      line is ``os.path.realpath(cwd)`` and whose second line is
      ``capture_level=full``.
    """
    # Primary: environment variable.
    env_level = os.environ.get("FBK_CAPTURE_LEVEL", "")
    if env_level.strip().lower() == "full":
        return True

    # Secondary: operator global-dir marker.
    claude_config_dir = os.environ.get(
        "CLAUDE_CONFIG_DIR", os.path.expanduser("~/.claude")
    )
    marker_dir = os.path.join(claude_config_dir, "fbk-capture-level")

    if not os.path.isdir(marker_dir):
        return False

    resolved_cwd = os.path.realpath(cwd)

    try:
        entries = os.listdir(marker_dir)
    except OSError:
        return False

    for entry in entries:
        entry_path = os.path.join(marker_dir, entry)
        if not os.path.isfile(entry_path):
            continue
        try:
            with open(entry_path, "r") as f:
                # Byte-capped at 4096 (covers PATH_MAX for realpath line); an
                # over-capacity line fails the match and corroboration is refused.
                line1 = f.readline(4096).strip()
                line2 = f.readline(4096).strip()
        except OSError:
            continue

        if line1 == resolved_cwd and line2 == "capture_level=full":
            return True

    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def project_is_instrumented(cwd):
    """Return True when the project at cwd is Firebreak-instrumented.

    A project is instrumented when either:
    (a) the Firebreak sentinel ``.claude/automation/.fbk-managed`` exists, or
    (b) a realpath-confined ``.fbk-capture/capture.cfg`` exists.

    A bare ``.claude/automation/`` directory without the sentinel does NOT
    instrument the project — a hostile repo could ship that shared namespace.

    If ``.fbk-capture/`` exists but is a symlink (or ``capture.cfg`` inside it
    is a symlink), the entire project is treated as uninstrumented — a symlinked
    capture subsystem is a security red flag that overrides the sentinel.

    Returns False on any filesystem error; never raises.
    """
    try:
        capture_candidate = os.path.join(cwd, _CAPTURE_DIR_NAME)
        capture_dir_exists = os.path.exists(capture_candidate)

        # If .fbk-capture/ is present as a symlink, refuse the whole project.
        if capture_dir_exists and os.path.islink(capture_candidate):
            return False

        # (a) Firebreak sentinel.
        sentinel = os.path.join(cwd, _AUTOMATION_DIR, FBK_MARKER_SENTINEL)
        if os.path.isfile(sentinel):
            # If a capture dir is present, also verify capture.cfg is not symlinked.
            if capture_dir_exists:
                real_capture = _real_capture_dir(cwd)
                if real_capture is not None:
                    cfg_path = os.path.join(real_capture, _CAPTURE_CFG_NAME)
                    if os.path.islink(cfg_path):
                        return False
            return True

        # (b) Realpath-confined capture.cfg.
        real_capture = _real_capture_dir(cwd)
        if real_capture is not None:
            cfg_path = os.path.join(real_capture, _CAPTURE_CFG_NAME)
            # Refuse a symlinked capture.cfg.
            if os.path.islink(cfg_path):
                return False
            if os.path.isfile(cfg_path):
                return True

        return False
    except Exception:
        return False


def resolve_capture_level(cwd):
    """Return the effective capture level for the project at cwd.

    Returns one of ``"off"``, ``"standard"``, or ``"full"``.  Returns ``"off"``
    on any error; never raises.

    Resolution rules:
    - Uninstrumented project → ``"off"``.
    - cfg value ``"off"`` → ``"off"``.
    - cfg value ``"standard"`` → ``"standard"``.
    - cfg value ``"full"`` → ``"full"`` only when out-of-tree corroboration
      exists; otherwise clamped to ``"standard"``.
    - Firebreak-marked project with no cfg → ``"standard"``.
    - Unrecognised cfg value → ``"standard"`` with a stderr warning.
    """
    try:
        if not project_is_instrumented(cwd):
            return "off"

        real_capture = _real_capture_dir(cwd)
        cfg_value = None
        if real_capture is not None:
            cfg_value = _read_cfg_level(real_capture)

        if cfg_value is None:
            # Firebreak-marked, no readable cfg → default standard.
            return "standard"

        if cfg_value == "off":
            return "off"

        if cfg_value == "standard":
            return "standard"

        if cfg_value == "full":
            if _full_corroborated(cwd):
                return "full"
            return "standard"

        # Unrecognised value.
        print(
            f"fbk.capture.gate_check: invalid capture_level value {cfg_value!r}; "
            "defaulting to standard",
            file=sys.stderr,
        )
        return "standard"

    except Exception:
        return "off"
