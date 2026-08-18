from decimal import Decimal, localcontext

import pytest

from services.api.app.application.conversations import _default_content
from services.api.app.application.quote_calculator import (
    QuoteCalculationError,
    calculate_quote,
    merge_quote_workspace_context,
    quote_question_intent,
    render_quote_answer,
)


def test_quote_fixture_calculation_is_exact() -> None:
    result = calculate_quote(_default_content("quote"))

    assert result.standard_total == Decimal("272000.00")
    assert result.discounted_total == Decimal("253400.00")
    assert result.savings_amount == Decimal("18600.00")
    with localcontext() as context:
        context.prec = 50
        assert result.effective_price_ratio == Decimal("253400") / Decimal("272000")
        assert result.savings_rate == Decimal("18600") / Decimal("272000")
    assert result.below_floor_items == ()
    assert result.mismatches == ()

    answer = render_quote_answer(_default_content("quote"), "calculation")
    assert "¥272,000" in answer
    assert "¥253,400" in answer
    assert "¥18,600" in answer
    assert "93.16%" in answer
    assert "9.32 折" in answer
    assert "6.84%" in answer
    assert "不低于 88.00%" in answer


def test_claimed_subtotals_and_total_are_not_authoritative() -> None:
    content = _default_content("quote")
    content["items"][0]["subtotal"] = 1_770_000
    content["total"] = 2_000_000

    result = calculate_quote(content)

    assert result.discounted_total == Decimal("253400.00")
    assert result.mismatches == (
        "企业办公 Agent 平台许可的小计已过期",
        "报价表总计已过期",
    )
    answer = render_quote_answer(content, "source")
    assert "¥253,400" in answer
    assert "¥2,000,000" not in answer
    assert "忽略旧合计" in answer


def test_quantity_change_recomputes_from_base_fields() -> None:
    content = _default_content("quote")
    content["items"][0]["qty"] = 101

    result = calculate_quote(content)

    assert result.line_subtotals[0] == Decimal("152712.00")
    assert result.discounted_total == Decimal("254912.00")
    assert "企业办公 Agent 平台许可的小计已过期" in result.mismatches


def test_quote_money_rounds_half_up_per_line() -> None:
    result = calculate_quote(
        {
            "items": [
                {"name": "A", "qty": 1, "unit_price": 0.025, "discount": 1},
                {"name": "B", "qty": 1, "unit_price": 0.025, "discount": 1},
            ]
        }
    )

    assert result.line_subtotals == (Decimal("0.03"), Decimal("0.03"))
    assert result.discounted_total == Decimal("0.06")


def test_quote_money_rounds_10_075_half_up() -> None:
    result = calculate_quote(
        {
            "items": [
                {"name": "精确舍入", "qty": 1, "unit_price": 10.075, "discount": 1}
            ]
        }
    )

    assert result.standard_total == Decimal("10.08")
    assert result.line_subtotals == (Decimal("10.08"),)
    assert result.discounted_total == Decimal("10.08")


def test_quote_total_limit_is_inclusive_and_one_cent_over_fails_closed() -> None:
    at_limit = calculate_quote(
        {
            "items": [
                {
                    "name": "上限项目",
                    "qty": 100,
                    "unit_price": 10_000_000_000,
                    "discount": 1,
                }
            ]
        }
    )

    assert at_limit.standard_total == Decimal("1000000000000.00")
    assert at_limit.discounted_total == Decimal("1000000000000.00")

    with pytest.raises(QuoteCalculationError, match="报价总额超出可核算范围"):
        calculate_quote(
            {
                "items": [
                    {
                        "name": "上限项目",
                        "qty": 100,
                        "unit_price": 10_000_000_000,
                        "discount": 1,
                    },
                    {"name": "超出一分", "qty": 1, "unit_price": 0.01, "discount": 1},
                ]
            }
        )


def test_ratio_display_rounds_90005_consistently() -> None:
    content = {
        "items": [
            {"name": "比例边界", "qty": 1, "unit_price": 10_000, "discount": 0.90005}
        ]
    }

    result = calculate_quote(content)
    answer = render_quote_answer(content, "calculation")

    assert result.effective_price_ratio == Decimal("0.90005")
    assert result.savings_rate == Decimal("0.09995")
    assert "综合折后比例：90.01%" in answer
    assert "优惠率：10.00%" in answer


