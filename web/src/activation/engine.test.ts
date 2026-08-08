import { describe, expect, it } from "vitest";
import { ActivationEngine } from "./engine";
import { THEME } from "./theme";

const EDGE_BUNDLE = new Map([
  ["e0", "da::db"],
  ["e1", "da"],
]);

function makeEngine() {
  return new ActivationEngine(EDGE_BUNDLE);
}

describe("ActivationEngine", () => {
  it("seed 事件：节点 act 拉高，无束热力", () => {
    const eng = makeEngine();
    eng.handleEvent(
      { type: "graph.hit", ts: 0, payload: { node_ids: ["a"], edge_ids: [], role: "seed" } },
      10
    );
    expect(eng.nodeActOf("a")).toBeGreaterThan(1);
    expect(eng.heatOf("da::db", 10)).toBeNull();
  });

  it("expand 事件：关联束按 stagger 错峰点亮", () => {
    const eng = makeEngine();
    eng.handleEvent(
      { type: "graph.hit", ts: 0, payload: { node_ids: [], edge_ids: ["e0", "e1"], role: "expand" } },
      10
    );
    const h0 = eng.heatOf("da::db", 10)!;
    const h1 = eng.heatOf("da", 10)!;
    expect(h0.color).toEqual(THEME.colors.expand);
    expect(h1.front).toBe(0);
    const later = eng.heatOf("da::db", 11)!;
    expect(later.front).toBeGreaterThan(0.8);
  });

  it("conflict 角色染紫红", () => {
    const eng = makeEngine();
    eng.handleEvent(
      { type: "graph.hit", ts: 0, payload: { node_ids: [], edge_ids: ["e0"], role: "conflict" } },
      0
    );
    expect(eng.heatOf("da::db", 0)!.color).toEqual(THEME.colors.conflict);
  });

  it("热力生命周期：front 推进 → 保持 → 衰减 → 清除", () => {
    const eng = makeEngine();
    eng.handleEvent(
      { type: "graph.hit", ts: 0, payload: { node_ids: [], edge_ids: ["e0"], role: "expand" } },
      0
    );
    expect(eng.heatOf("da::db", 1.0)!.fade).toBe(1);
    expect(eng.heatOf("da::db", 2.6)!.fade).toBeLessThan(1);
    expect(eng.heatOf("da::db", 3.5)).toBeNull();
  });

  it("lens.begin 设置透镜标签并点亮关联束", () => {
    const eng = makeEngine();
    eng.handleEvent(
      { type: "lens.begin", ts: 0, payload: { index: 1, name: "证据强度", node_ids: ["a"], edge_ids: ["e0"] } },
      0
    );
    expect(eng.lensLabel).toBe("透镜一 · 证据强度");
    expect(eng.heatOf("da::db", 0)!.color).toEqual(THEME.colors.lens);
  });

  it("session.idle 清空全部激活态", () => {
    const eng = makeEngine();
    eng.handleEvent(
      { type: "graph.hit", ts: 0, payload: { node_ids: ["a"], edge_ids: ["e0"], role: "seed" } },
      0
    );
    eng.handleEvent({ type: "session.idle", ts: 0, payload: {} }, 1);
    expect(eng.heatOf("da::db", 1)).toBeNull();
    expect(eng.lensLabel).toBeNull();
    expect(eng.skillLabel).toBeNull();
  });

  it("nodeAct 随时间衰减", () => {
    const eng = makeEngine();
    eng.handleEvent(
      { type: "graph.hit", ts: 0, payload: { node_ids: ["a"], edge_ids: [], role: "seed" } },
      0
    );
    const before = eng.nodeActOf("a");
    eng.decay(1.0);
    expect(eng.nodeActOf("a")).toBeLessThan(before);
  });

  it("card.read 轻点亮节点", () => {
    const eng = makeEngine();
    eng.handleEvent({ type: "card.read", ts: 0, payload: { card_id: "a" } }, 0);
    expect(eng.nodeActOf("a")).toBeCloseTo(0.9);
  });
});
