# -*- coding: utf-8 -*-
"""语法分析器（Pratt 递归下降 / 优先级爬升）。

生成 AST，节点类型（均携带 pos 用于错误定位）：
    Number(value_str, pos)
    Constant(name, pos)          # pi / e
    Variable(name, pos)          # x
    UnaryOp(op, operand, pos)    # - / +
    BinaryOp(op, left, right, pos)
    FunctionCall(name, arg, pos)
    Factorial(operand, pos)

优先级（数值越大绑定越紧）：
    二元 + -     10
    二元 * / %   20
    二元 ^       40（右结合，2^3^2 = 2^(3^2)）
    一元 + -     操作数以最小绑定力 40 解析（比 ^ 松，比 * / 紧）
    后缀 !       50

一元负号说明：按数学惯例 -2^2 = -(2^2)，故一元操作数用 min_bp=40 解析，
    这样 ^(40) 会被吞入，而 * /(20) 不会被吞入。
"""

from .errors import (
    EngineError, UNBALANCED_PARENS, UNEXPECTED_TOKEN, UNEXPECTED_END,
    MISSING_OPERAND, CONSECUTIVE_OPERATORS,
)
from .tokenizer import tokenize


class Node:
    __slots__ = ("pos",)

    def __init__(self, pos):
        self.pos = pos


class Number(Node):
    __slots__ = ("value",)

    def __init__(self, value, pos):
        super().__init__(pos)
        self.value = value


class Constant(Node):
    __slots__ = ("name",)

    def __init__(self, name, pos):
        super().__init__(pos)
        self.name = name


class Variable(Node):
    __slots__ = ("name",)

    def __init__(self, name, pos):
        super().__init__(pos)
        self.name = name


class UnaryOp(Node):
    __slots__ = ("op", "operand")

    def __init__(self, op, operand, pos):
        super().__init__(pos)
        self.op = op
        self.operand = operand


class BinaryOp(Node):
    __slots__ = ("op", "left", "right")

    def __init__(self, op, left, right, pos):
        super().__init__(pos)
        self.op = op
        self.left = left
        self.right = right


class FunctionCall(Node):
    __slots__ = ("name", "arg")

    def __init__(self, name, arg, pos):
        super().__init__(pos)
        self.name = name
        self.arg = arg


class Factorial(Node):
    __slots__ = ("operand",)

    def __init__(self, operand, pos):
        super().__init__(pos)
        self.operand = operand


_INFIX_BP = {"+": 10, "-": 10, "*": 20, "/": 20, "%": 20, "^": 40}
_RIGHT_ASSOC = {"^"}
_PREFIX_OPERANDS_BP = 40   # 一元正负号解析其操作数的最小绑定力
_POSTFIX_BP = {"!": 50}


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos]

    def next(self):
        t = self.tokens[self.pos]
        self.pos += 1
        return t

    def parse_expr(self, min_bp):
        """优先级爬升：解析一个表达式，吞入绑定力 >= min_bp 的运算符。"""
        lhs = self.parse_prefix()
        while True:
            tok = self.peek()
            if tok.type == "OP" and tok.value in _INFIX_BP:
                bp = _INFIX_BP[tok.value]
                if bp < min_bp:
                    break
                self.next()
                rhs_bp = bp if tok.value in _RIGHT_ASSOC else bp + 1
                rhs = self.parse_expr(rhs_bp)
                lhs = BinaryOp(tok.value, lhs, rhs, tok.pos)
            elif tok.type == "OP" and tok.value in _POSTFIX_BP:
                bp = _POSTFIX_BP[tok.value]
                if bp < min_bp:
                    break
                self.next()
                lhs = Factorial(lhs, tok.pos)
            else:
                break
        return lhs

    def parse_prefix(self):
        """解析一个前缀表达式（原子 / 一元 / 括号 / 函数调用）。"""
        tok = self.peek()

        # 一元正负号
        if tok.type == "OP" and tok.value in ("+", "-"):
            self.next()
            operand = self.parse_expr(_PREFIX_OPERANDS_BP)
            return UnaryOp(tok.value, operand, tok.pos)

        if tok.type == "NUM":
            self.next()
            return Number(tok.value, tok.pos)

        if tok.type == "CONST":
            self.next()
            return Constant(tok.value, tok.pos)

        if tok.type == "VAR":
            self.next()
            return Variable(tok.value, tok.pos)

        if tok.type == "FUNC":
            self.next()
            if self.peek().type != "LPAREN":
                raise EngineError(MISSING_OPERAND, "函数 %s 后缺少 '('" % tok.value, tok.pos)
            self.next()  # 吃掉 '('
            arg = self.parse_expr(0)
            if self.peek().type != "RPAREN":
                raise EngineError(UNBALANCED_PARENS, "函数 %s 缺少 ')'" % tok.value, self.peek().pos)
            self.next()
            return FunctionCall(tok.value, arg, tok.pos)

        if tok.type == "LPAREN":
            self.next()
            e = self.parse_expr(0)
            if self.peek().type != "RPAREN":
                raise EngineError(UNBALANCED_PARENS, "括号不匹配：缺少 ')'", self.peek().pos)
            self.next()
            return e

        # 以下都是「操作数缺失 / 意外符号」类错误
        if tok.type == "OP":
            raise EngineError(CONSECUTIVE_OPERATORS,
                              "运算符 '%s' 出现位置不正确（运算符连续或缺少操作数）" % tok.value, tok.pos)
        if tok.type == "RPAREN":
            raise EngineError(UNBALANCED_PARENS, "多余的 ')'", tok.pos)
        if tok.type == "EOF":
            raise EngineError(UNEXPECTED_END, "表达式不完整", tok.pos)
        raise EngineError(UNEXPECTED_TOKEN, "此处缺少操作数", tok.pos)


def parse(expr):
    """解析表达式字符串，返回 AST 根节点；任何语法问题都会抛 EngineError。"""
    tokens = tokenize(expr)
    parser = Parser(tokens)
    ast = parser.parse_expr(0)
    tail = parser.peek()
    if tail.type != "EOF":
        if tail.type == "OP":
            raise EngineError(CONSECUTIVE_OPERATORS, "运算符 '%s' 后缺少操作数" % tail.value, tail.pos)
        if tail.type == "RPAREN":
            raise EngineError(UNBALANCED_PARENS, "多余的 ')'", tail.pos)
        raise EngineError(MISSING_OPERAND, "缺少运算符", tail.pos)
    return ast
