from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, Overflow as DecimalOverflow, ROUND_HALF_UP, localcontext
from typing import Any, Literal


_CENT = Decimal("0.01")
_HUNDRED = Decimal("100")
_TEN = Decimal("10")
_MAX_ITEMS = 100
_MAX_INPUT = Decimal("10000000000")
_MAX_DECIMAL_PLACES = 8
_MAX_SAFE_TOTAL = Decimal("1000000000000.00")


class QuoteCalculationError(ValueError):
    pass


@dataclass(frozen=True)
class QuoteCalculation:
    quote_id: str
    currency: str
    line_count: int
    standard_total: Decimal
    discounted_total: Decimal
    savings_amount: Decimal
    effective_price_ratio: Decimal | None
    savings_rate: Decimal | None
    approved_floor: Decimal | None
    below_floor_items: tuple[str, ...]
    line_subtotals: tuple[Decimal, ...]
    mismatches: tuple[str, ...]


QuoteQuestionIntent = Literal["calculation", "source"]


def quote_question_intent(text: str) -> QuoteQuestionIntent | None:
    normalized = "".join(text.lower().split())
    office_action_terms = (
        "写进",
        "写入",
        "填入",
        "更新",
        "修改",
        "保存到",
        "发送",
        "发给",
        "创建",
        "新增",
        "导入",
        "起草",
    )
    if any(term in normalized for term in office_action_terms):
        return None
    calculation_terms = (
        "总折扣",
        "综合折扣",
        "综合折后比例",
        "当前折扣",
        "折扣多少",
        "折扣是多少",
        "折扣底线",
        "最低折后比例",
        "核算报价",
        "打几折",
        "折后总价",
        "折后价",
        "标准总价",
        "原价",
        "优惠额",
        "优惠金额",
        "优惠率",
        "总价",
        "总计",
        "合计",
        "重算",
        "再算",
        "重新计算",
        "核对金额",
        "核对报价",
        "核对一下报价",
        "检查报价",
        "报价算对",
        "金额对吗",
        "计算正确吗",
        "怎么算",
        "计算过程",
        "计算依据",
    )
    source_terms = (
        "数据哪里来",
        "数据从哪里来",
        "数据来源",
        "哪里来的",
        "来源是什么",
        "依据是什么",
    )
    if any(term in normalized for term in calculation_terms):
        return "calculation"
    if any(term in normalized for term in source_terms):
        return "source"
    return None


def merge_quote_workspace_context(
    server_content: dict[str, Any], workspace_content: dict[str, Any] | None
) -> dict[str, Any]:
    if not isinstance(workspace_content, dict) or not workspace_content:
        raise QuoteCalculationError("当前报价工作区上下文为空")
    server_items = server_content.get("items")
    workspace_items = workspace_content.get("items")
    if not isinstance(server_items, list) or not server_items:
        raise QuoteCalculationError("服务端报价没有可核算的行项目")
    if not isinstance(workspace_items, list) or len(workspace_items) != len(server_items):
        raise QuoteCalculationError("当前工作区行项目与服务端报价版本不一致")

    merged_items: list[dict[str, Any]] = []
    for index, (server_item, workspace_item) in enumerate(
        zip(server_items, workspace_items, strict=True), start=1
    ):
        if not isinstance(server_item, dict) or not isinstance(workspace_item, dict):
            raise QuoteCalculationError(f"第 {index} 行不是有效的报价项目")
        merged_items.append(
            {
                **server_item,
                "name": workspace_item.get("name", server_item.get("name")),
                "qty": workspace_item.get("qty"),
                "discount": workspace_item.get("discount"),
            }
        )

    merged = {
        **server_content,
        "items": merged_items,
        "valid_until": workspace_content.get(
            "valid_until", server_content.get("valid_until")
        ),
    }
    calculation = calculate_quote(merged)
    merged["items"] = [
        {**item, "subtotal": _json_number(calculation.line_subtotals[index])}
        for index, item in enumerate(merged_items)
    ]
    merged["total"] = _json_number(calculation.discounted_total)
    if _editable_quote_projection(merged) != _editable_quote_projection(server_content):
        merged["approval"] = {
            "status": "needs_review",
            "reason": "当前报价相对基线有修改，不能沿用基线审批结论",
        }
    return merged


def calculate_quote(content: dict[str, Any]) -> QuoteCalculation:
    with localcontext() as context:
        context.prec = 50
        context.rounding = ROUND_HALF_UP
        try:
            return _calculate_quote(content)
        except (DecimalOverflow, InvalidOperation, OverflowError) as exc:
            raise QuoteCalculationError("报价数值超出可核算范围") from exc


