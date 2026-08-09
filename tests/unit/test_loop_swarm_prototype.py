from __future__ import annotations

import re
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).parents[2]
PROTOTYPE = REPOSITORY_ROOT / "docs" / "prototypes" / "loop-swarm-showcase.html"
TARGET_ARCHITECTURE = REPOSITORY_ROOT / "docs" / "TARGET_ARCHITECTURE.md"
FINAL_REFERENCE = REPOSITORY_ROOT / "docs" / "final-reference"


def test_offline_prototype_covers_runtime_components_and_demos() -> None:
    content = PROTOTYPE.read_text(encoding="utf-8")

    for component in (
        "Task Contract",
        "Durable Task State",
        "Context State Manager",
        "Execution Loop",
        "Capability Runtime",
        "Evidence & Quality Verifier",
        "Control Policy",
        "Trace & Checkpoints",
    ):
        assert component in content

    for demo in ("Demo 1", "Demo 2", "Demo 3"):
        assert demo in content


def test_offline_prototype_has_no_remote_assets_or_non_fixture_email_domains() -> None:
    content = PROTOTYPE.read_text(encoding="utf-8")

    assert not re.search(r"(?:src|href)\s*=\s*['\"]https?://", content, re.IGNORECASE)
    domains = {
        match.group("domain").lower()
        for match in re.finditer(
            r"[A-Z0-9._%+-]+@(?P<domain>[A-Z0-9.-]+\.[A-Z]{2,})",
            content,
            re.IGNORECASE,
        )
    }
    assert domains <= {"example.com", "example.org", "example.net"}


def test_target_architecture_does_not_claim_future_capabilities_are_implemented() -> None:
    content = TARGET_ARCHITECTURE.read_text(encoding="utf-8")

    assert "不是当前能力清单" in content
    assert "尚未完成的目标能力" in content
    assert "当前执行结果仍全部来自 Simulator" in content


def test_final_reference_set_preserves_the_reviewed_prototype() -> None:
    reference_prototype = FINAL_REFERENCE / "office_agent_demo_showcase_v5_reference_layout.html"

    assert reference_prototype.read_bytes() == PROTOTYPE.read_bytes()
    assert (FINAL_REFERENCE / "未来办公Agent_一小时汇报讲稿_v5.md").is_file()
    assert (FINAL_REFERENCE / "0716-v2.pptx").is_file()


def test_final_reference_covers_every_next_step_focus() -> None:
    content = (FINAL_REFERENCE / "README.md").read_text(encoding="utf-8")

    for focus in (
        "技术对比及其交互影响",
        "具体用户场景与设计来源",
        "AI 与交互方式的共同演进",
        "技术落地后的前台输出",
        "前端与后端统一策略",
        "基于 8 个最小模块继续 Demo",
    ):
        assert focus in content
