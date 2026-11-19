"""Firebreak workflow and standalone review commands."""

from fbk.workflow import COMMANDS

COMMAND_MAP = {name: "fbk.workflow.cli" for name in COMMANDS}
COMMAND_MAP.update({"pipeline": "fbk.pipeline", "cross-review": "fbk.cross_review"})
COMMAND_MAP["review-round"] = "fbk.workflow.review_rounds"
COMMAND_MAP["investigation"] = "fbk.workflow.investigations"

COMMAND_MAP["remediation"] = "fbk.workflow.remediation_verification"
