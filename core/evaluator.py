# -*- coding: utf-8 -*-
"""安全求值器。

设计要点：
    1. 基本算术使用 decimal.Decimal 高精度，0.1 + 0.2 精确等于 0.3。
    2. 超越函数（sin/cos/tan/log/exp 等）用 math（双精度）计算后转回 Decimal，
       这是「纯标准库、可同时跑在 CPython 与 Pyodide 下」的折中方案。
    3. 定义域错误（除零、负数开方、对数越域、负底数分数次幂、阶乘非整数等）
       统一抛 EngineError，前端据此展示中文提示。
    4. 求值结果先经 cleanup 做「1e-12 阈值整数吸附」，再经 format_display 生成展示字符串。
"""

import math
import re
from decimal import Decimal, getcontext, ROUND_HALF_EVEN

from .errors import (
    EngineError, DIVISION_BY_ZERO, MODULO_BY_ZERO, NEGATIVE_SQRT, LOG_DOMAIN,
    ASIN_ACOS_DOMAIN, INVALID_FACTORIAL, NEGATIVE_POWER, ZERO_POWER_NEGATIVE,
    OVERFLOW, UNKNOWN_VARIABLE, UNEXPECTED_TOKEN, UNKNOWN_FUNCTION,
)
from . import parser as _parser

getcontext().prec = 50

# 高精度常量（更多位数，避免多次运算累积误差）
PI = Decimal("3.1415926535897932384626433832795028841971693993751")
E = Decimal("2.7182818284590452353602874713526624977572470937")

_FACTORIAL_LIMIT = 1000
_FLOAT_MAX = Decimal("1e308")   # 超过 float 上限即视为溢出


def _from_float(f, pos=-1):
    """把 float 安全转回 Decimal；非有限值（inf/nan）视为溢出。"""
    if not math.isfinite(f):
        raise EngineError(OVERFLOW, "数值溢出（结果超出可表示范围）", pos)
    return Decimal(repr(f))


def _check_finite(d, pos=-1):
    if not d.is_finite():
        raise EngineError(OVERFLOW, "数值溢出", pos)
    return d


def _factorial(x, pos):
    """阶乘：仅对非负整数有定义。"""
    if x < 0 or x != int(x):
        raise EngineError(INVALID_FACTORIAL, "阶乘仅对非负整数有定义", pos)
    n = int(x)
    if n > _FACTORIAL_LIMIT:
        raise EngineError(INVALID_FACTORIAL, "阶乘参数过大（上限 %d）" % _FACTORIAL_LIMIT, pos)
    return Decimal(str(math.factorial(n)))


def _power(a, b, pos):
    """幂运算，含定义域检查。约定 0^0 = 1。"""
    if b == 0:
        return Decimal(1)
    if a == 0:
        if b < 0:
            raise EngineError(ZERO_POWER_NEGATIVE, "0 的负次幂无定义", pos)
        return Decimal(0)
    if a < 0 and b != int(b):
        raise EngineError(NEGATIVE_POWER, "负数的非整数次幂无定义", pos)
    if b == int(b):
        bi = int(b)
        if abs(bi) > 100000:
            raise EngineError(OVERFLOW, "指数过大", pos)
        return _check_finite(a ** bi, pos)
    # 非整数次幂（如 9^0.5、x^(1/3)）走浮点
    try:
        return _from_float(math.pow(float(a), float(b)), pos)
    except EngineError:
        raise
    except (OverflowError, ValueError):
        raise EngineError(OVERFLOW, "幂运算溢出", pos)


def _trig(fn, x, angle, pos):
    """正三角函数：angle == 'deg' 时先把输入转弧度。"""
    v = float(x)
    if angle == "deg":
        v = math.radians(v)
    try:
        return _from_float(fn(v), pos)
    except ValueError:
        raise EngineError(OVERFLOW, "数值溢出", pos)


def _trig_inv(fn, x, angle, pos, lo, hi):
    """反三角函数：asin/acos 需检查定义域；deg 模式下输出转角度。"""
    v = float(x)
    if (lo is not None and v < lo) or (hi is not None and v > hi):
        raise EngineError(ASIN_ACOS_DOMAIN, "反三角函数定义域错误（需 |x| ≤ 1）", pos)
    try:
        r = fn(v)  # 结果为弧度
    except ValueError:
        raise EngineError(ASIN_ACOS_DOMAIN, "反三角函数定义域错误", pos)
    if angle == "deg":
        r = math.degrees(r)
    return _from_float(r, pos)


