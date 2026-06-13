"""fbk package for validation gates and utilities."""

COMMAND_MAP = {
    "spec-gate": "fbk.gates.spec",
    "review-gate": "fbk.gates.review",
    "breakdown-gate": "fbk.gates.breakdown",
    "task-reviewer-gate": "fbk.gates.task_reviewer",
    "test-hash-gate": "fbk.gates.test_hash",
    "intent-gate": "fbk.gates.intent",
    "design-gate": "fbk.gates.design",
    "code-review-gate": "fbk.gates.code_review",
    "task-completed": "fbk.hooks.task_completed",
    "dispatch-status": "fbk.hooks.dispatch_status",
    "pipeline": "fbk.pipeline",
    "audit": "fbk.audit",
    "config": "fbk.config",
    "state": "fbk.state",
    "session-logger": "fbk.council.session_logger",
    "session-manager": "fbk.council.session_manager",
    "session-state": "fbk.council.session_state",
    "ralph": "fbk.council.ralph",
    "report": "fbk.report",
}
