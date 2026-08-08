import type { SimEvent } from "../graph/types";
import type { Color } from "../graph/types-extra";
import { LENS_ORDINALS, THEME } from "./theme";

export interface Heat {
  front: number;
  fade: number;
  color: Color;
}

interface BundleState {
  igniteAt: number;
  color: Color;
}

export class ActivationEngine {
  skillLabel: string | null = null;
  lensLabel: string | null = null;
  private bundles = new Map<string, BundleState>();
  private nodeAct = new Map<string, number>();

  /** @param edgeBundle 边 id → 束 id */
  constructor(private edgeBundle: Map<string, string>) {}

  handleEvent(ev: SimEvent, now: number): void {
    const p = ev.payload as Record<string, never>;
    switch (ev.type) {
      case "skill.trigger":
        this.skillLabel = String(p["skill"] ?? "");
        this.lensLabel = null;
        break;
      case "graph.hit":
        this.onGraphHit(p as unknown as {
          node_ids: string[]; edge_ids: string[]; role: string;
        }, now);
        break;
      case "lens.begin": {
        const lp = p as unknown as { index: number; name: string; node_ids: string[]; edge_ids: string[] };
        const ordinal = LENS_ORDINALS[lp.index - 1] ?? String(lp.index);
        this.lensLabel = `透镜${ordinal} · ${lp.name}`;
        lp.node_ids.forEach((id) => this.bumpNode(id, THEME.node.readAct));
        this.ignite(lp.edge_ids, now, THEME.colors.lens);
        break;
      }
      case "card.read": {
        const cid = String(p["card_id"] ?? "");
        if (cid) this.bumpNode(cid, THEME.node.readAct);
        break;
      }
      case "write.applied": {
        const wp = p as unknown as { created: string[]; enriched: string[] };
        [...wp.created, ...wp.enriched].forEach((id) =>
          this.bumpNode(id, THEME.node.seedAct)
        );
        break;
      }
      case "session.idle":
        this.bundles.clear();
        this.lensLabel = null;
        this.skillLabel = null;
        break;
    }
  }

  private onGraphHit(
    p: { node_ids: string[]; edge_ids: string[]; role: string },
    now: number
  ): void {
    if (p.role === "seed") {
      p.node_ids.forEach((id) => this.bumpNode(id, THEME.node.seedAct));
      return;
    }
    const color = p.role === "conflict" ? THEME.colors.conflict : THEME.colors.expand;
    this.ignite(p.edge_ids, now, color);
    p.node_ids.forEach((id) => this.bumpNode(id, THEME.node.readAct));
  }

  private ignite(edgeIds: string[], now: number, color: Color): void {
    const seen = new Set<string>();
    let i = 0;
    for (const eid of edgeIds) {
      const bid = this.edgeBundle.get(eid);
      if (!bid || seen.has(bid)) continue;
      seen.add(bid);
      // 再激活：重置 front（神经再激活隐喻）
      this.bundles.set(bid, { igniteAt: now + i * THEME.timing.stagger, color });
      i++;
    }
  }

  private bumpNode(id: string, act: number): void {
    this.nodeAct.set(id, Math.max(this.nodeAct.get(id) ?? 0, act));
  }

  /** 渲染器回写：纤维 front 到达端点时点亮突触 */
  pokeFromRenderer(id: string, act: number): void {
    this.bumpNode(id, act);
  }

  /** 束当前热力；超出寿命自动清除并返回 null */
  heatOf(bundleId: string, now: number): Heat | null {
    const st = this.bundles.get(bundleId);
    if (!st) return null;
    const age = now - st.igniteAt;
    if (age < 0) return { front: 0, fade: 1, color: st.color };
    const t = THEME.timing;
    if (age > t.ttl) {
      this.bundles.delete(bundleId);
      return null;
    }
    const front = Math.min(1.3, (age / t.frontDuration) * 1.3);
    const fade = age < t.holdUntil ? 1 : Math.max(0, 1 - (age - t.holdUntil) / t.fadeDuration);
    return { front, fade, color: st.color };
  }

  nodeActOf(id: string): number {
    return this.nodeAct.get(id) ?? 0;
  }

  /** 每帧调用：dt 秒，节点 act 指数衰减 */
  decay(dt: number): void {
    const k = Math.pow(THEME.node.decayPerFrame, dt * 60);
    for (const [id, act] of this.nodeAct) {
      const next = act * k;
      if (next < 0.02) this.nodeAct.delete(id);
      else this.nodeAct.set(id, next);
    }
  }

  /** 仍有活跃束（用于跳帧优化判断） */
  hasActiveBundles(): boolean {
    return this.bundles.size > 0;
  }
}
