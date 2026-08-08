import { describe, expect, it } from "vitest";
import { Camera } from "./camera";

describe("Camera", () => {
  it("世界/屏幕坐标互转可逆", () => {
    const cam = new Camera(10, 20, 1.5);
    const [sx, sy] = cam.toScreen(100, 50, 800, 600);
    const [wx, wy] = cam.toWorld(sx, sy, 800, 600);
    expect(wx).toBeCloseTo(100, 6);
    expect(wy).toBeCloseTo(50, 6);
  });

  it("zoomAt 后光标下的世界点保持不动", () => {
    const cam = new Camera(0, 0, 1);
    const [wx, wy] = cam.toWorld(600, 300, 800, 600);
    cam.zoomAt(600, 300, 800, 600, 1.2);
    const [sx2, sy2] = cam.toScreen(wx, wy, 800, 600);
    expect(sx2).toBeCloseTo(600, 4);
    expect(sy2).toBeCloseTo(300, 4);
  });

  it("缩放范围受限 [0.2, 4]", () => {
    const cam = new Camera(0, 0, 1);
    for (let i = 0; i < 50; i++) cam.zoomAt(400, 300, 800, 600, 1.5);
    expect(cam.scale).toBeLessThanOrEqual(4);
    for (let i = 0; i < 100; i++) cam.zoomAt(400, 300, 800, 600, 0.5);
    expect(cam.scale).toBeGreaterThanOrEqual(0.2);
  });

  it("panBy 平移", () => {
    const cam = new Camera(0, 0, 2);
    cam.panBy(10, -20);
    expect(cam.x).toBeCloseTo(-5);
    expect(cam.y).toBeCloseTo(10);
  });
});
