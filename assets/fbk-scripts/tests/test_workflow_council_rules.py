"""The mediated council's rules: turns, the proposal list, closing stances, the count rule,
and the final session's contract."""

import pytest

from fbk.workflow import council
from fbk.workflow.store import WorkflowError


def finding(severity="suggestion", title="Cut the retry layer"):
    return {"title": title, "location": "design.md", "evidence": "Nothing asks for it.",
            "remedy": "Remove it.", "severity": severity}


def proposal(pid, severity="suggestion", replaces=()):
    return {"id": pid, "member": pid.split(":")[0], "finding": finding(severity),
            "replaces": list(replaces)}


def turn(responses=(), proposals=(), comment="I agree with most of this."):
    return {"comment": comment, "responses": list(responses), "proposals": list(proposals)}


def stances(members, votes):
    """votes maps a proposal id to each member's stance, in member order."""
    return {m: {pid: {"stance": s[i], "reason": "" if s[i] == "support" else f"{m} disagrees"}
                for pid, s in votes.items()}
            for i, m in enumerate(members)}


# Turns and the proposal list.

def test_a_turn_may_contest_concede_withdraw_its_own_and_replace():
    _, validate = council.turn_contract(["builder:1", "architect:1"], own=["builder:1"])
    validate(turn(
        [{"proposal": "builder:1", "action": "withdraw", "reason": "The architect is right."},
         {"proposal": "architect:1", "action": "contest", "reason": "It costs more than it fixes."}],
        [{**finding(), "replaces": ["architect:1"]}],
    ))


def test_a_turn_cannot_withdraw_another_members_proposal():
    _, validate = council.turn_contract(["architect:1"], own=[])
    with pytest.raises(WorkflowError, match="only its own"):
        validate(turn([{"proposal": "architect:1", "action": "withdraw", "reason": "No."}]))


def test_a_replacement_naming_an_unlisted_proposal_is_rejected():
    _, validate = council.turn_contract(["architect:1"], own=[])
    with pytest.raises(WorkflowError, match="replaces"):
        validate(turn(proposals=[{**finding(), "replaces": ["guardian:9"]}]))


def test_a_turn_adds_at_most_three_proposals():
    _, validate = council.turn_contract(["architect:1"], own=[])
    with pytest.raises(WorkflowError, match="at most 3"):
        validate(turn(proposals=[{**finding(), "replaces": ["architect:1"]}] * 4))


def test_a_turn_comment_over_its_limit_is_rejected():
    _, validate = council.turn_contract(["architect:1"], own=[])
    with pytest.raises(WorkflowError, match="comment"):
        validate(turn(comment="x" * (council.COMMENT_LIMIT + 1)))


def test_applying_a_turn_withdraws_adds_and_records_an_unanchored_proposal():
    listing = [proposal("builder:1"), proposal("architect:1")]
    after, record = council.apply_turn(listing, "builder", turn(
        [{"proposal": "builder:1", "action": "withdraw", "reason": "Conceded."}],
        [{**finding(), "replaces": ["architect:1"]}, {**finding(title="A fresh concern"), "replaces": []}],
    ))
    assert [p["id"] for p in after] == ["architect:1", "builder:r1"]
    assert after[1]["replaces"] == ["architect:1"] and after[1]["member"] == "builder"
    assert record["withdrawn"] == ["builder:1"]
    assert record["added"] == ["builder:r1"]
    assert [f["title"] for f in record["unanchored"]] == ["A fresh concern"]


# Closing stances.

def test_stances_must_cover_every_listed_proposal_once():
    _, validate = council.stance_contract(["a:1", "b:1"])
    with pytest.raises(WorkflowError, match="every listed proposal"):
        validate({"stances": [{"proposal": "a:1", "stance": "support", "reason": ""}]})


def test_a_contest_needs_its_reason():
    _, validate = council.stance_contract(["a:1"])
    with pytest.raises(WorkflowError, match="reason"):
        validate({"stances": [{"proposal": "a:1", "stance": "contest", "reason": " "}]})


# The count rule.

MEMBERS3 = ["architect", "builder", "guardian"]
MEMBERS2 = ["architect", "builder"]


def test_a_majority_supported_proposal_stands_with_dissent_and_a_contested_one_drops():
    listing = [proposal("architect:1"), proposal("guardian:1")]
    result = council.count(listing, MEMBERS3, stances(MEMBERS3, {
        "architect:1": ["support", "contest", "support"],
        "guardian:1": ["contest", "contest", "support"],
    }))
    [kept] = result["standing"]
    assert kept["id"] == "architect:1"
    assert kept["contest"] == [{"member": "builder", "reason": "builder disagrees"}]
    assert [(d["id"], d["why"]) for d in result["dropped"]] == [("guardian:1", "contested")]


def test_a_tied_suggestion_stands_with_both_sides():
    result = council.count([proposal("architect:1")], MEMBERS2,
                           stances(MEMBERS2, {"architect:1": ["support", "contest"]}))
    [kept] = result["standing"]
    assert kept["tied"] and kept["severity"] == "suggestion"
    assert kept["support"] == ["architect"] and kept["contest"][0]["member"] == "builder"


