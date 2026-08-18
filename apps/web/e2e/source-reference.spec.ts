import { expect, test } from "@playwright/test";

import {
  formatSourceReference,
  projectSourceReferences,
} from "../app/source-reference";

test("Demo 1 source references use a fail-closed display allowlist", () => {
  expect(formatSourceReference("fixture:crm/customer-a:official-revenue-v3", 0))
    .toBe("演示数据 · CRM 正式收入记录（v3）");

  const unsafeReferences = [
    "source:https://intranet.example/private",
    "source:http://127.0.0.1/admin",
    "document:C:/Users/alice/customer-a.pdf",
    "/srv/private/customer-a.json",
    "source:sk-live-123456",
    "fixture:crm/customer-b:private-key",
  ];

  unsafeReferences.forEach((sourceRef, index) => {
    expect(formatSourceReference(sourceRef, index))
      .toBe(`来源 ${index + 1} 的内部标识已隐藏`);
  });

  const visibleProjection = projectSourceReferences([
    "fixture:mail/customer-a:2026-06-15",
    "fixture:crm/customer-a:official-revenue-v3",
    "fixture:forecast/customer-a:revenue-v2",
    "fixture:project/customer-a:weekly-v5",
    ...unsafeReferences,
  ]);
  const serializedProjection = JSON.stringify(visibleProjection);
  expect(serializedProjection).toContain("演示数据 · 客户往来邮件（2026-06-15）");
  expect(serializedProjection).toContain("演示数据 · CRM 正式收入记录（v3）");
  expect(serializedProjection).toContain("演示数据 · 收入预测表（v2）");
  expect(serializedProjection).toContain("演示数据 · 客户项目周报（v5）");
  expect(serializedProjection).not.toContain("fixture:");
  expect(serializedProjection).not.toContain("source:");
  expect(serializedProjection).not.toContain("document:");
  expect(serializedProjection).not.toContain("C:/");
  expect(serializedProjection).not.toContain("/srv/");
});
