# -*- coding: utf-8 -*-
"""pytest 配置：把项目根目录加入 sys.path，使 `import core` 可用。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
