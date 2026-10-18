# -*- coding: utf-8 -*-
"""求值器测试（优先级、精度、定义域、错误码）。"""
from core import engine


def test_precedence():
    assert engine.evaluate("2+3*4")["display"] == "14"
    assert engine.evaluate("(2+3)*4")["display"] == "20"


def test_float_precision():
    r = engine.evaluate("0.1+0.2")
    assert r["ok"] and r["display"] == "0.3"


def test_division():
    assert engine.evaluate("10/4")["display"] == "2.5"


def test_division_by_zero():
    r = engine.evaluate("1/0")
    assert not r["ok"] and r["error"]["code"] == "DIVISION_BY_ZERO"


def test_sqrt_negative():
    r = engine.evaluate("sqrt(-1)")
    assert not r["ok"] and r["error"]["code"] == "NEGATIVE_SQRT"


def test_log_zero():
    r = engine.evaluate("log(0)")
    assert not r["ok"] and r["error"]["code"] == "LOG_DOMAIN"


def test_log_negative():
    r = engine.evaluate("log(-1)")
    assert not r["ok"] and r["error"]["code"] == "LOG_DOMAIN"


def test_ln_one():
    assert engine.evaluate("ln(1)")["display"] == "0"


def test_factorial():
    assert engine.evaluate("5!")["display"] == "120"
    assert engine.evaluate("0!")["display"] == "1"


def test_factorial_invalid_negative():
    r = engine.evaluate("(-1)!")
    assert not r["ok"] and r["error"]["code"] == "INVALID_FACTORIAL"


def test_factorial_invalid_fraction():
    r = engine.evaluate("2.5!")
    assert not r["ok"] and r["error"]["code"] == "INVALID_FACTORIAL"


def test_sin_pi_cleanup():
    assert engine.evaluate("sin(pi)")["display"] == "0"


def test_cos_zero():
    assert engine.evaluate("cos(0)")["display"] == "1"


def test_negative_fractional_power():
    r = engine.evaluate("(-8)^(1/3)")
    assert not r["ok"] and r["error"]["code"] == "NEGATIVE_POWER"


def test_zero_power_zero():
    assert engine.evaluate("0^0")["display"] == "1"


def test_modulo():
    assert engine.evaluate("10%3")["display"] == "1"


def test_deg_mode():
    r = engine.evaluate("sin(90)", "deg")
    assert r["ok"] and r["display"] == "1"


def test_unknown_variable():
    r = engine.evaluate("x")
    assert not r["ok"] and r["error"]["code"] == "UNKNOWN_VARIABLE"


def test_right_assoc_pow():
    assert engine.evaluate("2^3^2")["display"] == "512"


def test_unary_minus_pow():
    assert engine.evaluate("-2^2")["display"] == "-4"
    assert engine.evaluate("(-2)^2")["display"] == "4"


def test_large_number():
    r = engine.evaluate("10^100")
    assert r["ok"]


def test_constants():
    assert engine.evaluate("pi")["display"].startswith("3.14159")
    assert engine.evaluate("e")["display"].startswith("2.71828")


def test_implicit_mul_eval():
    assert engine.evaluate("2(3+4)")["display"] == "14"
    r = engine.evaluate("2pi")
    assert r["ok"] and r["display"].startswith("6.283")


def test_validate():
    assert engine.validate("1+2")["ok"] is True
    assert engine.validate("1+")["ok"] is False