def test_a_tied_blocker_goes_to_a_second_round():
    listing = [proposal("architect:1", "blocker"), proposal("builder:1")]
    votes = stances(MEMBERS2, {"architect:1": ["support", "contest"], "builder:1": ["support", "support"]})
    assert council.count(listing, MEMBERS2, votes) == {"tied_blockers": ["architect:1"]}


@pytest.mark.parametrize("second, severity, stands", [
    (["support", "support"], "blocker", True),
    (["contest", "contest"], None, False),
    (["support", "contest"], "suggestion", True),
])
def test_the_second_round_settles_a_tied_blocker(second, severity, stands):
    listing = [proposal("architect:1", "blocker")]
    first = stances(MEMBERS2, {"architect:1": ["support", "contest"]})
    result = council.count(listing, MEMBERS2, first, stances(MEMBERS2, {"architect:1": second}))
    if stands:
        [kept] = result["standing"]
        assert kept["severity"] == severity
    else:
        assert result["standing"] == [] and result["dropped"][0]["why"] == "contested"


def test_a_standing_replacement_removes_what_it_names_and_a_dropped_one_does_not():
    listing = [proposal("architect:1"), proposal("guardian:1"),
               proposal("builder:r1", replaces=["architect:1"]),
               proposal("builder:r2", replaces=["guardian:1"])]
    result = council.count(listing, MEMBERS3, stances(MEMBERS3, {
        "architect:1": ["support"] * 3, "guardian:1": ["support"] * 3,
        "builder:r1": ["support"] * 3, "builder:r2": ["contest"] * 3,
    }))
    assert [p["id"] for p in result["standing"]] == ["guardian:1", "builder:r1"]
    assert {(d["id"], d["why"]) for d in result["dropped"]} == {
        ("architect:1", "replaced"), ("builder:r2", "contested")}


def test_in_a_chain_a_dropped_replacement_takes_only_its_own_claim():
    listing = [proposal("architect:1"), proposal("builder:r1", replaces=["architect:1"]),
               proposal("guardian:r1", replaces=["builder:r1"])]
    result = council.count(listing, MEMBERS3, stances(MEMBERS3, {
        "architect:1": ["support"] * 3, "builder:r1": ["support"] * 3, "guardian:r1": ["contest"] * 3,
    }))
    assert [p["id"] for p in result["standing"]] == ["builder:r1"]


def test_two_standing_replacements_of_one_proposal_stand_as_alternatives():
    listing = [proposal("architect:1"), proposal("builder:r1", replaces=["architect:1"]),
               proposal("guardian:r1", replaces=["architect:1"])]
    result = council.count(listing, MEMBERS3, stances(MEMBERS3, {pid: ["support"] * 3 for pid in
                                                                 ("architect:1", "builder:r1", "guardian:r1")}))
    standing = {p["id"]: p for p in result["standing"]}
    assert set(standing) == {"builder:r1", "guardian:r1"}
    assert standing["builder:r1"]["alternatives"] == ["guardian:r1"]
    assert standing["guardian:r1"]["alternatives"] == ["builder:r1"]


def test_a_members_stance_on_its_own_proposal_counts_like_any_other():
    result = council.count([proposal("architect:1")], MEMBERS3, stances(MEMBERS3, {
        "architect:1": ["contest", "contest", "support"]}))
    assert result["standing"] == []


# The final session.

def final(findings, dropped=(), consensus=("The design keeps one store.",)):
    return {"summary": "Two corrections stand.", "findings": findings,
            "consensus": list(consensus), "dropped": list(dropped)}


def test_the_final_session_writes_exactly_the_standing_list():
    _, validate = council.final_contract({"architect:1": "blocker"}, ["guardian:1"])
    validate(final([{"proposal": "architect:1", "finding": finding("blocker"), "dissent": ""}],
                   [{"proposal": "guardian:1", "reason": "Two members found nothing asks for it."}]))
    with pytest.raises(WorkflowError, match="exactly one finding for each standing proposal"):
        validate(final([], [{"proposal": "guardian:1", "reason": "Dropped."}]))


def test_the_final_session_cannot_change_a_severity():
    _, validate = council.final_contract({"architect:1": "suggestion"}, [])
    with pytest.raises(WorkflowError, match="keep the severity"):
        validate(final([{"proposal": "architect:1", "finding": finding("blocker"), "dissent": ""}]))


def test_the_final_session_gives_a_reason_for_each_dropped_proposal():
    _, validate = council.final_contract({}, ["guardian:1"])
    with pytest.raises(WorkflowError, match="each dropped proposal"):
        validate(final([], []))


def test_the_council_finding_limit_fits_every_proposal_that_can_stand():
    assert council.COUNCIL_FINDING_LIMIT == 33


def test_a_review_result_holds_every_finding_a_council_can_return():
    from fbk.workflow import review

    assert review.RESULT_FINDING_LIMIT == council.COUNCIL_FINDING_LIMIT
