from types import SimpleNamespace

import pytest

from services.api.app.application.collaboration_review import DependencyAssessmentDraft, validate_dependency_assessments


@pytest.mark.parametrize("fault", ["missing", "duplicate", "foreign", "negative_index", "large_index", "unresolved", "wrong_source"])
def test_assessment_binding_fails_closed(fault):
    context = SimpleNamespace(contribution_id="parent", source_file_refs=("approved",))
    candidate = SimpleNamespace(finding_id="finding")
    resolved = SimpleNamespace(finding_id="finding", evidence_anchors=[])
    draft = DependencyAssessmentDraft(contribution_id="parent", verdict="supported", explanation="A claim", finding_indices=[0])
    drafts = [draft]
    if fault == "missing":
        drafts = []
    elif fault == "duplicate":
        drafts = [draft, draft]
    elif fault == "foreign":
        draft.contribution_id = "not-a-parent"
    elif fault == "negative_index":
        draft.finding_indices = [-1]
    elif fault == "large_index":
        draft.finding_indices = [96]
    elif fault == "unresolved":
        resolved.finding_id = "other"
    elif fault == "wrong_source":
        resolved.evidence_anchors = [SimpleNamespace(file_ref="foreign")]
    with pytest.raises(ValueError):
        validate_dependency_assessments(drafts, [context], [candidate], [resolved])
