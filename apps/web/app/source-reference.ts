const DEMO1_VISIBLE_SOURCE_REFERENCES: Record<string, string> = {
  "fixture:mail/customer-a:2026-06-15": "演示文件 · mail/customer-a-status-request-2026-06-15.eml",
  "fixture:crm/customer-a:official-revenue-v3": "演示文件 · crm/customer-a-revenue-close-v3.csv",
  "fixture:forecast/customer-a:revenue-v2": "演示文件 · forecast/customer-a-revenue-forecast-v2.csv",
  "fixture:project/customer-a:weekly-v5": "演示文件 · project/customer-a-weekly-status-v5.json",
};

export type VisibleSourceReference = {
  key: string;
  label: string;
};

export function formatSourceReference(sourceRef: string, index: number): string {
  const label = DEMO1_VISIBLE_SOURCE_REFERENCES[sourceRef];
  if (label) return label;
  return `来源 ${index + 1} 的内部标识已隐藏`;
}

export function projectSourceReferences(
  sourceRefs: readonly string[],
): VisibleSourceReference[] {
  return sourceRefs.map((sourceRef, index) => ({
    key: `source-${index + 1}`,
    label: formatSourceReference(sourceRef, index),
  }));
}
