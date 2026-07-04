"""双击运行入口。

直接执行 main 模块，避免显示命令行窗口。
"""

from __future__ import annotations

import runpy


if __name__ == "__main__":
    runpy.run_module("main", run_name="__main__")