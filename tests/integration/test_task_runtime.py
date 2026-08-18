import asyncio
from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest

from packages.contracts import (
    ConflictRecord,
    TaskArtifactBinding,
    TaskBudget,
    TaskControlCommand,
)
from packages.contracts.hashing import canonical_hash
from services.api.app.application.task_storage import (
    InMemoryTaskStore,
    TaskStoreConflictError,
)
from services.api.app.application.tasks import (
    TaskMutationConflictError,
    TaskNotFoundError,
    TaskService,
    TaskTransitionError,
    demo1_contract_draft,
)


OFFICIAL_SOURCE = "fixture:crm/customer-a:official-revenue-v3"
FORECAST_SOURCE = "fixture:forecast/customer-a:revenue-v2"


async def test_demo1_loop_is_atomic_traceable_and_isolates_one_conflict() -> None:
    store = InMemoryTaskStore()
    service = TaskService(store)
    created = await service.create_demo1("user_1")

    waiting = await service.start(
        created.task_id,
        "user_1",
        expected_task_version=created.version,
        idempotency_key="start-demo1-001",
    )

    assert waiting.status == "waiting_input"
    assert waiting.phase == "verify"
    assert waiting.version == 2
    assert waiting.budget.steps_used == 4
    assert waiting.budget.tool_calls_used == 4
    assert len(waiting.artifact_versions) == 5
    assert [item.status for item in waiting.artifact_versions].count("candidate") == 3
    assert [item.status for item in waiting.artifact_versions].count("verified") == 2
    assert len(waiting.verification_reports) == 3
    assert len(waiting.conflicts) == 1
    assert waiting.conflicts[0].status == "open"
    assert waiting.last_commit is None

    statuses = {branch.deliverable_ids[0]: branch.status for branch in waiting.branches}
    assert statuses == {
        "operating-analysis": "waiting_evidence",
        "risk-brief": "committed",
        "reply-draft": "committed",
    }
    operating = next(
        branch for branch in waiting.branches if "operating-analysis" in branch.deliverable_ids
    )
    assert operating.issue_ids == [waiting.conflicts[0].conflict_id]
    assert waiting.conflicts[0].branch_id == operating.branch_id

    history = await service.history(created.task_id, "user_1")
    assert [event.sequence for event in history] == list(range(1, waiting.last_event_sequence + 1))
    assert sum(event.idempotency_key == "start-demo1-001" for event in history) == 1
    event_types = {event.event_type for event in history}
    assert {
        "LOOP_STEP_STARTED",
        "LOOP_STEP_COMPLETED",
        "ARTIFACT_VERSION_CREATED",
        "VERIFICATION_RECORDED",
        "CONFLICT_OPENED",
        "CHECKPOINT_COMMITTED",
    }.issubset(event_types)

    restored = await TaskService(store).get(created.task_id, "user_1")
    assert restored == waiting


