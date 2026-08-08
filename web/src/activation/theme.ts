import type { Color } from "../graph/types-extra";

export const THEME = {
  colors: {
    rest: [86, 222, 208] as Color,
    seed: [255, 205, 135] as Color,
    expand: [125, 211, 252] as Color,
    conflict: [226, 120, 245] as Color,
    lens: [255, 190, 100] as Color,
    background: "#080d16",
  },
  timing: {
    /** front 从 0 推进到 1.3 的秒数 */
    frontDuration: 1.1,
    /** 保持期结束时刻（秒） */
    holdUntil: 2.2,
    /** 衰减期秒数 */
    fadeDuration: 0.8,
    /** 同事件多束点亮的错峰秒数 */
    stagger: 0.35,
    /** 总寿命（超过即清除） */
    ttl: 3.0,
  },
  fibers: {
    baseAlphaIntra: 0.1,
    baseAlphaInter: 0.2,
    litAlpha: 0.95,
    spread: 14,
  },
  node: {
    seedAct: 1.2,
    readAct: 0.9,
    /** 每 60fps 帧的 act 衰减系数 */
    decayPerFrame: 0.99,
    /** act 超过此值才显示标题 */
    labelThreshold: 0.45,
  },
};

export const LENS_ORDINALS = ["一", "二", "三", "四", "五", "六"];
