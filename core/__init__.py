# -*- coding: utf-8 -*-
"""Web 科学计算器 + 函数图像绘制平台 —— Python 核心引擎。

模块划分（依赖方向单向，越往后越靠近对外入口）：
    errors     —— 统一结构化错误定义
    tokenizer  —— 词法分析（含「有限隐式乘法」处理）
    parser     —— 语法分析（Pratt 递归下降 → AST）
    evaluator  —— 安全求值（Decimal 高精度 + 定义域检查 + 结果净化）
    sampler    —— 函数采样（自适应加密 + 断点检测 + LOD）
    engine     —— 对外统一入口 evaluate / validate / sample_function

本包只使用 Python 标准库，可同时运行在 CPython（pytest / FastAPI）与 Pyodide（WASM）下。
"""

__version__ = "1.0.0"