async def test_resolving_official_evidence_creates_verified_commit_idempotently() -> None:
    store = InMemoryTaskStore()
    service = TaskService(store)
    created = await service.create_demo1("user_1")
    waiting = await service.start(
        created.task_id,
        "user_1",
        expected_task_version=1,
        idempotency_key="start-demo1-002",
    )
    operating = next(branch for branch in waiting.branches if branch.status == "waiting_evidence")
    waiting_reply = next(
        branch for branch in waiting.branches if "reply-draft" in branch.deliverable_ids
    )
    waiting_reply_head = waiting_reply.artifact_heads["reply-draft"]
    command = TaskControlCommand(
        kind="resolve_evidence",
        branch_id=operating.branch_id,
        selected_source_ref=OFFICIAL_SOURCE,
        expected_task_version=waiting.version,
        idempotency_key="resolve-demo1-002",
    )

    committed = await service.control(created.task_id, "user_1", command)

    assert committed.status == "committed"
    assert committed.phase == "commit"
    assert committed.version == 3
    assert all(branch.status == "committed" for branch in committed.branches)
    assert all(conflict.status == "resolved" for conflict in committed.conflicts)
    assert len(committed.artifact_versions) == 7
    assert len(committed.verification_reports) == 5
    assert committed.last_commit is not None
    assert committed.last_commit.state_hash.startswith("sha256:")
    assert set(committed.last_commit.artifact_version_ids) == {
        branch.artifact_heads[branch.deliverable_ids[0]] for branch in committed.branches
    }
    resolved_artifact = next(
        item
        for item in committed.artifact_versions
        if item.artifact_version_id
        == next(
            branch for branch in committed.branches if branch.branch_id == operating.branch_id
        ).artifact_heads["operating-analysis"]
    )
    assert resolved_artifact.status == "verified"
    assert resolved_artifact.content["selected_revenue_wan"] == 2400
    assert resolved_artifact.content["forecast_revenue_wan"] == 2680
    committed_reply = next(
        branch for branch in committed.branches if "reply-draft" in branch.deliverable_ids
    )
    committed_reply_head = committed_reply.artifact_heads["reply-draft"]
    assert committed_reply_head != waiting_reply_head
    assert waiting_reply_head not in committed.last_commit.artifact_version_ids
    reply_artifact = next(
        item
        for item in committed.artifact_versions
        if item.artifact_version_id == committed_reply_head
    )
    assert reply_artifact.version == 3
    assert reply_artifact.parent_version_id == waiting_reply_head
    assert reply_artifact.content["official_revenue_wan"] == 2400
    assert reply_artifact.content["forecast_revenue_wan"] == 2680
    assert "待正式口径确认" not in reply_artifact.content["body"]
    assert OFFICIAL_SOURCE in reply_artifact.source_refs
    reply_report = next(
        item
        for item in committed.verification_reports
        if item.artifact_version_id == committed_reply_head
    )
    assert reply_report.status == "passed"
    assert any(check.label == "回复与正式经营事实一致" for check in reply_report.checks)

    artifacts_by_id = {
        item.artifact_version_id: item for item in committed.artifact_versions
    }
    reports_by_artifact = {
        item.artifact_version_id: item
        for item in committed.verification_reports
        if item.status == "passed"
    }
    state_artifacts = []
    for head_id in committed.last_commit.artifact_version_ids:
        head = artifacts_by_id[head_id]
        lineage = sorted(
            (
                item
                for item in committed.artifact_versions
                if item.artifact_id == head.artifact_id
            ),
            key=lambda item: item.version,
        )
        state_artifacts.append(
            {
                "branch_id": head.branch_id,
                "deliverable_id": head.deliverable_id,
                "artifact_version_id": head.artifact_version_id,
                "artifact_id": head.artifact_id,
                "version": head.version,
                "parent_version_id": head.parent_version_id,
                "content_digest": head.content_digest,
                "lineage": [
                    {
                        "artifact_version_id": item.artifact_version_id,
                        "version": item.version,
                        "parent_version_id": item.parent_version_id,
                        "content_digest": item.content_digest,
                    }
                    for item in lineage
                ],
            }
        )
    selected_reports = [
        reports_by_artifact[head_id]
        for head_id in committed.last_commit.artifact_version_ids
    ]
    state_payload = {
        "task_id": committed.task_id,
        "task_version": committed.version,
        "contract_digest": canonical_hash(committed.contract),
        "artifact_heads": sorted(
            state_artifacts,
            key=lambda item: (item["branch_id"], item["deliverable_id"]),
        ),
        "verification_reports": [
            item.model_dump(mode="json")
            for item in sorted(selected_reports, key=lambda item: item.report_id)
        ],
        "resolved_conflicts": [
            item.model_dump(mode="json")
            for item in sorted(committed.conflicts, key=lambda item: item.conflict_id)
        ],
    }
    assert canonical_hash(state_payload) == committed.last_commit.state_hash
    for path in (
        "task_version",
        "contract_digest",
        "artifact_heads",
        "verification_reports",
        "resolved_conflicts",
    ):
        changed_payload = deepcopy(state_payload)
        if path == "task_version":
            changed_payload[path] += 1
        elif path == "contract_digest":
            changed_payload[path] = "sha256:" + "0" * 64
        elif path == "artifact_heads":
            changed_payload[path][0]["content_digest"] = "sha256:" + "0" * 64
        elif path == "verification_reports":
            changed_payload[path][0]["checks"][0]["detail"] += " changed"
        else:
            changed_payload[path][0]["resolution"] += " changed"
        assert canonical_hash(changed_payload) != committed.last_commit.state_hash

    replayed = await service.control(created.task_id, "user_1", command)
    assert replayed == committed
    assert len(await service.history(created.task_id, "user_1")) == committed.last_event_sequence

    changed = command.model_copy(update={"reason": "reuse key with another payload"})
    with pytest.raises(TaskMutationConflictError, match="幂等键"):
        await service.control(created.task_id, "user_1", changed)


