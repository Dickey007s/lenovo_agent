const DEMO1_VISIBLE_SOURCE_REFERENCES: Record<string, string> = {
  "fixture:mail/customer-a:2026-06-15": "演示数据 · 客户往来邮件（2026-06-15）",
  "fixture:crm/customer-a:official-revenue-v3": "演示数据 · CRM 正式收入记录（v3）",
  "fixture:forecast/customer-a:revenue-v2": "演示数据 · 收入预测表（v2）",
  "fixture:project/customer-a:weekly-v5": "演示数据 · 客户项目周报（v5）",
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
