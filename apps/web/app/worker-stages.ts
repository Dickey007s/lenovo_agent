import type { HarnessRun } from "./harness-workbench";

type WorkUnit = HarnessRun["work_units"][number];

// Dependency depth describes planned ordering, not actual dispatch wave/time.
export function workerStages(units: WorkUnit[]) {
  const byId = new Map(units.flatMap(unit => [unit.work_unit_id, unit.unit_id, unit.branch_id].map(id => [id, unit] as const)));
  const depths = new Map<string, number | null>();
  function depth(unit: WorkUnit, path = new Set<string>()): number | null {
    if (depths.has(unit.work_unit_id)) return depths.get(unit.work_unit_id)!;
    if (path.has(unit.work_unit_id)) return null;
    const visiting = new Set(path).add(unit.work_unit_id);
    const parents = unit.depends_on.map(id => byId.get(id));
    const values = parents.map(parent => parent ? depth(parent, visiting) : null);
    const value = values.some(item => item === null) ? null : values.length ? Math.max(...values as number[]) + 1 : 0;
    depths.set(unit.work_unit_id, value);
    return value;
  }
  const stages = new Map<number | null, WorkUnit[]>();
  for (const unit of units) {
    const level = depth(unit);
    stages.set(level, [...(stages.get(level) ?? []), unit]);
  }
  return [...stages].sort(([a], [b]) => (a ?? Infinity) - (b ?? Infinity)).map(([level, items]) => ({ level, units: items }));
}
