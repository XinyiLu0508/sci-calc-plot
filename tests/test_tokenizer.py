# -*- coding: utf-8 -*-
"""词法分析器测试。"""
from core.tokenizer import tokenize
from core.errors import EngineError


def _types(expr):
    return [t.type for t in tokenize(expr)]


def _pairs(expr):
    return [(t.type, t.value) for t in tokenize(expr)]


def test_numbers_and_operators():
    assert _types("1+2") == ["NUM", "OP", "NUM", "EOF"]


def test_implicit_mul_number_var():
    ts = tokenize("2x")
    assert [t.type for t in ts] == ["NUM", "OP", "VAR", "EOF"]
    assert ts[1].value == "*"


def test_implicit_mul_number_paren():
    ts = tokenize("2(x+1)")
    assert ts[1].type == "OP" and ts[1].value == "*"


def test_implicit_mul_paren_paren():
    assert ("OP", "*") in _pairs("(x+1)(x-1)")


def test_implicit_mul_rparen_num():
    assert ("OP", "*") in _pairs("(x+1)2")


def test_implicit_mul_number_const():
    # 3π → 3 * π
    ts = tokenize("3π")
    assert [t.type for t in ts] == ["NUM", "OP", "CONST", "EOF"]


def test_implicit_mul_var_const():
    # xπ → x * π
    assert ("OP", "*") in _pairs("xπ")


def test_no_implicit_mul_num_num():
    assert ("OP", "*") not in _pairs("2 3")


def test_no_implicit_mul_var_var():
    assert ("OP", "*") not in _pairs("x x")


def test_pi_symbol_constant():
    ts = tokenize("π")
    assert ts[0].type == "CONST" and ts[0].value == "pi"


def test_unknown_identifier():
    try:
        tokenize("foo")
        assert False
    except EngineError as e:
        assert e.code == "UNKNOWN_FUNCTION"


def test_invalid_char():
    try:
        tokenize("1@2")
        assert False
    except EngineError as e:
        assert e.code == "INVALID_TOKEN"


def test_scientific_notation():
    ts = tokenize("1e3")
    assert ts[0].type == "NUM" and ts[0].value == "1e3"


def test_function_token():
    ts = tokenize("sin(x)")
    assert ts[0].type == "FUNC" and ts[0].value == "sin"
