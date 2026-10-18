import { describe, it, expect } from 'vitest';
import { fitViewport, worldToScreen, screenToWorld, zoomAt, panBy, niceTicks } from './viewport.js';

describe('viewport 坐标换算', () => {
  it('fit 后世界原点位于屏幕中心', () => {
    const v = fitViewport(800, 600, [-10, 10], [-5, 5]);
    const [sx, sy] = worldToScreen(v, 0, 0);
    expect(sx).toBeCloseTo(400, 1);
    expect(sy).toBeCloseTo(300, 1);
  });

  it('world ↔ screen 往返一致', () => {
    const v = fitViewport(800, 600, [-10, 10], [-5, 5]);
    const [sx, sy] = worldToScreen(v, 3.7, -2.2);
    const [wx, wy] = screenToWorld(v, sx, sy);
    expect(wx).toBeCloseTo(3.7, 6);
    expect(wy).toBeCloseTo(-2.2, 6);
  });

  it('缩放锚点不动（锚点下的世界坐标不变）', () => {
    const v = fitViewport(800, 600, [-10, 10], [-5, 5]);
    const sx = 200, sy = 150;
    const [wxBefore, wyBefore] = screenToWorld(v, sx, sy);
    const v2 = zoomAt(v, sx, sy, 1.25);
    const [wxAfter, wyAfter] = screenToWorld(v2, sx, sy);
    expect(wxAfter).toBeCloseTo(wxBefore, 6);
    expect(wyAfter).toBeCloseTo(wyBefore, 6);
  });

  it('平移：拖动像素后世界原点按像素位移', () => {
    const v = fitViewport(800, 600, [-10, 10], [-5, 5]);
    const v2 = panBy(v, 100, 50);
    const [sx1, sy1] = worldToScreen(v, 0, 0);
    const [sx2, sy2] = worldToScreen(v2, 0, 0);
    expect(sx2 - sx1).toBeCloseTo(100, 1);
    expect(sy2 - sy1).toBeCloseTo(50, 1);
  });

  it('1-2-5 序列刻度间隔', () => {
    const { step, ticks } = niceTicks(0, 10, 10);
    const mantissa = step / Math.pow(10, Math.floor(Math.log10(step)));
    expect([1, 2, 5, 10]).toContain(mantissa);
    expect(ticks.length).toBeGreaterThan(5);
  });
});
