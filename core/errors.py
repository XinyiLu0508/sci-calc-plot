# -*- coding: utf-8 -*-
"""核心引擎统一错误定义。

所有错误都携带结构化信息：
    code      —— 机器可读错误码（前端据此选择展示样式）
    message   —— 中文可读提示
    position  —— 错误发生处距表达式开头的字符偏移（0 起，-1 表示无法定位）

前端拿到 {"code","message","position"} 后可直接渲染「位置 N 附近：...」的提示。
"""


class EngineError(Exception):
    """结构化引擎错误，同时被计算器求值与绘图采样使用。"""

    def __init__(self, code, message, position=-1):
        super().__init__(message)
        self.code = code
        self.message = message
        self.position = position

    def to_dict(self):
        return {"code": self.code, "message": self.message, "position": self.position}


# ---- 词法 / 语法类 ----
INVALID_TOKEN = "INVALID_TOKEN"                # 非法字符
UNKNOWN_FUNCTION = "UNKNOWN_FUNCTION"          # 未知标识符 / 函数名
UNEXPECTED_TOKEN = "UNEXPECTED_TOKEN"          # 语法位置出现意外符号
UNEXPECTED_END = "UNEXPECTED_END"              # 表达式提前结束
UNBALANCED_PARENS = "UNBALANCED_PARENS"        # 括号不匹配
MISSING_OPERAND = "MISSING_OPERAND"            # 缺少操作数 / 运算符
CONSECUTIVE_OPERATORS = "CONSECUTIVE_OPERATORS"  # 运算符连续（如 1 * / 2）

# ---- 求值类 ----
DIVISION_BY_ZERO = "DIVISION_BY_ZERO"
MODULO_BY_ZERO = "MODULO_BY_ZERO"
NEGATIVE_SQRT = "NEGATIVE_SQRT"
LOG_DOMAIN = "LOG_DOMAIN"
ASIN_ACOS_DOMAIN = "ASIN_ACOS_DOMAIN"
INVALID_FACTORIAL = "INVALID_FACTORIAL"
NEGATIVE_POWER = "NEGATIVE_POWER"              # 负数的非整数次幂
ZERO_POWER_NEGATIVE = "ZERO_POWER_NEGATIVE"    # 0 的负次幂
OVERFLOW = "OVERFLOW"
UNKNOWN_VARIABLE = "UNKNOWN_VARIABLE"          # 计算器里出现了自变量 x

# ---- 绘图类 ----
NOT_A_FUNCTION = "NOT_A_FUNCTION"              # 表达式无法解析为 y=f(x)
EMPTY_DOMAIN = "EMPTY_DOMAIN"                  # 当前范围内无有效定义域
INVALID_RANGE = "INVALID_RANGE"                # 取值范围非法
