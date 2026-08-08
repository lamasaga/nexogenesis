export class Camera {
  /** 缩放范围限制（用户决议 2026-08-08，收窄自 [0.2, 4]）：防止缩得过小失真或放得过大失焦 */
  static MIN_SCALE = 0.3;
  static MAX_SCALE = 3;

  constructor(
    public x = 0,
    public y = 0,
    public scale = 1
  ) {}

  toScreen(wx: number, wy: number, w: number, h: number): [number, number] {
    return [w / 2 + (wx - this.x) * this.scale, h / 2 + (wy - this.y) * this.scale];
  }

  toWorld(sx: number, sy: number, w: number, h: number): [number, number] {
    return [this.x + (sx - w / 2) / this.scale, this.y + (sy - h / 2) / this.scale];
  }

  /** 以屏幕点 (sx,sy) 为锚缩放 */
  zoomAt(sx: number, sy: number, w: number, h: number, factor: number): void {
    const [wx, wy] = this.toWorld(sx, sy, w, h);
    this.scale = Math.min(Camera.MAX_SCALE, Math.max(Camera.MIN_SCALE, this.scale * factor));
    this.x = wx - (sx - w / 2) / this.scale;
    this.y = wy - (sy - h / 2) / this.scale;
  }

  /** 屏幕像素增量 → 世界平移 */
  panBy(dxPx: number, dyPx: number): void {
    this.x -= dxPx / this.scale;
    this.y -= dyPx / this.scale;
  }
}
