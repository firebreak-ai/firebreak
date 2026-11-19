"""Read-only comparison with managed implementation acceptance.

Test discovery is deliberately heuristic, not a claim about test runner collection.
"""

import fnmatch
import os
from pathlib import Path

from . import evidence
from .store import WorkflowError

_IGNORED = {'.git', '.fbk', '.claude', '.venv', 'venv', 'node_modules', '__pycache__', '.pytest_cache'}
_TEST_NAMES = ('test_*.py', '*_test.py', '*_test.go', '*.test.*', '*.spec.*', '*Test.java', '*Tests.cs')


def _inventory(root, declared):
    roots = {'tests', 'test', '__tests__'}
    for pattern in declared['tests']:
        parts = Path(pattern).parts
        prefix = []
        for part in parts:
            if any(c in part for c in '*?['):
                break
            prefix.append(part)
        path = Path(*prefix) if prefix else Path('.')
        if prefix and not (root / path).is_dir():
            path = path.parent
        roots.add(path.as_posix())
    result = set()
    for relative in sorted(roots):
        directory = root / relative
        if directory.is_symlink() or not directory.is_dir():
            continue
        try:
            directory.resolve().relative_to(root.resolve())
        except ValueError:
            continue
        for current, directories, files in os.walk(directory, followlinks=False):
            directories[:] = [d for d in directories if d not in _IGNORED and not (Path(current) / d).is_symlink()]
            for name in files:
                path = Path(current) / name
                if not path.is_symlink() and any(fnmatch.fnmatchcase(name, pattern) for pattern in _TEST_NAMES):
                    result.add(path.relative_to(root).as_posix())
    return sorted(result)


def baseline(root, record):
    declared = evidence.scope(root, record['unit'])
    return {'scope': declared, 'test_inventory': _inventory(root, declared)}


def report(root, record):
    accepted = record['phases'].get('implement', {}).get('evidence')
    if not accepted:
        return None
    stored = accepted.get('drift_baseline')
    errors = []
    try:
        declared = stored['scope'] if stored else evidence.scope(root, record['unit'])
    except WorkflowError as exc:
        declared = {'sources': [], 'tests': [], 'docs': []}
        errors.append(str(exc))
    original = accepted.get('files', {})
    current = {}
    # Compare every originally accepted path even when current scope is broken.
    changes = []
    for path, old_hash in original.items():
        try:
            current[path] = evidence.file_hashes(root, [path])[path]
        except WorkflowError:
            kind = 'deleted' if not (root / path).exists() else 'unavailable'
            changes.append({'path': path, 'kind': kind})
            continue
        if current[path] != old_hash:
            changes.append({'path': path, 'kind': 'modified'})
    try:
        selected = evidence.expand(root, declared['sources'] + declared['tests'] + declared.get('docs', []))
        changes.extend({'path': path, 'kind': 'added'} for path in selected if path not in original)
    except WorkflowError as exc:
        errors.append(str(exc))
    candidates = _inventory(root, declared)
    previous = set(stored['test_inventory']) if stored else set()
    outside = [p for p in candidates if p not in previous and not evidence.matches(p, declared['tests'])]
    return {
        'accepted_at': accepted.get('at'),
        'accepted_revision': accepted.get('revision'),
        'changes': sorted(changes, key=lambda row: row['path']),
        'outside_scope_test_candidates': outside,
        'inventory_baseline_known': stored is not None,
        'discovery': 'Conventional test filenames under declared test parents and tests/test/__tests__ directories; excludes symlinks and caches. This is not test-runner collection. Without an inventory baseline, candidate introduction time is unknown.',
        'errors': errors,
        'next': 'Review changes against accepted intent and scope. Reopen the earliest affected phase with a recorded reason; obtain required approvals and re-close affected phases. Out-of-scope candidates require scope review before they can become managed evidence. This report does not change acceptance or test locks.',
    }
