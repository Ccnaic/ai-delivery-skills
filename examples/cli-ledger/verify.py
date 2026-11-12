"""项目级验证工具（verify-app）。

用法：
    python verify.py
    python verify.py --root <项目根> --evidence-dir <证据目录>

驱动的是真实用户路径：subprocess 调用 accountant.py。
不使用内部 setter，不直接写账本冒充功能可用。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

REQUIRED_KEYS = {"id", "ts", "amount", "category", "note"}


class Verifier:
    def __init__(self, root: Path, evidence_dir: Path):
        self.root = root.resolve()
        self.evidence_dir = evidence_dir.resolve()
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.lines: list[str] = []
        self.results: list[tuple[bool, str, str]] = []
        self._tmp = tempfile.TemporaryDirectory()
        self.data = Path(self._tmp.name) / "ledger.jsonl"
        self.entry_count = 0

    def record(self, text: str = "") -> None:
        self.lines.append(text)

    def run(self, *args: str, py_isolated: bool = False) -> subprocess.CompletedProcess:
        cmd = [sys.executable]
        if py_isolated:
            cmd.append("-I")
        cmd += ["-X", "utf8", str(self.root / "accountant.py"), "--data", str(self.data), *args]
        result = subprocess.run(
            cmd,
            cwd=str(self.root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
        self.record(f"$ {' '.join(cmd[1:])}")
        self.record(f"  exit={result.returncode}")
        if result.stdout.strip():
            for line in result.stdout.rstrip().splitlines():
                self.record(f"  out| {line}")
        if result.stderr.strip():
            for line in result.stderr.rstrip().splitlines():
                self.record(f"  err| {line}")
        return result

    def check(self, name: str, ok: bool, detail: str) -> None:
        self.results.append((ok, name, detail))
        self.record(f"[{'PASS' if ok else 'FAIL'}] {name} :: {detail}")

    def add_sample_entries(self) -> None:
        r1 = self.run("add", "100.10", "--income", "--date", "2026-11-01")
        self.check(
            "add 记收入",
            r1.returncode == 0 and "已记账：+100.10" in r1.stdout,
            f"exit={r1.returncode}",
        )

        r2 = self.run("add", "35.5", "-c", "餐饮", "-n", "午饭", "--date", "2026-11-02")
        self.check(
            "add 记支出（分类/备注）",
            r2.returncode == 0 and "-35.50" in r2.stdout and "餐饮" in r2.stdout,
            f"exit={r2.returncode}",
        )

        r3 = self.run("add", "0.1", "--date", "2026-11-03")
        self.check("add 第三笔", r3.returncode == 0, f"exit={r3.returncode}")

        # 副作用：账本真的多了 3 行，且每行是合法 JSON
        ok = False
        detail = "文件不存在"
        if self.data.exists():
            rows = [line for line in self.data.read_text(encoding="utf-8").splitlines() if line.strip()]
            parsed = [json.loads(line) for line in rows]
            ok = len(rows) == 3 and all(REQUIRED_KEYS <= set(row) for row in parsed)
            detail = f"行数={len(rows)}"
            self.entry_count = len(rows)
        self.check("副作用：账本落盘 3 行合法 JSON", ok, detail)

    def check_balance(self) -> None:
        result = self.run("balance")
        text = result.stdout
        ok = (
            result.returncode == 0
            and "收入合计：+100.10" in text
            and "支出合计：-35.60" in text
            and "当前余额：+64.50" in text
            and "记录条数：3" in text
        )
        self.check("balance 精确到分（100.10 - 35.50 - 0.10 = 64.50）", ok, f"exit={result.returncode}")

    def check_list(self) -> None:
        result = self.run("list")
        text = result.stdout
        order_ok = (
            "2026-11-03" in text
            and "2026-11-02" in text
            and "2026-11-01" in text
            and text.index("2026-11-03") < text.index("2026-11-02") < text.index("2026-11-01")
        )
        self.check("list 最新在前", result.returncode == 0 and order_ok, f"exit={result.returncode}")

        limited = self.run("list", "--limit", "2")
        self.check(
            "list --limit 2 只出 2 条",
            limited.returncode == 0
            and "共 2 条" in limited.stdout
            and "2026-11-01" not in limited.stdout,
            f"exit={limited.returncode}",
        )

        month = self.run("list", "--month", "2026-11")
        self.check(
            "list --month 2026-11 命中 3 条",
            month.returncode == 0 and "共 3 条" in month.stdout,
            f"exit={month.returncode}",
        )

        empty = self.run("list", "--month", "2026-10")
        self.check(
            "list --month 2026-10 为空",
            empty.returncode == 0 and "没有记录" in empty.stdout,
            f"exit={empty.returncode}",
        )

    def check_errors(self) -> None:
        for label, args in (
            ("非数字金额", ("add", "abc")),
            ("零金额", ("add", "0")),
            ("负金额", ("add", "-5")),
            ("非法日期", ("add", "1", "--date", "11/08/2026")),
            ("非法月份", ("list", "--month", "2026-13")),
        ):
            result = self.run(*args)
            self.check(
                f"错误输入：{label}",
                result.returncode == 2 and "错误" in result.stderr,
                f"exit={result.returncode}",
            )

    def check_zero_dependencies(self) -> None:
        result = self.run("--help", py_isolated=True)
        self.check(
            "零第三方依赖（python -I 隔离环境仍可 --help）",
            result.returncode == 0 and "add" in result.stdout,
            f"exit={result.returncode}",
        )
        self.check(
            "帮助可读（含示例）",
            "示例" in result.stdout and "记一笔" in result.stdout,
            "help 文本",
        )

    def execute(self) -> int:
        self.record("=" * 72)
        self.record(f"verify-app evidence  {datetime.now().isoformat(timespec='seconds')}")
        self.record(f"root={self.root}")
        self.record(f"data={self.data}")
        self.record("=" * 72)

        help_result = self.run("--help")
        self.check(
            "启动：--help 退出码 0 且列出三命令",
            help_result.returncode == 0
            and all(name in help_result.stdout for name in ("add", "balance", "list")),
            f"exit={help_result.returncode}",
        )
        self.check(
            "就绪判定：帮助里出现「命令行记账工具」",
            "命令行记账工具" in help_result.stdout,
            "help 标题",
        )

        self.add_sample_entries()
        self.check_balance()
        self.check_list()
        self.check_errors()
        self.check_zero_dependencies()

        # 清理后证据必须还在
        evidence = self.evidence_dir / f"verify_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        self._tmp.cleanup()
        self.check("清理：临时账本已删除", not self.data.exists(), str(self.data))
        evidence.write_text("\n".join(self.lines) + "\n", encoding="utf-8")
        self.check("清理后证据仍在", evidence.exists() and evidence.stat().st_size > 0, str(evidence))

        failed = [name for ok, name, _ in self.results if not ok]
        self.record("")
        self.record(
            f"RESULT: {len(self.results) - len(failed)}/{len(self.results)} PASS; "
            f"{len(failed)} FAIL"
        )
        evidence.write_text("\n".join(self.lines) + "\n", encoding="utf-8")
        print("\n".join(self.lines))
        print(f"\n证据文件：{evidence}")
        print(f"结论：{'PASS' if not failed else 'FAIL'} ({len(self.results) - len(failed)}/{len(self.results)})")
        return 0 if not failed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="驱动 accountant.py 做端到端验证")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent), help="项目根目录")
    parser.add_argument("--evidence-dir", default=None, help="证据目录（默认 <root>/evidence）")
    args = parser.parse_args()
    root = Path(args.root)
    evidence_dir = Path(args.evidence_dir) if args.evidence_dir else root / "evidence"
    return Verifier(root, evidence_dir).execute()


if __name__ == "__main__":
    raise SystemExit(main())
