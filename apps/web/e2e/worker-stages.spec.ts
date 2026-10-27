import { expect, test } from "@playwright/test";
import { workerStages } from "../app/worker-stages";
import type { HarnessRun } from "../app/harness-workbench";

function unit(id: string, parents: string[] = []) {
  return { work_unit_id: `w-${id}`, branch_id: `b-${id}`, unit_id: id, depends_on: parents } as HarnessRun["work_units"][number];
}

test("worker stages: five work packages form three independent plus two dependent nodes", () => {
  const stages = workerStages([unit("d", ["a", "b-b"]), unit("a"), unit("b"), unit("c"), unit("e", ["w-c"])]);
  expect(stages.map(stage => stage.level)).toEqual([0, 1]);
  expect(stages.map(stage => stage.units.map(unit => unit.unit_id))).toEqual([["a", "b", "c"], ["d", "e"]]);
});

test("worker stages: six roots are one dependency stage, not a claim of one dispatch wave", () => {
  expect(workerStages(["a", "b", "c", "d", "e", "f"].map(id => unit(id)))).toHaveLength(1);
});

test("worker stages: missing dependencies and cycles are explicitly unknown", () => {
  const stages = workerStages([unit("a", ["b"]), unit("b", ["a"]), unit("c", ["missing"]), unit("d")]);
  expect(stages.map(stage => stage.level)).toEqual([0, null]);
  expect(stages[1].units).toHaveLength(3);
});

test("worker stages: dependency chains and empty inputs do not invent workers", () => {
  expect(workerStages([])).toEqual([]);
  expect(workerStages([unit("c", ["b"]), unit("b", ["a"]), unit("a")]).map(stage => stage.level)).toEqual([0, 1, 2]);
});