async def test_committed_artifact_binding_rejects_history_and_changed_facts() -> None:
    service = TaskService(InMemoryTaskStore())
    created = await service.create_demo1("user_1")
    waiting = await service.start(
        created.task_id,
        "user_1",
        expected_task_version=created.version,
        idempotency_key="binding-start-001",
    )
    branch = next(item for item in waiting.branches if item.status == "waiting_evidence")
    committed = await service.control(
        created.task_id,
        "user_1",
        TaskControlCommand(
            kind="resolve_evidence",
            branch_id=branch.branch_id,
            selected_source_ref=OFFICIAL_SOURCE,
            expected_task_version=waiting.version,
            idempotency_key="binding-resolve-001",
        ),
    )
    reply_branch = next(
        item for item in committed.branches if "reply-draft" in item.deliverable_ids
    )
    current_id = reply_branch.artifact_heads["reply-draft"]
    task, artifact, report = await service.get_committed_artifact(
        committed.task_id, current_id, "user_1"
    )
    assert artifact.kind == "reply_draft"
    assert task.last_commit is not None
    binding = TaskArtifactBinding(
        task_id=task.task_id,
        task_version=task.version,
        commit_id=task.last_commit.commit_id,
        commit_state_hash=task.last_commit.state_hash,
        artifact_id=artifact.artifact_id,
        artifact_version_id=artifact.artifact_version_id,
        artifact_version=artifact.version,
        artifact_content_digest=artifact.content_digest,
        deliverable_id=artifact.deliverable_id,
        verification_report_id=report.report_id,
    )
    await service.validate_action_binding(binding, "user_1")

    historical_id = next(
        item.artifact_version_id
        for item in committed.artifact_versions
        if item.artifact_id == artifact.artifact_id
        and item.artifact_version_id != current_id
    )
    with pytest.raises(TaskTransitionError, match="最终提交"):
        await service.get_committed_artifact(
            committed.task_id, historical_id, "user_1"
        )
    with pytest.raises(TaskTransitionError, match="已经变化"):
        await service.validate_action_binding(
            binding.model_copy(update={"artifact_content_digest": "sha256:" + "0" * 64}),
            "user_1",
        )


async def test_task_runtime_rejects_stale_owner_and_unapproved_source() -> None:
    service = TaskService(InMemoryTaskStore())
    created = await service.create_demo1("user_1")

    with pytest.raises(TaskMutationConflictError, match="任务版本"):
        await service.start(
            created.task_id,
            "user_1",
            expected_task_version=2,
            idempotency_key="stale-start-001",
        )
    with pytest.raises(TaskNotFoundError):
        await service.start(
            created.task_id,
            "user_2",
            expected_task_version=1,
            idempotency_key="wrong-owner-001",
        )

    waiting = await service.start(
        created.task_id,
        "user_1",
        expected_task_version=1,
        idempotency_key="valid-start-001",
    )
    operating = next(branch for branch in waiting.branches if branch.status == "waiting_evidence")
    invalid = TaskControlCommand(
        kind="resolve_evidence",
        branch_id=operating.branch_id,
        selected_source_ref=FORECAST_SOURCE,
        expected_task_version=waiting.version,
        idempotency_key="bad-source-001",
    )
    with pytest.raises(TaskTransitionError, match="正式"):
        await service.control(created.task_id, "user_1", invalid)
    unchanged = await service.get(created.task_id, "user_1")
    assert unchanged.version == waiting.version
    assert unchanged.conflicts[0].status == "open"