def test_floor_is_checked_per_line() -> None:
    content = _default_content("quote")
    content["items"][0]["discount"] = 0.87
    content["items"][1]["discount"] = 1

    result = calculate_quote(content)

    assert result.below_floor_items == ("企业办公 Agent 平台许可",)
    assert "低于底线的项目" in render_quote_answer(content, "calculation")


@pytest.mark.parametrize(
    ("patch", "error"),
    [
        ({"qty": -1}, "数量不能为负数"),
        ({"unit_price": "not-a-number"}, "标准价缺失或不是有效数字"),
        ({"discount": 1.01}, "折后比例必须在 0% 到 100% 之间"),
        ({"discount": float("nan")}, "折后比例缺失或不是有效数字"),
        ({"discount": True}, "折后比例缺失或不是有效数字"),
    ],
)
def test_invalid_quote_fields_do_not_produce_guessed_totals(
    patch: dict[str, object], error: str
) -> None:
    content = _default_content("quote")
    content["items"][0].update(patch)

    with pytest.raises(QuoteCalculationError, match=error):
        calculate_quote(content)


def test_huge_decimal_fails_closed() -> None:
    content = _default_content("quote")
    content["items"][0]["qty"] = Decimal("1e1000000")

    with pytest.raises(QuoteCalculationError, match="报价数值超出可核算范围"):
        calculate_quote(content)


def test_workspace_context_cannot_override_server_owned_quote_fields() -> None:
    server_content = _default_content("quote")
    workspace_content = _default_content("quote")
    workspace_content.update(
        {
            "quote_id": "Q-FORGED",
            "customer": "伪造客户",
            "currency": "USD",
            "approved_floor": 0.01,
            "approval": {"status": "forged"},
            "total": 1,
            "valid_until": "2026-08-31",
        }
    )
    workspace_content["items"][0].update(
        {
            "qty": 101,
            "unit_price": 2_000_000,
            "discount": 0.8,
            "subtotal": 1,
        }
    )

    merged = merge_quote_workspace_context(server_content, workspace_content)

    assert merged["quote_id"] == "Q-991-V3"
    assert merged["customer"] == "客户 A"
    assert merged["currency"] == "CNY"
    assert merged["approved_floor"] == 0.88
    assert merged["approval"]["status"] == "needs_review"
    assert "相对基线有修改" in merged["approval"]["reason"]
    assert merged["valid_until"] == "2026-08-31"
    assert merged["items"][0]["qty"] == 101
    assert merged["items"][0]["unit_price"] == 1680
    assert merged["items"][0]["discount"] == 0.8
    assert merged["items"][0]["subtotal"] == 135744
    assert merged["total"] == 237944


def test_explicit_empty_workspace_context_does_not_fall_back_to_saved_quote() -> None:
    with pytest.raises(QuoteCalculationError, match="当前报价工作区上下文为空"):
        merge_quote_workspace_context(_default_content("quote"), {})


def test_zero_standard_total_has_no_fake_percentage() -> None:
    content = {
        "quote_id": "Q-ZERO",
        "items": [{"name": "Free", "qty": 0, "unit_price": 0, "discount": 1}],
    }

    result = calculate_quote(content)

    assert result.effective_price_ratio is None
    assert "无法计算有意义的综合折扣" in render_quote_answer(content, "calculation")


@pytest.mark.parametrize(
    ("text", "intent"),
    [
        ("总折扣多少，你再算一下", "calculation"),
        ("再算一次", "calculation"),
        ("你的数据是哪里来的", "source"),
        ("计算依据是什么", "calculation"),
        ("把折后总价写进邮件", None),
        ("按总折扣把报价发给客户", None),
        ("更新报价总计", None),
        ("把原价保存到项目文档", None),
        ("今天是几号？", None),
    ],
)
def test_quote_question_intent(text: str, intent: str | None) -> None:
    assert quote_question_intent(text) == intent
