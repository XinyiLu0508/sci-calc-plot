# -*- coding: utf-8 -*-
"""核心引擎对外统一入口（唯一计算来源）。

前端 / FastAPI / Pyodide 都只调用这里，不直接触碰内部模块：
    evaluate(expr, angle="rad")                           —— 计算器求值
    validate(expr)                                        —— 表达式合法性校验（仅词法+语法，不计算）
    sample_function(expr, x_min, x_max, steps, angle)     —— 函数采样（绘图）

所有返回值都是可 JSON 序列化的 dict，便于 HTTP / WASM 双通道直接透传。
"""

import math
from decimal import Decimal

from .errors import EngineError
from .parser import parse
from .evaluator import evaluate_ast, cleanup, format_display, _FLOAT_MAX
from .sampler import sample_function  # noqa: F401  （重导出，供统一入口使用）

__all__ = ["evaluate", "validate", "sample_function"]


def _json_float(d):
    """Decimal → JSON 安全的 number（超出 float 范围时返回 None，由 display 兜底）。"""
    if d is None or not d.is_finite():
        return None
    if abs(d) > _FLOAT_MAX:
        return None
    return float(d)


def evaluate(expr, angle="rad"):
    """科学计算器求值。成功返回 {ok, value, display}，失败返回 {ok:False, error}。"""
    try:
        ast = parse(expr)
        result = evaluate_ast(ast, x_value=None, allow_var=False, angle=angle)
        result = cleanup(result)
        return {
            "ok": True,
            "value": _json_float(result),
            "display": format_display(result),
        }
    except EngineError as e:
        return {"ok": False, "error": e.to_dict()}
    except Exception as e:  # 防御：任何意外都不应把异常抛到前端
        return {"ok": False, "error": {"code": "INTERNAL", "message": "内部错误：%s" % e, "position": -1}}


def validate(expr):
    """仅做词法 + 语法校验，返回 {ok} 或 {ok:False, error}；用于前端输入实时标红。"""
    try:
        parse(expr)
        return {"ok": True}
    except EngineError as e:
        return {"ok": False, "error": e.to_dict()}
    except Exception as e:
        return {"ok": False, "error": {"code": "INTERNAL", "message": str(e), "position": -1}}
