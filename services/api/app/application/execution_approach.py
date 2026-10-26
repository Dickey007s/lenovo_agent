"""Bounded execution proposals and trusted, progressively loaded procedures."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


SkillId = Literal["source_extract", "rule_compare", "table_reconcile"]


class ExecutionApproach(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["primary", "delegate"] = "primary"
    reason: str = Field(default="先由主 Agent 处理，未提出明确的委派收益。", min_length=1, max_length=500)
    benefit: Literal["none", "parallel_depth", "context_isolation", "review_separation"] = "none"


SKILLS = {
    "source_extract": {
        "title": "原文清单整理",
        "description": "从文件提取要求、对象与例外，保留原文依据。",
        "procedure": "按每个工作项目标提取字段；区分通用规则与例外、必需与优先；缺失字段写明未提供，不补造。每项结论回到对应原文。",
    },
    "rule_compare": {
        "title": "规则与例外核对",
        "description": "比较规则、例外和实际记录，区分可执行规则与待裁决冲突。",
        "procedure": "先列规则及明确例外，再核对实际对象；已有优先级时按规则处理。未获批准的变更不是现行规则；真正冲突保留双方依据，不替人批准。",
    },
    "table_reconcile": {
        "title": "表格口径核对",
        "description": "核对期间、记录口径与金额字段，不把账面记录当作实际到账。",
        "procedure": "先核对期间、筛选条件、金额单位和记录口径。优先使用服务端提供的确定性数值；预览截断时不得声称全量。账面记录不能证明银行到账。",
    },
}


def skill_catalog() -> list[dict[str, str]]:
    return [{"id": key, "title": value["title"], "description": value["description"]}
            for key, value in SKILLS.items()]


def load_skills(ids: list[SkillId]) -> list[dict[str, str]]:
    # Only server-authored procedures are loadable; source documents cannot add skills.
    return [{"id": key, **SKILLS[key]} for key in dict.fromkeys(ids)]