def _calculate_quote(content: dict[str, Any]) -> QuoteCalculation:
    items = content.get("items")
    if not isinstance(items, list) or not items:
        raise QuoteCalculationError("当前报价没有可核算的行项目")
    if len(items) > _MAX_ITEMS:
        raise QuoteCalculationError(f"报价行项目不能超过 {_MAX_ITEMS} 行")

    approved_floor = _optional_ratio(content.get("approved_floor"), "最低折后比例")
    standard_total = Decimal("0")
    discounted_total = Decimal("0")
    line_subtotals: list[Decimal] = []
    below_floor_items: list[str] = []
    mismatches: list[str] = []

    for index, raw_item in enumerate(items, start=1):
        if not isinstance(raw_item, dict):
            raise QuoteCalculationError(f"第 {index} 行不是有效的报价项目")
        name = str(raw_item.get("name") or f"第 {index} 行")
        quantity = _required_decimal(raw_item.get("qty"), f"第 {index} 行数量")
        unit_price = _required_decimal(raw_item.get("unit_price"), f"第 {index} 行标准价")
        discount = _required_decimal(raw_item.get("discount"), f"第 {index} 行折后比例")
        if quantity < 0:
            raise QuoteCalculationError(f"第 {index} 行数量不能为负数")
        if unit_price < 0:
            raise QuoteCalculationError(f"第 {index} 行标准价不能为负数")
        if discount < 0 or discount > 1:
            raise QuoteCalculationError(
                f"第 {index} 行折后比例必须在 0% 到 100% 之间"
            )

        standard_line = (quantity * unit_price).quantize(_CENT, rounding=ROUND_HALF_UP)
        discounted_line = (standard_line * discount).quantize(
            _CENT, rounding=ROUND_HALF_UP
        )
        standard_total += standard_line
        discounted_total += discounted_line
        if standard_total > _MAX_SAFE_TOTAL or discounted_total > _MAX_SAFE_TOTAL:
            raise QuoteCalculationError("报价总额超出可核算范围")
        line_subtotals.append(discounted_line)

        claimed_subtotal = _optional_decimal(raw_item.get("subtotal"))
        if claimed_subtotal is not None and claimed_subtotal.quantize(
            _CENT, rounding=ROUND_HALF_UP
        ) != discounted_line:
            mismatches.append(f"{name}的小计已过期")
        if approved_floor is not None and discount < approved_floor:
            below_floor_items.append(name)

    standard_total = standard_total.quantize(_CENT, rounding=ROUND_HALF_UP)
    discounted_total = discounted_total.quantize(_CENT, rounding=ROUND_HALF_UP)
    savings_amount = (standard_total - discounted_total).quantize(
        _CENT, rounding=ROUND_HALF_UP
    )
    declared_total = _optional_decimal(content.get("total"))
    if declared_total is not None and declared_total.quantize(
        _CENT, rounding=ROUND_HALF_UP
    ) != discounted_total:
        mismatches.append("报价表总计已过期")

    effective_price_ratio = None
    savings_rate = None
    if standard_total > 0:
        effective_price_ratio = discounted_total / standard_total
        savings_rate = savings_amount / standard_total

    return QuoteCalculation(
        quote_id=str(content.get("quote_id") or "当前报价"),
        currency=str(content.get("currency") or "CNY"),
        line_count=len(items),
        standard_total=standard_total,
        discounted_total=discounted_total,
        savings_amount=savings_amount,
        effective_price_ratio=effective_price_ratio,
        savings_rate=savings_rate,
        approved_floor=approved_floor,
        below_floor_items=tuple(below_floor_items),
        line_subtotals=tuple(line_subtotals),
        mismatches=tuple(mismatches),
    )


