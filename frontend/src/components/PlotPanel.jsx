import { useCallback, useEffect, useRef, useState } from 'react';
import { sampleFunction } from '../engine';
import { fitViewport, worldToScreen, screenToWorld, zoomAt, panBy, niceTicks } from '../lib/viewport';

// 刻度数字格式化：极大/极小用科学计数，其余去尾零
function fmtTick(v) {
  if (v === 0) return '0';
  const a = Math.abs(v);
  if (a >= 1e5 || a < 1e-4) return v.toExponential(1);
  return parseFloat(v.toPrecision(6)).toString();
}

function cssVar(name, fallback) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
}

// 网格 + 坐标轴（画到离屏 canvas）
function drawGrid(ctx, v, w, h) {
  const gridColor = cssVar('--plot-grid', '#334155');
  const axisColor = cssVar('--plot-axis', '#94a3b8');
  const labelColor = cssVar('--plot-label', '#cbd5e1');

  const [wx0, wy0] = screenToWorld(v, 0, 0);
  const [wx1, wy1] = screenToWorld(v, w, h);
  const xLo = Math.min(wx0, wx1), xHi = Math.max(wx0, wx1);
  const yLo = Math.min(wy0, wy1), yHi = Math.max(wy0, wy1);

  const xT = niceTicks(xLo, xHi, 12);
  const yT = niceTicks(yLo, yHi, 10);

  ctx.lineWidth = 1;
  ctx.strokeStyle = gridColor;
  ctx.fillStyle = labelColor;
  ctx.font = '11px ui-monospace, monospace';

  for (const tx of xT.ticks) {
    const sx = worldToScreen(v, tx, 0)[0];
    ctx.beginPath(); ctx.moveTo(sx, 0); ctx.lineTo(sx, h); ctx.stroke();
    ctx.textAlign = 'center';
    ctx.fillText(fmtTick(tx), sx, h - 8);
  }
  for (const ty of yT.ticks) {
    const sy = worldToScreen(v, 0, ty)[1];
    ctx.beginPath(); ctx.moveTo(0, sy); ctx.lineTo(w, sy); ctx.stroke();
    ctx.textAlign = 'left';
    ctx.fillText(fmtTick(ty), 6, sy - 4);
  }

  // 坐标轴（x=0 与 y=0，若在视野内）
  ctx.strokeStyle = axisColor;
  ctx.lineWidth = 1.5;
  const [ax0] = worldToScreen(v, 0, 0);
  const [, ay0] = worldToScreen(v, 0, 0);
  if (yLo <= 0 && 0 <= yHi) { ctx.beginPath(); ctx.moveTo(0, ay0); ctx.lineTo(w, ay0); ctx.stroke(); }
  if (xLo <= 0 && 0 <= xHi) { ctx.beginPath(); ctx.moveTo(ax0, 0); ctx.lineTo(ax0, h); ctx.stroke(); }
  ctx.fillStyle = labelColor;
  ctx.textAlign = 'right';
  ctx.fillText('x', w - 6, ay0 + 16);
  ctx.textAlign = 'left';
  ctx.fillText('y', ax0 + 6, 12);
}

// 曲线：遇 invalid 点抬笔，保证断点两侧不连线
function drawCurve(ctx, v, pts) {
  ctx.strokeStyle = cssVar('--plot-curve', '#38bdf8');
  ctx.lineWidth = 2;
  ctx.lineJoin = 'round';
  ctx.beginPath();
  let pen = false;
  for (const p of pts) {
    if (!p.valid || p.y == null) { pen = false; continue; }
    const [sx, sy] = worldToScreen(v, p.x, p.y);
    if (pen) ctx.lineTo(sx, sy);
    else { ctx.moveTo(sx, sy); pen = true; }
  }
  ctx.stroke();
}

// 二分查找最近采样点
function findNearest(pts, v, sx, sy) {
  const [wx] = screenToWorld(v, sx, sy);
  let lo = 0, hi = pts.length - 1;
  while (lo < hi) { const m = (lo + hi) >> 1; if (pts[m].x < wx) lo = m + 1; else hi = m; }
  let best = null, bestD = Infinity;
  for (let i = Math.max(0, lo - 4); i <= Math.min(pts.length - 1, lo + 4); i++) {
    const p = pts[i];
    if (!p.valid || p.y == null) continue;
    const [px, py] = worldToScreen(v, p.x, p.y);
    const d = (px - sx) ** 2 + (py - sy) ** 2;
    if (d < bestD) { bestD = d; best = p; }
  }
  return bestD <= 20 * 20 ? best : null;
}

