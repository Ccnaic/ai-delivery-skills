"""用户入口（block C：收口）。

把 run/todo 的命令层和 run/store 的数据层接到一起，用户只需要敲这个文件。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "run" / "todo"))
sys.path.insert(0, str(ROOT / "run" / "store"))

from ledger_cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