def render_quote_answer(
    content: dict[str, Any], intent: QuoteQuestionIntent
) -> str:
    calculation = calculate_quote(content)
    source_line = (
        f"数据来源：你当前屏幕中的报价工作台 {calculation.quote_id}，"
        f"共 {calculation.line_count} 行；我只按每行的数量 × 标准价 × 折后比例重算，"
        "没有使用历史对话里的金额，也没有访问真实 CRM。"
        "这张报价表是演示工作区的固定数据，不是真实客户记录。"
    )
    approval = content.get("approval")
    review_line = ""
    if isinstance(approval, dict) and approval.get("status") == "needs_review":
        review_line = (
            "\n\n当前报价相对演示基线有修改，计算使用的是屏幕中的最新值；"
            "这些修改需要重新复核，不能沿用基线审批结论。"
        )

    if calculation.effective_price_ratio is None:
        return (
            f"{source_line}\n\n"
            "当前标准总价为 0，无法计算有意义的综合折扣；"
            f"请先补充有效的数量和标准价。{review_line}"
        )

    prefix = "¥" if calculation.currency.upper() == "CNY" else f"{calculation.currency} "
    ratio_percent = _percent(calculation.effective_price_ratio)
    discount_zhe = _number(calculation.effective_price_ratio * _TEN)
    savings_percent = _percent(calculation.savings_rate or Decimal("0"))
    summary = (
        f"**综合折后比例：{ratio_percent}，约 {discount_zhe} 折。**\n\n"
        f"- 标准总价：{prefix}{_money(calculation.standard_total)}\n"
        f"- 折后总价：{prefix}{_money(calculation.discounted_total)}\n"
        f"- 优惠金额：{prefix}{_money(calculation.savings_amount)}\n"
        f"- 优惠率：{savings_percent}"
    )
    floor_line = _floor_summary(calculation)
    mismatch_line = ""
    if calculation.mismatches:
        mismatch_line = (
            "\n\n检测到表内旧的小计或总计与行项目不一致；"
            "以上结果已忽略旧合计，并从当前行项目重新计算。"
        )

    if intent == "source":
        return (
            f"{source_line}\n\n当前重算结果如下：\n\n{summary}\n\n"
            f"{floor_line}{review_line}{mismatch_line}"
        )
    return (
        f"我已按当前报价工作台逐行重算：\n\n{summary}\n\n"
        f"{floor_line}\n\n{source_line}{review_line}{mismatch_line}"
    )


def _floor_summary(calculation: QuoteCalculation) -> str:
    if calculation.approved_floor is None:
        return "当前报价没有提供可核验的最低折后比例。"
    floor = _percent(calculation.approved_floor)
    floor_zhe = _number(calculation.approved_floor * _TEN)
    if calculation.below_floor_items:
        items = "、".join(calculation.below_floor_items)
        return (
            f"最低折后比例是 {floor}（{floor_zhe} 折）；"
            f"低于底线的项目：{items}。"
        )
    ratio = calculation.effective_price_ratio or Decimal("0")
    delta = (ratio - calculation.approved_floor) * _HUNDRED
    return (
        f"各行折后比例均不低于 {floor}（{floor_zhe} 折），符合批准底线；"
        f"综合折后比例高出底线 {_number(delta)} 个百分点。"
    )


def _editable_quote_projection(content: dict[str, Any]) -> dict[str, Any]:
    items = content.get("items")
    editable_items = []
    if isinstance(items, list):
        editable_items = [
            {
                "name": item.get("name"),
                "qty": item.get("qty"),
                "discount": item.get("discount"),
            }
            for item in items
            if isinstance(item, dict)
        ]
    return {
        "valid_until": content.get("valid_until"),
        "items": editable_items,
    }


def _required_decimal(value: Any, label: str) -> Decimal:
    parsed = _optional_decimal(value)
    if parsed is None:
        raise QuoteCalculationError(f"{label}缺失或不是有效数字")
    if abs(parsed) > _MAX_INPUT:
        raise QuoteCalculationError(f"{label}超出可核算范围")
    if parsed.as_tuple().exponent < -_MAX_DECIMAL_PLACES:
        raise QuoteCalculationError(f"{label}最多支持 {_MAX_DECIMAL_PLACES} 位小数")
    return parsed


def _optional_decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool) or not isinstance(
        value, (int, float, Decimal)
    ):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _optional_ratio(value: Any, label: str) -> Decimal | None:
    if value is None:
        return None
    parsed = _required_decimal(value, label)
    if parsed < 0 or parsed > 1:
        raise QuoteCalculationError(f"{label}必须在 0% 到 100% 之间")
    return parsed


def _money(value: Decimal) -> str:
    rounded = value.quantize(_CENT, rounding=ROUND_HALF_UP)
    if rounded == rounded.to_integral():
        return f"{int(rounded):,}"
    return f"{rounded:,.2f}"


def _number(value: Decimal) -> str:
    rounded = value.quantize(_CENT, rounding=ROUND_HALF_UP)
    return f"{rounded:.2f}"


def _percent(value: Decimal) -> str:
    return f"{_number(value * _HUNDRED)}%"


def _json_number(value: Decimal) -> int | float:
    if value == value.to_integral():
        return int(value)
    return float(value)