async def test_branch_controls_and_steer_follow_server_state_machine() -> None:
    service = TaskService(InMemoryTaskStore())
    created = await service.create_demo1("user_1")
    waiting = await service.start(
        created.task_id,
        "user_1",
        expected_task_version=1,
        idempotency_key="control-start-001",
    )
    branch = next(item for item in waiting.branches if item.status == "waiting_evidence")

    pause = TaskControlCommand(
        kind="pause_branch",
        branch_id=branch.branch_id,
        reason="先等待财务复核",
        expected_task_version=waiting.version,
        idempotency_key="pause-branch-001",
    )
    paused = await service.control(created.task_id, "user_1", pause)
    assert paused.status == "paused"
    assert (
        next(item for item in paused.branches if item.branch_id == branch.branch_id).status
        == "paused"
    )
    assert await service.control(created.task_id, "user_1", pause) == paused

    stale_takeover = TaskControlCommand(
        kind="take_over",
        branch_id=branch.branch_id,
        expected_task_version=waiting.version,
        idempotency_key="stale-takeover-001",
    )
    with pytest.raises(TaskMutationConflictError, match="任务版本"):
        await service.control(created.task_id, "user_1", stale_takeover)

    resumed = await service.control(
        created.task_id,
        "user_1",
        TaskControlCommand(
            kind="resume_branch",
            branch_id=branch.branch_id,
            expected_task_version=paused.version,
            idempotency_key="resume-branch-001",
        ),
    )
    assert resumed.status == "waiting_input"
    assert (
        next(item for item in resumed.branches if item.branch_id == branch.branch_id).status
        == "waiting_evidence"
    )

    taken = await service.control(
        created.task_id,
        "user_1",
        TaskControlCommand(
            kind="take_over",
            branch_id=branch.branch_id,
            expected_task_version=resumed.version,
            idempotency_key="take-over-001",
        ),
    )
    assert taken.status == "taken_over"
    returned = await service.control(
        created.task_id,
        "user_1",
        TaskControlCommand(
            kind="return_control",
            branch_id=branch.branch_id,
            expected_task_version=taken.version,
            idempotency_key="return-control-001",
        ),
    )
    assert returned.status == "waiting_input"

    steered = await service.control(
        created.task_id,
        "user_1",
        TaskControlCommand(
            kind="steer",
            instruction="保持客户回复为草稿，并突出正式口径与预测差异。",
            expected_task_version=returned.version,
            idempotency_key="steer-task-001",
        ),
    )
    assert steered.status == "waiting_input"
    assert steered.controls[-1].kind == "steer"
    assert steered.controls[-1].instruction.startswith("保持客户回复")
    assert steered.controls[-1].status == "accepted"
    assert steered.controls[-1].applied_task_version is None
    assert steered.controls[-1].applied_at is None
    steer_events = [
        event
        for event in await service.history(created.task_id, "user_1")
        if event.control_event_id == steered.controls[-1].control_event_id
    ]
    assert [event.event_type for event in steer_events] == ["CONTROL_ACCEPTED"]


async def test_concurrent_controls_allow_only_one_optimistic_version() -> None:
    service = TaskService(InMemoryTaskStore())
    created = await service.create_demo1("user_1")
    waiting = await service.start(
        created.task_id,
        "user_1",
        expected_task_version=1,
        idempotency_key="concurrent-start-001",
    )
    branch = next(item for item in waiting.branches if item.status == "waiting_evidence")
    commands = [
        TaskControlCommand(
            kind="pause_branch",
            branch_id=branch.branch_id,
            expected_task_version=waiting.version,
            idempotency_key="concurrent-pause-001",
        ),
        TaskControlCommand(
            kind="take_over",
            branch_id=branch.branch_id,
            expected_task_version=waiting.version,
            idempotency_key="concurrent-take-001",
        ),
    ]

    results = await asyncio.gather(
        *(service.control(created.task_id, "user_1", item) for item in commands),
        return_exceptions=True,
    )

    assert sum(isinstance(item, TaskMutationConflictError) for item in results) == 1
    assert sum(not isinstance(item, Exception) for item in results) == 1
    current = await service.get(created.task_id, "user_1")
    assert current.version == waiting.version + 1


async def test_prestart_branch_control_is_rejected_without_mutation() -> None:
    service = TaskService(InMemoryTaskStore())
    created = await service.create_demo1("user_1")
    branch = created.branches[0]

    with pytest.raises(TaskTransitionError, match="启动前"):
        await service.control(
            created.task_id,
            "user_1",
            TaskControlCommand(
                kind="pause_branch",
                branch_id=branch.branch_id,
                expected_task_version=created.version,
                idempotency_key="prestart-pause-001",
            ),
        )

    unchanged = await service.get(created.task_id, "user_1")
    assert unchanged == created
    assert len(await service.history(created.task_id, "user_1")) == 1


async def test_old_idempotency_key_replays_original_snapshot_after_later_mutation() -> None:
    store = InMemoryTaskStore()
    service = TaskService(store)
    created = await service.create_demo1("user_1")
    waiting = await service.start(
        created.task_id,
        "user_1",
        expected_task_version=created.version,
        idempotency_key="replay-original-start-001",
    )
    branch = next(item for item in waiting.branches if item.status == "waiting_evidence")
    paused = await service.control(
        created.task_id,
        "user_1",
        TaskControlCommand(
            kind="pause_branch",
            branch_id=branch.branch_id,
            expected_task_version=waiting.version,
            idempotency_key="replay-original-pause-001",
        ),
    )
    event_count = len(await service.history(created.task_id, "user_1"))
    artifact_count = len((await store.load(created.task_id, "user_1")).artifact_versions)

    replayed = await service.start(
        created.task_id,
        "user_1",
        expected_task_version=created.version,
        idempotency_key="replay-original-start-001",
    )

    assert replayed == waiting
    assert await service.get(created.task_id, "user_1") == paused
    assert len(await service.history(created.task_id, "user_1")) == event_count
    assert len((await store.load(created.task_id, "user_1")).artifact_versions) == artifact_count


