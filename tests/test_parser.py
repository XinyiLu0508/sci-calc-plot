# -*- coding: utf-8 -*-
"""语法分析器测试（结构、优先级、错误定位）。"""
from core.parser import parse, BinaryOp, UnaryOp, Factorial
from core.errors import EngineError


def test_nested_parens():
    ast = parse("((1+2)*3)")
    assert isinstance(ast, BinaryOp) and ast.op == "*"


def test_unary_minus_binds_looser_than_pow():
    # -2^2 = -(2^2)
    ast = parse("-2^2")
    assert isinstance(ast, UnaryOp) and ast.op == "-"
    assert isinstance(ast.operand, BinaryOp) and ast.operand.op == "^"


def test_pow_right_assoc():
    ast = parse("2^3^2")
    assert isinstance(ast, BinaryOp) and ast.op == "^"
    assert isinstance(ast.right, BinaryOp) and ast.right.op == "^"


def test_factorial_postfix():
    assert isinstance(parse("5!"), Factorial)


def test_consecutive_operators_error():
    for e in ["1*/2", "1^/2", "1+*2"]:
        try:
            parse(e)
            assert False, e
        except EngineError as err:
            assert err.code == "CONSECUTIVE_OPERATORS", e


def test_unbalanced_parens_missing():
    try:
        parse("(1+2")
        assert False
    except EngineError as e:
        assert e.code == "UNBALANCED_PARENS"


def test_unbalanced_parens_extra():
    try:
        parse("1+2)")
        assert False
    except EngineError as e:
        assert e.code == "UNBALANCED_PARENS"


def test_error_position():
    try:
        parse("1+2)")
        assert False
    except EngineError as e:
        assert e.position == 3


def test_missing_operator_between_numbers():
    try:
        parse("2 3")
        assert False
    except EngineError as e:
        assert e.code == "MISSING_OPERAND"


def test_empty_expression():
    try:
        parse("")
        assert False
    except EngineError as e:
        assert e.code == "UNEXPECTED_END"
