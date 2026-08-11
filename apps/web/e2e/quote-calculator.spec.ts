import { expect, test } from "@playwright/test";

import {
  calculateQuoteSummary,
  updateQuoteItem,
  type QuoteLineItem,
} from "../app/quote-calculator";


const fixtureItems: QuoteLineItem[] = [
  { name: "企业办公 Agent 平台许可", qty: 100, unit_price: 1680, discount: 0.9, subtotal: 151200 },
  { name: "实施与知识库集成", qty: 1, unit_price: 68000, discount: 1, subtotal: 68000 },
  { name: "年度技术支持", qty: 1, unit_price: 36000, discount: 0.95, subtotal: 34200 },
];


test("quote summary is derived from line inputs rather than claimed totals", () => {
  const result = calculateQuoteSummary(fixtureItems, 0.88);

  expect(result.standardTotal).toBe(272000);
  expect(result.discountedTotal).toBe(253400);
  expect(result.savingsAmount).toBe(18600);
  expect(result.effectivePriceRatio).toBeCloseTo(0.931617647, 8);
  expect(result.savingsRate).toBeCloseTo(0.068382353, 8);
  expect(result.belowFloorItems).toEqual([]);
});


test("quantity and discount edits recalculate row and quote totals together", () => {
  const quantityEdit = updateQuoteItem(fixtureItems, 0, { qty: 101 }, 0.88);
  expect(quantityEdit.items[0].subtotal).toBe(152712);
  expect(quantityEdit.discountedTotal).toBe(254912);

  const discountEdit = updateQuoteItem(fixtureItems, 0, { discount: 0.88 }, 0.88);
  expect(discountEdit.items[0].subtotal).toBe(147840);
  expect(discountEdit.discountedTotal).toBe(250040);
  expect(discountEdit.belowFloorItems).toEqual([]);

  const belowFloor = updateQuoteItem(fixtureItems, 0, { discount: 0.87 }, 0.88);
  expect(belowFloor.belowFloorItems).toEqual(["企业办公 Agent 平台许可"]);
});


test("browser calculation matches server half-up rounding for 10.075", () => {
  const result = calculateQuoteSummary([
    { name: "精确舍入", qty: 1, unit_price: 10.075, discount: 1 },
  ]);

  expect(result.valid).toBe(true);
  expect(result.items[0].subtotal).toBe(10.08);
  expect(result.standardTotal).toBe(10.08);
  expect(result.discountedTotal).toBe(10.08);
});


test("one trillion total is accepted and one cent more fails closed", () => {
  const atLimit = calculateQuoteSummary([
    { name: "上限项目", qty: 100, unit_price: 10_000_000_000, discount: 1 },
  ]);

  expect(atLimit.valid).toBe(true);
  expect(atLimit.standardTotal).toBe(1_000_000_000_000);
  expect(atLimit.discountedTotal).toBe(1_000_000_000_000);

  const oneCentOver = calculateQuoteSummary([
    { name: "上限项目", qty: 100, unit_price: 10_000_000_000, discount: 1 },
    { name: "超出一分", qty: 1, unit_price: 0.01, discount: 1 },
  ]);
  expect(oneCentOver.valid).toBe(false);
  expect(oneCentOver.errors).toContain("金额超出浏览器可安全显示范围");
  expect(oneCentOver.standardTotal).toBeNull();
  expect(oneCentOver.discountedTotal).toBeNull();
});


test("ratio 0.90005 displays as 90.01 percent with 10.00 percent savings", () => {
  const result = calculateQuoteSummary([
    { name: "比例边界", qty: 1, unit_price: 10_000, discount: 0.90005 },
  ]);

  expect(result.valid).toBe(true);
  expect(result.effectivePriceRatio).toBeCloseTo(0.90005, 10);
  expect(result.savingsRate).toBeCloseTo(0.09995, 10);
  expect(result.effectivePricePercent).toBe("90.01");
  expect(result.savingsPercent).toBe("10.00");
});


test("invalid rows suppress every aggregate instead of showing a partial total", () => {
  const result = calculateQuoteSummary([
    fixtureItems[0],
    { ...fixtureItems[1], qty: undefined },
    fixtureItems[2],
  ], 0.88);

  expect(result.valid).toBe(false);
  expect(result.errors).toContain("第 2 行数量缺失或不是有效数字");
  expect(result.items[1].subtotal).toBeUndefined();
  expect(result.standardTotal).toBeNull();
  expect(result.discountedTotal).toBeNull();
  expect(result.savingsAmount).toBeNull();
  expect(result.effectivePriceRatio).toBeNull();
  expect(result.savingsRate).toBeNull();
  expect(result.belowFloorItems).toEqual([]);
});


test("unsafe magnitudes fail closed in the browser calculator", () => {
  const result = updateQuoteItem(fixtureItems, 0, { qty: 10_000_000_001 }, 0.88);

  expect(result.valid).toBe(false);
  expect(result.errors).toContain("第 1 行数量超出可核算范围");
  expect(result.standardTotal).toBeNull();
  expect(result.discountedTotal).toBeNull();
});