async def test_evidence_resolution_does_not_commit_with_another_open_conflict() -> None:
    store = InMemoryTaskStore()
    service = TaskService(store)
    created = await service.create_demo1("user_1")
    waiting = await service.start(
        created.task_id,
        "user_1",
        expected_task_version=created.version,
        idempotency_key="global-conflict-start-001",
    )
    branch = next(item for item in waiting.branches if item.status == "waiting_evidence")
    extra_conflict = ConflictRecord(
        conflict_id="task_conflict_extra_open",
        task_id=waiting.task_id,
        branch_id=branch.branch_id,
        subject="客户 A 补充收入口径",
        summary="另一项正式口径仍待确认，任务不能进入最终提交。",
        source_refs=[OFFICIAL_SOURCE, FORECAST_SOURCE],
        candidate_values=["正式值", "预测值"],
        opened_at=datetime.now(UTC),
    )
    now = datetime.now(UTC)
    with_extra = waiting.model_copy(
        update={
            "branches": [
                item.model_copy(
                    update={
                        "issue_ids": [
                            *item.issue_ids,
                            extra_conflict.conflict_id,
                        ]
                    }
                )
                if item.branch_id == branch.branch_id
                else item
                for item in waiting.branches
            ],
            "conflicts": [*waiting.conflicts, extra_conflict],
            "version": waiting.version + 1,
            "last_event_sequence": waiting.last_event_sequence + 1,
            "updated_at": now,
        }
    )
    injected_event = (await service.history(created.task_id, "user_1"))[-1].model_dump(
        mode="json"
    )
    injected_event.update(
        {
            "sequence": with_extra.last_event_sequence,
            "event_id": "task_evt_extra_conflict_opened",
            "task_version": with_extra.version,
            "branch_id": branch.branch_id,
            "artifact_version_id": None,
            "control_event_id": None,
            "event_type": "CONFLICT_OPENED",
            "idempotency_key": None,
            "payload": {"conflict_id": extra_conflict.conflict_id},
            "occurred_at": now.isoformat(),
        }
    )
    await store.commit(
        waiting.task_id,
        waiting.owner_id,
        waiting.version,
        with_extra.model_dump(mode="json"),
        [injected_event],
        [],
    )
    with_extra = await service.get(created.task_id, "user_1")
    command = TaskControlCommand(
        kind="resolve_evidence",
        branch_id=branch.branch_id,
        selected_source_ref=OFFICIAL_SOURCE,
        expected_task_version=with_extra.version,
        idempotency_key="global-conflict-resolve-001",
    )

    updated = await service.control(created.task_id, "user_1", command)

    assert updated.status == "waiting_input"
    assert updated.phase == "verify"
    assert updated.last_commit is None
    assert [item.status for item in updated.conflicts].count("open") == 1
    assert len(updated.artifact_versions) == len(waiting.artifact_versions) + 1
    resolution_events = await service.history(
        created.task_id,
        "user_1",
        after_sequence=with_extra.last_event_sequence,
    )
    assert all(event.event_type != "TASK_COMMITTED" for event in resolution_events)
    updated_branch = next(
        item for item in updated.branches if item.branch_id == branch.branch_id
    )
    assert updated_branch.status == "waiting_evidence"
    assert updated_branch.issue_ids == [extra_conflict.conflict_id]

    committed = await service.control(
        created.task_id,
        "user_1",
        TaskControlCommand(
            kind="resolve_evidence",
            branch_id=branch.branch_id,
            selected_source_ref=OFFICIAL_SOURCE,
            expected_task_version=updated.version,
            idempotency_key="global-conflict-resolve-002",
        ),
    )
    assert committed.status == "committed"
    assert all(item.status != "open" for item in committed.conflicts)


