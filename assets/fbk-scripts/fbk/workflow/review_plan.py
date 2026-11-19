"""Persist review choices independently of phase routing and artifact authorship."""

import uuid

from .store import WorkflowError, event, project_config, save

PHASES = ("intent", "design", "spec", "breakdown")
# Design and spec record a plan before close; for intent and breakdown no plan means a single
# reviewer, so the council option adds no question to a unit.
REQUIRED = ("design", "spec")
MEMBERS = ("architect", "builder", "guardian", "security", "advocate", "analyst")


def validate(mode, members=()):
    if not isinstance(mode, str) or mode not in {"single", "council"}:
        raise WorkflowError("Review mode must be single or council.")
    if not isinstance(members, (list, tuple)) or any(
        not isinstance(m, str) or m not in MEMBERS for m in members
    ):
        raise WorkflowError("Council members must name supported review perspectives.")
    if mode == "single" and members:
        raise WorkflowError("Single review does not take council members.")
    if mode == "council" and (
        not 2 <= len(members) <= 3 or len(set(members)) != len(members)
    ):
        raise WorkflowError("Choose two or three distinct council perspectives.")
    if mode == "council" and "builder" not in members:
        # The builder prices each proposal's cost; without it the council only adds.
        raise WorkflowError("Every council includes the builder; choose one or two more perspectives.")
    return {"mode": mode, "members": sorted(members)}


def choice(mode, members, reason, source):
    if not isinstance(reason, str) or not reason.strip():
        raise WorkflowError(
            "Record the reason and applicable user preference for this review choice."
        )
    return {
        **validate(mode, members),
        "id": str(uuid.uuid4()),
        "reason": reason,
        "source": source,
    }


def defaults(root):
    data = project_config(root).get("review_defaults", {})
    if not isinstance(data, dict) or set(data) - set(PHASES):
        raise WorkflowError("review_defaults may name only intent, design, spec, and breakdown.")
    for phase, setting in data.items():
        if not isinstance(setting, dict) or set(setting) != {
            "mode",
            "members",
            "reason",
        }:
            raise WorkflowError(
                f"Review default for {phase} needs mode, members, and reason."
            )
        validate(setting["mode"], setting["members"])
        if not isinstance(setting["reason"], str) or not setting["reason"].strip():
            raise WorkflowError(
                "Review defaults need the applicable user preference as a reason."
            )
    return data


def initialize(root, phases):
    configured = defaults(root)
    return {
        phase: choice(**configured[phase], source="project")
        if phase in configured
        else None
        for phase in PHASES
        if phase in phases
    }


def inherit(root, record, phase, session):
    if phase not in PHASES or record.get("review_plans", {}).get(phase):
        return
    # Existing accepted units keep their historical evidence until explicitly reopened.
    if record["phases"][phase]["evidence"]:
        return
    configured = defaults(root)
    if phase in configured:
        selected = choice(**configured[phase], source="project")
        record.setdefault("review_plans", {})[phase] = selected
        event(record, "review-selected", session, phase=phase, selection=selected)


def select(root, record, phase, mode, members, reason, session):
    from . import engine, evidence

    engine.ownership(record, session)
    if phase not in PHASES or phase not in evidence.phases(record):
        raise WorkflowError("Select review for an applicable intent, design, spec, or breakdown phase.")
    if any(w["pending"] for w in record["phases"].values()):
        raise WorkflowError(
            "Finish or recover the running close before changing review mode."
        )
    if record["phases"][phase]["evidence"]:
        raise WorkflowError(
            "Reopen the accepted phase before changing its review plan."
        )
    selected = choice(mode, members, reason, "unit")
    current = record.get("review_plans", {}).get(phase)
    if current and all(current[k] == selected[k] for k in ("mode", "members")):
        return current  # Confirming a choice does not force another review or another question.
    record.setdefault("review_plans", {})[phase] = selected
    event(record, "review-selected", session, phase=phase, selection=selected)
    save(root, record)
    return selected


def require(record, phase):
    if phase not in PHASES:
        return None
    selected = record.get("review_plans", {}).get(phase)
    if not selected and phase not in REQUIRED:
        return None
    if not selected:
        raise WorkflowError(
            f"Choose single or council review for {phase} with review-plan before closing. "
            "Use the existing user/project preference; ask the human only when it does not cover this choice."
        )
    validate(selected["mode"], selected["members"])
    return selected


def context(record):
    plans = record.get("review_plans", {})
    descriptions = []
    for phase in PHASES:
        if phase == "design" and not record["design"]:
            continue
        plan = plans.get(phase)
        if plan:
            descriptions.append(
                f"{phase}: {plan['mode']}"
                + (f" ({', '.join(plan['members'])})" if plan["members"] else "")
            )
        elif phase in REQUIRED and not record["phases"][phase]["evidence"]:
            descriptions.append(
                f"{phase}: review choice pending; use review-plan before closing"
            )
    return "; ".join(descriptions)
