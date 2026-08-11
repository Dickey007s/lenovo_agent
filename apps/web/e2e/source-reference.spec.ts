import { expect, test } from "@playwright/test";

import { formatSourceReference } from "../app/source-reference";

test("Demo 1 source references use a fail-closed display allowlist", () => {
  expect(formatSourceReference("fixture:crm/customer-a:official-revenue-v3", 0))
    .toBe("CRM 客户主数据 · 正式收入 v3");

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
});