async def test_task_store_rejects_digest_lineage_and_missing_head_corruption() -> None:
    store = InMemoryTaskStore()
    service = TaskService(store)
    created = await service.create_demo1("user_1")
    waiting = await service.start(
        created.task_id,
        "user_1",
        expected_task_version=created.version,
        idempotency_key="store-validation-start-001",
    )
    branch = next(item for item in waiting.branches if item.status == "waiting_evidence")
    candidate = next(
        item
        for item in waiting.artifact_versions
        if item.artifact_version_id == branch.artifact_heads["operating-analysis"]
    )
    last_event = (await service.history(created.task_id, "user_1"))[-1]

    def mutation_payload(
        tag: str,
        artifact: dict | None = None,
        *,
        remove_head: bool = False,
    ) -> tuple[dict, list[dict]]:
        snapshot = waiting.model_dump(mode="json")
        snapshot["version"] = waiting.version + 1
        snapshot["last_event_sequence"] = waiting.last_event_sequence + 1
        if artifact is not None:
            snapshot["artifact_versions"].append(artifact)
        for raw_branch in snapshot["branches"]:
            if raw_branch["branch_id"] != branch.branch_id:
                continue
            if remove_head:
                raw_branch["artifact_heads"].pop("operating-analysis")
            elif artifact is not None:
                raw_branch["artifact_heads"]["operating-analysis"] = artifact[
                    "artifact_version_id"
                ]
        event = last_event.model_dump(mode="json")
        event.update(
            {
                "sequence": waiting.last_event_sequence + 1,
                "event_id": f"task_evt_store_validation_{tag}",
                "task_version": waiting.version + 1,
                "artifact_version_id": (
                    artifact["artifact_version_id"] if artifact is not None else None
                ),
                "idempotency_key": None,
                "payload": {},
            }
        )
        return snapshot, [event]

    bad_digest = candidate.model_dump(mode="json")
    bad_digest.update(
        {
            "artifact_version_id": "task_artifact_ver_bad_digest",
            "version": candidate.version + 1,
            "parent_version_id": candidate.artifact_version_id,
            "content": candidate.content | {"selected_revenue_wan": 2400},
        }
    )
    snapshot, events = mutation_payload("digest", bad_digest)
    with pytest.raises(TaskStoreConflictError, match="content digest"):
        await store.commit(
            waiting.task_id,
            waiting.owner_id,
            waiting.version,
            snapshot,
            events,
            [bad_digest],
        )

    bad_parent = candidate.model_dump(mode="json")
    bad_parent.update(
        {
            "artifact_version_id": "task_artifact_ver_bad_parent",
            "version": candidate.version + 1,
            "parent_version_id": "task_artifact_ver_not_the_head",
        }
    )
    snapshot, events = mutation_payload("parent", bad_parent)
    with pytest.raises(TaskStoreConflictError, match="parent version"):
        await store.commit(
            waiting.task_id,
            waiting.owner_id,
            waiting.version,
            snapshot,
            events,
            [bad_parent],
        )

    snapshot, events = mutation_payload("head", remove_head=True)
    with pytest.raises(TaskStoreConflictError, match="missing an artifact lineage head"):
        await store.commit(
            waiting.task_id,
            waiting.owner_id,
            waiting.version,
            snapshot,
            events,
            [],
        )

    assert await service.get(created.task_id, "user_1") == waiting


async def test_execution_budget_and_deadline_stop_before_mutation() -> None:
    budget_service = TaskService(InMemoryTaskStore())
    limited = demo1_contract_draft().model_copy(
        update={
            "budget": TaskBudget(
                max_steps=3,
                max_tool_calls=30,
                max_runtime_seconds=3_600,
            )
        }
    )
    budget_task = await budget_service.create(limited, "user_1")
    with pytest.raises(TaskTransitionError, match="步骤预算"):
        await budget_service.start(
            budget_task.task_id,
            "user_1",
            expected_task_version=budget_task.version,
            idempotency_key="budget-start-001",
        )
    assert await budget_service.get(budget_task.task_id, "user_1") == budget_task
    assert len(await budget_service.history(budget_task.task_id, "user_1")) == 1

    deadline_service = TaskService(InMemoryTaskStore())
    expired = demo1_contract_draft().model_copy(
        update={"deadline_at": datetime.now(UTC) - timedelta(seconds=1)}
    )
    deadline_task = await deadline_service.create(expired, "user_1")
    with pytest.raises(TaskTransitionError, match="截止时间"):
        await deadline_service.start(
            deadline_task.task_id,
            "user_1",
            expected_task_version=deadline_task.version,
            idempotency_key="deadline-start-001",
        )
    assert await deadline_service.get(deadline_task.task_id, "user_1") == deadline_task
    assert len(await deadline_service.history(deadline_task.task_id, "user_1")) == 1
