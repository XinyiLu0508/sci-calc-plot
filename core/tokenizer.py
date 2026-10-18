# -*- coding: utf-8 -*-
"""词法分析器。

职责：
    1. 把表达式字符串切分为 Token 序列（数字、函数名、常量、变量、运算符、括号）。
    2. 处理「有限隐式乘法」：在明确无歧义的上下文里自动补上乘号（见 _should_insert）。

Token 类型：
    NUM    数字（保留原始字符串，交给解析器转 Decimal，避免精度丢失）
    FUNC   函数名（sin、cos、log、ln、exp、sqrt、abs、factorial …）
    CONST  常量名（pi / π、e）
    VAR    自变量 x
    OP     运算符 + - * / ^ % !
    LPAREN / RPAREN / EOF
"""

import re

from .errors import EngineError, INVALID_TOKEN, UNKNOWN_FUNCTION

# 函数名集合（统一小写）
FUNCTIONS = {
    "sin", "cos", "tan", "asin", "acos", "atan",
    "log", "ln", "exp", "sqrt", "abs", "factorial",
}

# 数字：支持 5、5.、.5、1e5、1.5e-3（贪心匹配）
_NUMBER_RE = re.compile(r"\d+\.?\d*(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?")
# 标识符：字母/下划线开头，可含数字（用于识别 x、sin、log10 等；未知名会报错）
_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


class Token:
    __slots__ = ("type", "value", "pos")

    def __init__(self, type_, value, pos):
        self.type = type_
        self.value = value
        self.pos = pos

    def __repr__(self):  # pragma: no cover - 仅调试用
        return "Token(%s, %r, %d)" % (self.type, self.value, self.pos)


def _should_insert(prev, tok):
    """判断两个相邻 Token 之间是否需要补 '*'（有限隐式乘法）。

    允许的相邻组合（左 → 右）：
        数字   → 函数/常量/变量/左括号    （2x、2(x+1)、3π、2sin(x)）
        右括号 → 函数/常量/变量/左括号/数字（(x+1)(x-1)、(x+1)2）
        变量   → 常量/函数/左括号         （xπ、x sin(x)、x(x+1)）
        常量   → 左括号                  （π(x)）
    不允许：数字→数字、变量→变量、常量→常量/变量（"2 3"、"x x"、"π e" 会报语法错误）。
    """
    if prev.type == "NUM":
        return tok.type in ("FUNC", "CONST", "VAR", "LPAREN")
    if prev.type == "RPAREN":
        return tok.type in ("FUNC", "CONST", "VAR", "LPAREN", "NUM")
    if prev.type == "VAR":
        return tok.type in ("CONST", "FUNC", "LPAREN")
    if prev.type == "CONST":
        return tok.type == "LPAREN"
    return False


def _insert_implicit_mul(tokens):
    """在满足 _should_insert 的相邻 Token 间插入 '*'。"""
    result = []
    for tok in tokens:
        if result and _should_insert(result[-1], tok):
            result.append(Token("OP", "*", tok.pos))
        result.append(tok)
    return result


def tokenize(expr):
    """把表达式字符串切分为 Token 列表（含末尾 EOF）。"""
    tokens = []
    i = 0
    n = len(expr)

    while i < n:
        c = expr[i]

        # 空白
        if c in " \t\r\n":
            i += 1
            continue

        # 数字（或小数点开头）
        if c.isdigit() or c == ".":
            m = _NUMBER_RE.match(expr, i)
            if m is None:
                raise EngineError(INVALID_TOKEN, "无效的小数点", i)
            tokens.append(Token("NUM", m.group(), i))
            i = m.end()
            continue

        # π 常量（单独处理，非 ASCII）
        if c == "π":
            tokens.append(Token("CONST", "pi", i))
            i += 1
            continue

        # 标识符
        if c.isalpha() or c == "_":
            m = _IDENT_RE.match(expr, i)
            name = m.group().lower()
            pos = i
            i = m.end()
            if name in FUNCTIONS:
                tokens.append(Token("FUNC", name, pos))
            elif name == "pi":
                tokens.append(Token("CONST", "pi", pos))
            elif name == "e":
                tokens.append(Token("CONST", "e", pos))
            elif name == "x":
                tokens.append(Token("VAR", "x", pos))
            else:
                raise EngineError(UNKNOWN_FUNCTION, "未知的标识符 '%s'" % m.group(), pos)
            continue

        # 括号与运算符
        if c == "(":
            tokens.append(Token("LPAREN", "(", i))
            i += 1
            continue
        if c == ")":
            tokens.append(Token("RPAREN", ")", i))
            i += 1
            continue
        if c in "+-*/^%!":
            tokens.append(Token("OP", c, i))
            i += 1
            continue

        # 其余字符非法
        raise EngineError(INVALID_TOKEN, "无效字符 '%s'" % c, i)

    tokens = _insert_implicit_mul(tokens)
    tokens.append(Token("EOF", None, n))
    return tokens
