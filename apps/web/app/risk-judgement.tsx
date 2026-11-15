"use client";

import "./risk-judgement.css";

// Five-factor judgement record (人机共驾设计指导手册 v1.1, 4.2-4.5), rendered read-only.
const RULE_LABELS: Record<string, string> = {
  restricted_first: "受限优先", take_highest: "就高", unknown_as_high: "不明按高",
  reason_no_downgrade: "理由不降级", per_action: "逐动作定级", recheck_on_change: "变化即重判",
};
export type RiskJudgement = {
  factors: { key: string; label: string; value: string; value_label: string; floor: string; assumed: boolean; basis: string; drives_level: boolean }[];
  rules_applied: string[]; rule_notes: string[]; risk_level: string; autonomy_cap: string;
  action_form: string; action_form_label: string; autonomy_level: string;
  intervention: string | null; intervention_label: string | null; follow_ups: string[];
};

export function JudgementPanel({ judgement }: { judgement: RiskJudgement }) {
  return <div className="office-judgement" aria-label="五因子判定过程">
    <table><thead><tr><th>判定因子</th><th>取值</th><th>等级下限</th></tr></thead><tbody>
      {judgement.factors.map(item => <tr key={item.key} className={item.drives_level ? "is-driver" : ""}>
        <th scope="row">{item.label}</th>
        <td>{item.value_label}{item.assumed && <em>不明按高</em>}{item.basis && <small>{item.basis}</small>}</td>
        <td><b className={`wf-risk level-${item.floor}`}>{item.floor}</b></td>
      </tr>)}
    </tbody></table>
    <p className="office-judgement-result"><b>{judgement.risk_level}</b> 合并规则：{judgement.rules_applied.map(rule => RULE_LABELS[rule] ?? rule).join(" → ")}</p>
    <p className="office-judgement-result">自主程度 = min（等级上限 {judgement.autonomy_cap}，{judgement.action_form_label}）= <b>{judgement.autonomy_level}</b></p>
    {judgement.rule_notes.length > 0 && <ul>{judgement.rule_notes.map(note => <li key={note}>{note}</li>)}</ul>}
    {judgement.intervention_label && <p className="office-judgement-next">此刻处理：{judgement.intervention_label}{judgement.follow_ups.length > 0 && <>；后续还需：{judgement.follow_ups.join("、")}</>}</p>}
  </div>;
}

export function normalizeJudgement(value: unknown): RiskJudgement | null {
  if (!value || typeof value !== "object") return null;
  const item = value as Record<string, unknown>;
  return Array.isArray(item.factors) && Array.isArray(item.rules_applied) && typeof item.risk_level === "string"
    ? value as RiskJudgement : null;
}