export default function PlotPanel({ angle }) {
  const canvasRef = useRef(null);
  const [expr, setExpr] = useState('');
  const [xMin, setXMin] = useState('-10');
  const [xMax, setXMax] = useState('10');
  const [data, setData] = useState(null);
  const [status, setStatus] = useState('idle'); // idle | loading | ready | error
  const [error, setError] = useState(null);
  const [view, setView] = useState(null);
  const [boxMode, setBoxMode] = useState(false);
  const [hover, setHover] = useState(null);
  const [box, setBox] = useState(null);

  const viewRef = useRef(view); viewRef.current = view;
  const dataRef = useRef(data); dataRef.current = data;
  const boxModeRef = useRef(boxMode); boxModeRef.current = boxMode;
  const boxRef = useRef(box); boxRef.current = box;
  const hoverRef = useRef(hover); hoverRef.current = hover;
  const dragRef = useRef(null);
  const rafRef = useRef(0);
  const gridCanvasRef = useRef(null);
  const gridStampRef = useRef('');

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth, h = canvas.clientHeight;
    if (!w || !h) return;
    if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    const v = viewRef.current;
    if (!v) {
      ctx.fillStyle = cssVar('--plot-hint', '#64748b');
      ctx.font = '16px ui-monospace, monospace';
      ctx.textAlign = 'center';
      ctx.fillText('输入如 y = sin(x) * x', w / 2, h / 2);
      return;
    }

    // 网格 + 坐标轴（离屏缓存，仅视图变化时重绘）
    if (!gridCanvasRef.current) gridCanvasRef.current = document.createElement('canvas');
    const gc = gridCanvasRef.current;
    const stamp = [v.cx, v.cy, v.scale, w, h].join('|');
    if (stamp !== gridStampRef.current) {
      gridStampRef.current = stamp;
      gc.width = Math.round(w * dpr); gc.height = Math.round(h * dpr);
      const gctx = gc.getContext('2d');
      gctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      drawGrid(gctx, v, w, h);
    }
    ctx.drawImage(gc, 0, 0, w, h);

    const pts = dataRef.current?.points;
    if (pts && pts.length) drawCurve(ctx, v, pts);

    // 框选矩形
    const b = boxRef.current;
    if (b) {
      ctx.strokeStyle = cssVar('--plot-axis', '#94a3b8');
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.strokeRect(Math.min(b.x0, b.x1), Math.min(b.y0, b.y1), Math.abs(b.x1 - b.x0), Math.abs(b.y1 - b.y0));
      ctx.setLineDash([]);
    }

    // 悬停点 + 坐标
    const hp = hoverRef.current;
    if (hp) {
      const [sx, sy] = worldToScreen(v, hp.x, hp.y);
      ctx.fillStyle = cssVar('--plot-curve', '#38bdf8');
      ctx.beginPath(); ctx.arc(sx, sy, 4, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = cssVar('--plot-label', '#cbd5e1');
      ctx.font = '12px ui-monospace, monospace';
      ctx.textAlign = 'left';
      ctx.fillText(`x=${fmtTick(hp.x)}  y=${fmtTick(hp.y)}`, sx + 8, sy - 8);
    }
  }, []);

  // 视图 / 数据 / 悬停 / 框选变化 → requestAnimationFrame 节流重绘
  useEffect(() => {
    cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(rafRef.current);
  }, [view, data, hover, box, draw]);

  const doPlot = useCallback(async () => {
    const x0 = parseFloat(xMin), x1 = parseFloat(xMax);
    const canvas = canvasRef.current;
    const width = canvas?.clientWidth || 800;
    const height = canvas?.clientHeight || 600;
    if (expr.trim() === '') { setStatus('idle'); setData(null); setView(null); return; }
    if (!Number.isFinite(x0) || !Number.isFinite(x1) || x0 >= x1) {
      setStatus('error'); setError('取值范围非法（需 x_min < x_max）'); setData(null); return;
    }
    setStatus('loading'); setError(null);
    const steps = Math.max(100, Math.round(width / 2));
    const r = await sampleFunction(expr, x0, x1, steps, angle);
    if (r.ok && !r.empty) {
      setData(r);
      setStatus('ready');
      setView(fitViewport(width, height, r.x_range, r.y_range));
    } else if (r.ok && r.empty) {
      setData(null); setStatus('error');
      setError('该表达式在当前范围内无有效定义域');
    } else {
      setData(null); setStatus('error');
      setError(r.error?.message || '绘图失败');
    }
  }, [expr, xMin, xMax, angle]);

  // 交互监听（wheel / 拖拽 / 框选 / 悬停）
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const getPos = (e) => {
      const r = canvas.getBoundingClientRect();
      return [e.clientX - r.left, e.clientY - r.top];
    };

    const onWheel = (e) => {
      e.preventDefault();
      const [sx, sy] = getPos(e);
      const factor = e.deltaY < 0 ? 1.25 : 1 / 1.25;
      setView(v => (v ? zoomAt(v, sx, sy, factor) : v));
    };

    const onDown = (e) => {
      const [sx, sy] = getPos(e);
      if (boxModeRef.current) {
        dragRef.current = { sx, sy, mode: 'box' };
        setBox({ x0: sx, y0: sy, x1: sx, y1: sy });
      } else {
        dragRef.current = { sx, sy, mode: 'pan', startView: viewRef.current };
      }
    };

    const onMove = (e) => {
      const [sx, sy] = getPos(e);
      const d = dragRef.current;
      if (d && d.mode === 'pan' && d.startView) {
        setView(panBy(d.startView, sx - d.sx, sy - d.sy));
      } else if (d && d.mode === 'box') {
        setBox({ x0: d.sx, y0: d.sy, x1: sx, y1: sy });
      } else {
        const pts = dataRef.current?.points;
        const v = viewRef.current;
        if (pts && pts.length && v) {
          const p = findNearest(pts, v, sx, sy);
          setHover(p ? { x: p.x, y: p.y } : null);
        }
      }
    };

    const onUp = (e) => {
      const d = dragRef.current;
      if (d && d.mode === 'box') {
        const [sx, sy] = getPos(e);
        const v = viewRef.current;
        if (v && Math.abs(sx - d.sx) > 8 && Math.abs(sy - d.sy) > 8) {
          const [wx0, wy0] = screenToWorld(v, Math.min(d.sx, sx), Math.min(d.sy, sy));
          const [wx1, wy1] = screenToWorld(v, Math.max(d.sx, sx), Math.max(d.sy, sy));
          const xSpan = (wx1 - wx0) || 1;
          const ySpan = (wy1 - wy0) || 1;
          const w = canvas.clientWidth, h = canvas.clientHeight;
          setView({ ...v, scale: Math.min(w / xSpan, h / ySpan), cx: (wx0 + wx1) / 2, cy: (wy0 + wy1) / 2 });
        }
        setBox(null);
      }
      dragRef.current = null;
    };

    const onLeave = () => setHover(null);

    canvas.addEventListener('wheel', onWheel, { passive: false });
    canvas.addEventListener('mousedown', onDown);
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    canvas.addEventListener('mouseleave', onLeave);
    return () => {
      canvas.removeEventListener('wheel', onWheel);
      canvas.removeEventListener('mousedown', onDown);
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
      canvas.removeEventListener('mouseleave', onLeave);
    };
  }, []);

  // 画布尺寸变化时同步到视图
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ro = new ResizeObserver(() => {
      const w = canvas.clientWidth, h = canvas.clientHeight;
      if (w && h) setView(v => (v ? { ...v, width: w, height: h } : v));
    });
    ro.observe(canvas);
    return () => ro.disconnect();
  }, []);

  const onKeyDown = useCallback((e) => {
    const step = 40;
    if (e.key === 'ArrowLeft') { setView(v => (v ? panBy(v, step, 0) : v)); e.preventDefault(); }
    else if (e.key === 'ArrowRight') { setView(v => (v ? panBy(v, -step, 0) : v)); e.preventDefault(); }
    else if (e.key === 'ArrowUp') { setView(v => (v ? panBy(v, 0, step) : v)); e.preventDefault(); }
    else if (e.key === 'ArrowDown') { setView(v => (v ? panBy(v, 0, -step) : v)); e.preventDefault(); }
  }, []);

  const resetView = useCallback(() => {
    const d = dataRef.current;
    const canvas = canvasRef.current;
    if (d && canvas) {
      setView(fitViewport(canvas.clientWidth, canvas.clientHeight, d.x_range, d.y_range));
    }
  }, []);

  return (
    <div className="plot">
      <div className="plot-controls">
        <input
          className="plot-expr"
          value={expr}
          onChange={(e) => setExpr(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') doPlot(); }}
          placeholder="y = sin(x) * x"
          aria-label="函数表达式"
          spellCheck={false}
          autoComplete="off"
        />
        <button className="plot-btn primary" onClick={doPlot} disabled={status === 'loading'}>
          {status === 'loading' ? '绘制中…' : '绘制'}
        </button>
        <div className="range">
          <label>x ∈</label>
          <input value={xMin} onChange={(e) => setXMin(e.target.value)} aria-label="x 最小值" />
          <span>~</span>
          <input value={xMax} onChange={(e) => setXMax(e.target.value)} aria-label="x 最大值" />
        </div>
      </div>

      <div className="plot-toolbar">
        <button
          className={`plot-btn ${boxMode ? 'active' : ''}`}
          onClick={() => setBoxMode(b => !b)}
          aria-pressed={boxMode}
        >
          ⬚ 框选缩放
        </button>
        <button className="plot-btn" onClick={() => setView(v => (v ? zoomAt(v, v.width / 2, v.height / 2, 1.25) : v))} aria-label="放大">＋</button>
        <button className="plot-btn" onClick={() => setView(v => (v ? zoomAt(v, v.width / 2, v.height / 2, 1 / 1.25) : v))} aria-label="缩小">－</button>
        <button className="plot-btn" onClick={resetView} aria-label="恢复默认视图">⌂ 复位</button>
        <span className="plot-hint">滚轮缩放 · 拖拽平移 · 框选放大 · 方向键平移</span>
      </div>

      <div className="plot-canvas-wrap">
        <canvas ref={canvasRef} className="plot-canvas" tabIndex={0} onKeyDown={onKeyDown} />
        {status === 'loading' && <div className="plot-overlay">绘制中…</div>}
        {status === 'error' && error && <div className="plot-overlay error">{error}</div>}
      </div>
    </div>
  );
}
