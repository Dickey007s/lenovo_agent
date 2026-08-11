const DEMO1_VISIBLE_SOURCE_REFERENCES = new Set([
  "fixture:mail/customer-a:2026-06-15",
  "fixture:crm/customer-a:official-revenue-v3",
  "fixture:forecast/customer-a:revenue-v2",
  "fixture:project/customer-a:weekly-v5",
]);

export function formatSourceReference(sourceRef: string, index: number): string {
  if (DEMO1_VISIBLE_SOURCE_REFERENCES.has(sourceRef)) {
    return sourceRef;
  }
  return `来源 ${index + 1} 的内部标识已隐藏`;
}
