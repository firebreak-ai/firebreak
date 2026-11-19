"""A scripted council for tests: each step's answer comes from a small rule, and every call is
recorded as (step, member)."""

import json

MEMBERS = ("architect", "builder", "guardian", "security", "advocate", "analyst")


def record_of(prompt):
    """The council record a turn, stance or final session receives, or None for an opening."""
    marker = "\nCouncil record:\n"
    return json.loads(prompt.split(marker, 1)[1]) if marker in prompt else None


def member_of(prompt):
    return next((m for m in MEMBERS if f"Council member: {m}." in prompt), None)


def step_of(schema, prompt):
    props = schema["properties"]
    if "comment" in props:
        return "turn"
    if "stances" in props:
        return "second-round" if "tied_blockers" in (record_of(prompt) or {}) else "stance"
    if "consensus" in props:
        return "final"
    return "opening"


def answer(review, **extra):
    return {"review": review, "seconds": 1, "usage": {"test-model": {"inputTokens": 100}}, **extra}


class Council:
    """openings: member -> findings. turn(member, record) -> turn. stance(member, proposal, record)
    and second(...) -> "support" or "contest". context(step, member) -> declaration or None.
    fail(step, member) may raise."""

    def __init__(self, openings=None, turn=None, stance=None, second=None, context=None, fail=None):
        self.openings = openings or {}
        self.turn = turn or (lambda member, record: {"comment": "Nothing to add.", "responses": [], "proposals": []})
        self.stance = stance or (lambda member, proposal, record: "support")
        self.second = second or self.stance
        self.context = context or (lambda step, member: None)
        self.fail = fail or (lambda step, member: None)
        self.calls = []
        self.prompts = []

    def __call__(self, root, prompt, config, **kwargs):
        step, member = step_of(kwargs["schema"], prompt), member_of(prompt)
        self.calls.append((step, member))
        self.prompts.append((step, member, prompt))
        self.fail(step, member)
        record = record_of(prompt)
        if step == "opening":
            review = {"summary": f"{member} read the work.", "findings": list(self.openings.get(member, []))}
        elif step == "turn":
            review = self.turn(member, record)
        elif step in {"stance", "second-round"}:
            rule = self.stance if step == "stance" else self.second
            listed = record["proposals"] if step == "stance" else record["tied_blockers"]
            review = {"stances": [
                {"proposal": p["id"], "stance": (vote := rule(member, p["id"], record)),
                 "reason": "" if vote == "support" else f"{member} contests {p['id']}."}
                for p in listed]}
        else:
            review = {
                "summary": "The council agreed on its corrections.",
                "findings": [{"proposal": p["id"], "finding": {**p["finding"], "severity": p["severity"]},
                              "dissent": "; ".join(c["reason"] for c in p["contest"])}
                             for p in record["standing"]],
                "consensus": ["The members agreed on the standing corrections."],
                "dropped": [{"proposal": p["id"], "reason": f"Dropped: {p['why']}."} for p in record["dropped"]],
            }
        context = self.context(step, member)
        return answer(review, **({"context": context} if context else {}))

    def count(self, step):
        return sum(1 for s, _ in self.calls if s == step)
