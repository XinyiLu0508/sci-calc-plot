# -*- coding: utf-8 -*-
"""函数采样器（绘图核心）。

算法思路（四步流水线）：
    1. 基础采样：dx = (x_max - x_min) / base_n，base_n ≈ canvasWidth/2，
       保证水平方向每像素至少 1 个采样点。
    2. 自适应加密：相邻两点若「垂直跨度过大（陡峭）」或「弦中点与线性插值偏差过大（弯曲）」，
       则二分加密，最多递归 3 层，让 y=x^3 这类陡峭曲线也平滑。
    3. 断点处理：每个采样点记录有效性；求值时的定义域错误（除零/负开方/对数越域/负幂）
       会被标记为 invalid。此外，若相邻两个有效点「符号翻转且幅度远超可视范围」，
       说明中间有极点（如 1/x 的 x=0、tan(x) 的 π/2+kπ），在中间插入 invalid 点强制断线，
       保证 y=1/x、y=tan(x) 不会画成竖线。
    4. LOD：单条曲线采样点上限 20000，超出时均匀抽稀，但保留所有 invalid 断点。
"""

import math
import re
from decimal import Decimal

from .errors import EngineError, INVALID_RANGE
from .parser import parse
from .evaluator import evaluate_ast

MAX_POINTS = 20000
MAX_BASE_STEPS = 5000
MAX_REFINE_DEPTH = 3


def _strip_plot_prefix(s):
    """允许 y=、f(x)= 等前缀，剥掉后返回真正的函数体。"""
    s = (s or "").strip()
    m = re.match(r"^(?:y|f\s*\(\s*x\s*\))\s*=\s*(.+)$", s, re.IGNORECASE)
    return m.group(1).strip() if m else s


def _eval_point(ast, x, angle):
    """在 x 处求值，返回 (y, valid)。任何定义域错误 → (None, False)。"""
    try:
        y = evaluate_ast(ast, x_value=Decimal(repr(x)), allow_var=True, angle=angle)
        if y is None or not y.is_finite():
            return None, False
        f = float(y)
        if not math.isfinite(f):
            return None, False
        return f, True
    except EngineError:
        return None, False
    except Exception:
        return None, False


def _base_sample(ast, x_min, x_max, base_n, angle):
    dx = (x_max - x_min) / base_n
    pts = []
    for i in range(base_n + 1):
        x = x_min + i * dx
        y, valid = _eval_point(ast, x, angle)
        pts.append((x, y, valid))
    return pts


def _refine(ast, pts, steep_thresh, y_span, depth, max_depth, angle):
    """全局自适应加密：每一层扫描所有相邻点对，合格的切一刀，再进入下一层。"""
    if depth >= max_depth:
        return pts
    tol = y_span * 0.01  # 弦偏差阈值（1% 可视范围）
    out = []
    for i in range(len(pts) - 1):
        x1, y1, v1 = pts[i]
        x2, y2, v2 = pts[i + 1]
        out.append((x1, y1, v1))
        if v1 and v2:
            xm = (x1 + x2) / 2.0
            ym, vm = _eval_point(ast, xm, angle)
            if vm:
                lin = (y1 + y2) / 2.0
                if abs(y2 - y1) > steep_thresh or abs(ym - lin) > tol:
                    out.append((xm, ym, vm))
    out.append(pts[-1])
    return _refine(ast, out, steep_thresh, y_span, depth + 1, max_depth, angle)


def _insert_breaks(pts, y_span):
    """符号翻转 + 幅度远超可视范围 → 极点，插入 invalid 断点强制断线。"""
    thr = max(10.0 * y_span, 1e-6)
    out = []
    for i in range(len(pts) - 1):
        x1, y1, v1 = pts[i]
        x2, y2, v2 = pts[i + 1]
        out.append((x1, y1, v1))
        if v1 and v2 and y1 * y2 < 0 and abs(y1) > thr and abs(y2) > thr:
            out.append(((x1 + x2) / 2.0, None, False))
    out.append(pts[-1])
    return out


def _lod(pts, limit):
    """点数上限保护：超过 limit 时均匀抽稀，但保留 invalid 断点。"""
    if len(pts) <= limit:
        return pts
    k = max(1, math.ceil(len(pts) / limit))
    out = []
    count = 0
    for p in pts:
        if (not p[2]) or (count % k == 0):
            out.append(p)
        count += 1
    if len(out) > limit:
        out = out[:limit]
    return out


def sample_function(expr, x_min, x_max, steps, angle="rad"):
    """对表达式在 [x_min, x_max] 上采样，返回可 JSON 化的点集与可视范围。"""
    try:
        x_min = float(x_min)
        x_max = float(x_max)
    except (TypeError, ValueError):
        return {"ok": False,
                "error": {"code": INVALID_RANGE, "message": "取值范围必须是数字", "position": -1}}
    if (not math.isfinite(x_min)) or (not math.isfinite(x_max)) or x_min >= x_max:
        return {"ok": False,
                "error": {"code": INVALID_RANGE, "message": "取值范围非法（需 x_min < x_max）", "position": -1}}

    body = _strip_plot_prefix(expr)
    try:
        ast = parse(body)
    except EngineError as e:
        return {"ok": False, "error": e.to_dict()}

    try:
        base_n = int(steps)
    except (TypeError, ValueError):
        base_n = 1000
    base_n = max(2, min(base_n, MAX_BASE_STEPS))

    pts = _base_sample(ast, x_min, x_max, base_n, angle)

    ys = sorted([y for (_, y, v) in pts if v and y is not None and math.isfinite(y)])
    if not ys:
        return {"ok": True, "points": [], "x_range": [x_min, x_max],
                "y_range": [0.0, 0.0], "empty": True}

    # 鲁棒可视范围：1%..99% 分位，避免极点把坐标轴拉爆
    y_lo = ys[int(len(ys) * 0.01)]
    y_hi = ys[int(len(ys) * 0.99)]
    if y_hi - y_lo < 1e-12:
        pad = 1.0 if y_hi == 0 else abs(y_hi) * 0.5 + 1.0
        y_lo -= pad
        y_hi += pad
    y_span = y_hi - y_lo

    pts = _refine(ast, pts, y_span / base_n, y_span, 0, MAX_REFINE_DEPTH, angle)
    pts = _insert_breaks(pts, y_span)
    pts = _lod(pts, MAX_POINTS)

    return {
        "ok": True,
        "points": [{"x": x, "y": y, "valid": valid} for (x, y, valid) in pts],
        "x_range": [x_min, x_max],
        "y_range": [float(y_lo), float(y_hi)],
    }