def _call(name, x, pos, angle):
    try:
        if name == "sin":
            return _trig(math.sin, x, angle, pos)
        if name == "cos":
            return _trig(math.cos, x, angle, pos)
        if name == "tan":
            return _trig(math.tan, x, angle, pos)
        if name == "asin":
            return _trig_inv(math.asin, x, angle, pos, -1.0, 1.0)
        if name == "acos":
            return _trig_inv(math.acos, x, angle, pos, -1.0, 1.0)
        if name == "atan":
            return _trig_inv(math.atan, x, angle, pos, None, None)
        if name == "sqrt":
            if x < 0:
                raise EngineError(NEGATIVE_SQRT, "负数不能开平方", pos)
            return x.sqrt()
        if name == "log":
            if x <= 0:
                raise EngineError(LOG_DOMAIN, "log 的定义域为 (0, +∞)", pos)
            return _from_float(math.log10(float(x)), pos)
        if name == "ln":
            if x <= 0:
                raise EngineError(LOG_DOMAIN, "ln 的定义域为 (0, +∞)", pos)
            return _from_float(math.log(float(x)), pos)
        if name == "exp":
            return _from_float(math.exp(float(x)), pos)
        if name == "abs":
            return abs(x)
        if name == "factorial":
            return _factorial(x, pos)
    except EngineError:
        raise
    except (OverflowError, ValueError):
        raise EngineError(OVERFLOW, "数值溢出", pos)
    raise EngineError(UNKNOWN_FUNCTION, "未知函数 '%s'" % name, pos)


def _binary(op, a, b, pos):
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    if op == "/":
        if b == 0:
            raise EngineError(DIVISION_BY_ZERO, "除数为零", pos)
        return a / b
    if op == "%":
        if b == 0:
            raise EngineError(MODULO_BY_ZERO, "取模除数为零", pos)
        return a % b
    if op == "^":
        return _power(a, b, pos)
    raise EngineError(UNEXPECTED_TOKEN, "未知运算符 '%s'" % op, pos)


def evaluate_node(node, x_value=None, allow_var=False, angle="rad"):
    """递归求值 AST。x_value 用于绘图采样时给自变量 x 代入值。"""
    if isinstance(node, _parser.Number):
        return Decimal(node.value)
    if isinstance(node, _parser.Constant):
        return PI if node.name == "pi" else E
    if isinstance(node, _parser.Variable):
        if x_value is None or not allow_var:
            raise EngineError(UNKNOWN_VARIABLE, "变量 x 在此处不可用", node.pos)
        return x_value
    if isinstance(node, _parser.UnaryOp):
        v = evaluate_node(node.operand, x_value, allow_var, angle)
        return v if node.op == "+" else -v
    if isinstance(node, _parser.BinaryOp):
        left = evaluate_node(node.left, x_value, allow_var, angle)
        right = evaluate_node(node.right, x_value, allow_var, angle)
        return _binary(node.op, left, right, node.pos)
    if isinstance(node, _parser.FunctionCall):
        arg = evaluate_node(node.arg, x_value, allow_var, angle)
        return _call(node.name, arg, node.pos, angle)
    if isinstance(node, _parser.Factorial):
        v = evaluate_node(node.operand, x_value, allow_var, angle)
        return _factorial(v, node.pos)
    raise EngineError(UNEXPECTED_TOKEN, "未知的 AST 节点", node.pos)


def evaluate_ast(ast, x_value=None, allow_var=False, angle="rad"):
    """对外求值入口。"""
    return evaluate_node(ast, x_value, allow_var, angle)


def cleanup(d):
    """结果净化：把落在整数 1e-12（相对）邻域内的浮点噪声吸附为整数。

    例：1.0000000000000002 → 1；sin(π) ≈ 1.22e-16 → 0。
    精确的 Decimal 运算结果（如 0.1+0.2=0.3、大整数）不受影响。
    """
    if d == 0:
        return Decimal(0)
    nearest = d.to_integral_value(rounding=ROUND_HALF_EVEN)
    if abs(d - nearest) <= Decimal("1e-12") * max(Decimal(1), abs(d)):
        d = nearest
    return d


def _strip_sci(s):
    """科学计数法字符串去掉尾零：'1.5000000000E-15' -> '1.5E-15'。"""
    m, _, e = s.partition("E")
    m = m.rstrip("0").rstrip(".")
    return (m or "0") + "E" + e


def format_display(d):
    """把净化后的 Decimal 结果格式化为适合展示的字符串。"""
    if d == 0:
        return "0"
    # 整数：精确显示（极大值转科学计数）
    if d == d.to_integral_value(rounding=ROUND_HALF_EVEN):
        iv = d.to_integral_value()
        if abs(iv) < Decimal("1e16"):
            return str(int(iv))
        return _strip_sci(format(iv, ".10E"))
    # 非整数：用 float 的 'g' 格式（12 位有效数字，自动去尾零）
    if abs(d) > _FLOAT_MAX:
        return _strip_sci(format(d, ".10E"))
    return format(float(d), ".12g")
