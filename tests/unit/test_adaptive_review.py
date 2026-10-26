from types import SimpleNamespace as Obj

import pytest

from services.api.app.application.adaptive_review import AdaptiveReviewProposal, validate_additions


def sample():
    plan = Obj(units=[Obj(unit_id="root", input_file_refs=["a"], objective="initial extraction")])
    finding = Obj(finding_id="finding", plan_unit_id="root", evidence_anchors=["anchor"], review=None)
    proposal = AdaptiveReviewProposal(summary="A source condition needs a further check", additions=[dict(
        title="Check the condition", objective="Compare the condition to the requested scope",
        reason="The adopted finding contains a specific scope condition", trigger_finding_ids=["finding"],
        parent_unit_ids=["root"], input_file_refs=["a"])])
    return plan, finding, proposal


@pytest.mark.parametrize("fault", ["human", "anchor", "parent", "repeat", "duplicate", "budget", "source", "scope"])
def test_addition_gates(fault):
    plan, finding, proposal = sample()
    parents, used, calls = {"root"}, set(), 2
    if fault == "human": finding.review = Obj(requires_human_decision=True)
    if fault == "anchor": finding.evidence_anchors = []
    if fault == "parent": parents = set()
    if fault == "repeat": used = {"finding"}
    if fault == "duplicate": proposal.additions[0].objective = plan.units[0].objective
    if fault == "budget": calls = 0
    if fault == "source": proposal.additions[0].input_file_refs = ["outside"]
    if fault == "scope": finding.plan_unit_id = "another-unit"
    with pytest.raises(ValueError):
        validate_additions(proposal, plan, [finding], parents, used, calls)


def test_zero_additions_is_valid_and_does_not_require_more_budget():
    plan, finding, _ = sample()
    validate_additions(AdaptiveReviewProposal(summary="No further work is needed"), plan, [finding], {"root"}, set(), 0)
