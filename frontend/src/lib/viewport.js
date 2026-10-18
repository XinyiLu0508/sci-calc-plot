// 世界坐标 ↔ 屏幕坐标换算 + 缩放/平移变换 + 1-2-5 刻度。
// 这是「唯一允许出现在前端的数学」——纯坐标换算与渲染，不涉及任何表达式计算。

export function fitViewport(width, height, xRange, yRange) {
  const xSpan = (xRange[1] - xRange[0]) || 1;
  const ySpan = (yRange[1] - yRange[0]) || 1;
  const w = Math.max(width, 1);
  const h = Math.max(height, 1);
  const scale = Math.min(w / xSpan, h / ySpan) * 0.9;
  return {
    width: w,
    height: h,
    scale,
    cx: (xRange[0] + xRange[1]) / 2,
    cy: (yRange[0] + yRange[1]) / 2,
  };
}

export function worldToScreen(v, x, y) {
  return [
    (x - v.cx) * v.scale + v.width / 2,
    v.height / 2 - (y - v.cy) * v.scale,
  ];
}

export function screenToWorld(v, sx, sy) {
  return [
    (sx - v.width / 2) / v.scale + v.cx,
    (v.height / 2 - sy) / v.scale + v.cy,
  ];
}

const MIN_SCALE = 1e-6;
const MAX_SCALE = 1e9;

// 以屏幕点 (sx, sy) 为锚点缩放：保证锚点下的世界坐标不动
export function zoomAt(v, sx, sy, factor) {
  const [wx, wy] = screenToWorld(v, sx, sy);
  const scale = Math.min(MAX_SCALE, Math.max(MIN_SCALE, v.scale * factor));
  return {
    ...v,
    scale,
    cx: wx - (sx - v.width / 2) / scale,
    cy: wy + (sy - v.height / 2) / scale,
  };
}

// 拖拽平移：拖动 (dxPx, dyPx) 像素，内容跟随鼠标
export function panBy(v, dxPx, dyPx) {
  return { ...v, cx: v.cx - dxPx / v.scale, cy: v.cy + dyPx / v.scale };
}

// 1-2-5 序列的「漂亮刻度」：间隔为 1 / 2 / 5 × 10^n
export function niceTicks(lo, hi, targetCount = 10) {
  const span = hi - lo;
  if (!(span > 0)) return { step: 1, ticks: [] };
  const rawStep = span / targetCount;
  const mag = Math.pow(10, Math.floor(Math.log10(rawStep)));
  const norm = rawStep / mag;
  let step;
  if (norm <= 1) step = 1;
  else if (norm <= 2) step = 2;
  else if (norm <= 5) step = 5;
  else step = 10;
  step *= mag;
  const start = Math.ceil(lo / step) * step;
  const ticks = [];
  for (let v = start; v <= hi + step * 1e-9; v += step) {
    ticks.push(v);
  }
  return { step, ticks };
}
