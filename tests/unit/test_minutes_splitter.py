import asyncio
import json

import pytest

from services.api.app.application import minutes_splitter as ms

MINUTES = """办公运营周会纪要
参会：行政、招聘、财务

一、上周回顾
上周入职流程整体顺利，本项无需办理。

二、本周需要办理的事项
1. 招聘同事反馈外卖商户BD岗位的要求还没整理：请从《外卖商户BD岗位JD.docx》摘录学历和沟通要求，附依据，不评价候选人。
2. 财务同事要核对一笔往来账：请从《2026往来明细.xlsx》摘录该公司这一行，附原始行，不推断逾期，不修改文件。
3. 行政同事需要吴嘉木的入职安排：请从《3月20日-4月20日入职时间表.csv》摘出入职日期和岗位，不执行人事操作。

三、其他
下次例会定在下周二。
"""


def test_rules_split_keeps_only_numbered_action_items():
    result = ms.split_by_rules(MINUTES)
    assert result.method == "rules" and result.is_multi
    assert len(result.todos) == 3
    assert "上周回顾" not in "".join(t.instruction for t in result.todos)
    assert "下次例会" not in "".join(t.instruction for t in result.todos)
    assert all(t.source_quote and t.source_quote in MINUTES for t in result.todos)


def test_single_item_is_not_multi():
    result = ms.split_by_rules("本周事项\n1. 请从《岗位JD.docx》摘录一项岗位要求并附依据，不评价候选人。\n")
    assert len(result.todos) == 1 and not result.is_multi


def test_too_short_or_too_long_is_rejected():
    with pytest.raises(ms.MinutesSplitError):
        ms.split_by_rules("太短")
    with pytest.raises(ms.MinutesSplitError):
        ms.split_by_rules("x" * (ms.MAX_MINUTES_CHARS + 1))


def test_model_output_quotes_must_come_from_the_minutes():
    good = "请从《外卖商户BD岗位JD.docx》摘录学历和沟通要求，附依据，不评价候选人。"
    content = json.dumps({"todos": [
        {"title": "整理BD岗位要求", "instruction": "整理BD岗位要求。\n" + good, "source_quote": good},
        {"title": "编造", "instruction": "编造的一项待办事项", "source_quote": "纪要里根本没有这句话"},
        {"title": "重复", "instruction": "编造的一项待办事项", "source_quote": ""},
    ]}, ensure_ascii=False)
    todos = ms._parse_model_output("```json\n" + content + "\n```", MINUTES)
    assert [t.title for t in todos] == ["整理BD岗位要求", "编造"]
    assert todos[0].source_quote == good
    assert todos[1].source_quote == ""  # not in the minutes -> dropped, never shown as a source


def test_without_a_model_the_rule_split_is_used():
    result = asyncio.run(ms.split_minutes(MINUTES, base_url="", api_key="", model="m"))
    assert result.method == "rules" and len(result.todos) == 3


def test_unreachable_model_falls_back_to_rules():
    result = asyncio.run(ms.split_minutes(MINUTES, base_url="http://127.0.0.1:9", api_key="k", model="m", timeout=2))
    assert result.method == "rules" and len(result.todos) == 3
