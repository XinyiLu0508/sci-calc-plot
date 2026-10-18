# -*- coding: utf-8 -*-
"""函数采样器测试（点数/区间、断点不连线、自适应加密、空定义域）。"""
from core import engine


def test_basic_sampling_range():
    r = engine.sample_function("x*sin(x)", -10, 10, 600)
    assert r["ok"]
    pts = r["points"]
    assert len(pts) > 0
    xs = [p["x"] for p in pts]
    assert abs(xs[0] - (-10)) < 1e-9
    assert abs(xs[-1] - 10) < 1e-9
    assert all(-10 - 1e-9 <= x <= 10 + 1e-9 for x in xs)
    assert all(xs[i] <= xs[i + 1] + 1e-12 for i in range(len(xs) - 1))


def test_plot_prefix():
    a = engine.sample_function("y=sin(x)", -1, 1, 50)
    b = engine.sample_function("f(x)=sin(x)", -1, 1, 50)
    c = engine.sample_function("sin(x)", -1, 1, 50)
    assert a["ok"] and b["ok"] and c["ok"]
    assert len(a["points"]) == len(c["points"])
    assert len(b["points"]) == len(c["points"])


def test_one_over_x_no_vertical_line():
    r = engine.sample_function("1/x", -5, 5, 400)
    assert r["ok"]
    pts = r["points"]
    # 相邻两个有效点不允许「符号翻转且幅度巨大」→ 说明极点处已断线
    for i in range(len(pts) - 1):
        p, q = pts[i], pts[i + 1]
        if p["valid"] and q["valid"] and p["y"] is not None and q["y"] is not None:
            sign_flip = p["y"] * q["y"] < 0
            huge = abs(p["y"]) > 100 and abs(q["y"]) > 100
            assert not (sign_flip and huge), "y=1/x 在 x=0 附近不应连线"


def test_tan_no_vertical_line():
    r = engine.sample_function("tan(x)", -6.28, 6.28, 800)
    assert r["ok"]
    pts = r["points"]
    for i in range(len(pts) - 1):
        p, q = pts[i], pts[i + 1]
        if p["valid"] and q["valid"] and p["y"] is not None and q["y"] is not None:
            sign_flip = p["y"] * q["y"] < 0
            huge = abs(p["y"]) > 1000 and abs(q["y"]) > 1000
            assert not (sign_flip and huge), "y=tan(x) 在渐近线处不应连线"


def test_steep_adaptive_refine():
    r = engine.sample_function("x^3", -10, 10, 400)
    assert r["ok"]
    pts = r["points"]
    # 自适应加密应使点数多于基础采样数
    assert len(pts) > 401
    # 陡峭段（|x|>8）的最大 x 间隔应小于基础步长 20/400=0.05
    base_dx = 20.0 / 400
    steep_gaps = []
    for i in range(len(pts) - 1):
        p, q = pts[i], pts[i + 1]
        if p["valid"] and q["valid"] and abs(p["x"]) > 8:
            steep_gaps.append(abs(q["x"] - p["x"]))
    assert max(steep_gaps) < base_dx


def test_empty_domain():
    r = engine.sample_function("sqrt(-x^2-1)", -10, 10, 100)
    assert r["ok"] and r.get("empty") is True


def test_invalid_range():
    r = engine.sample_function("sin(x)", 10, -10, 100)
    assert not r["ok"] and r["error"]["code"] == "INVALID_RANGE"


def test_invalid_expr():
    r = engine.sample_function("sin(x", -10, 10, 100)
    assert not r["ok"]
