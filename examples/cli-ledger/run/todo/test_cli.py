"""worker B 自测：命令层。运行：python run/todo/test_cli.py"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CLI = Path(__file__).resolve().parent / "ledger_cli.py"


class CliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name) / "ledger.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(CLI), "--data", str(self.data), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def test_help_lists_three_commands(self):
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0)
        for word in ("add", "balance", "list"):
            self.assertIn(word, result.stdout)

    def test_no_command_prints_help(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 0)
        self.assertIn("记一笔", result.stdout)

    def test_full_user_flow(self):
        r1 = self.run_cli("add", "100.10", "--income", "--date", "2026-11-01")
        self.assertEqual(r1.returncode, 0, r1.stderr)
        r2 = self.run_cli("add", "35.5", "-c", "餐饮", "-n", "午饭", "--date", "2026-11-02")
        self.assertEqual(r2.returncode, 0, r2.stderr)
        r3 = self.run_cli("add", "0.1", "--date", "2026-11-03")
        self.assertEqual(r3.returncode, 0, r3.stderr)

        # 副作用：一个进程写，另一个进程读得到
        self.assertEqual(len(self.data.read_text(encoding="utf-8").splitlines()), 3)

        balance = self.run_cli("balance")
        self.assertEqual(balance.returncode, 0)
        self.assertIn("收入合计：+100.10", balance.stdout)
        self.assertIn("支出合计：-35.60", balance.stdout)
        self.assertIn("当前余额：+64.50", balance.stdout)
        self.assertIn("记录条数：3", balance.stdout)

        listing = self.run_cli("list", "--limit", "2")
        self.assertEqual(listing.returncode, 0)
        body = listing.stdout
        self.assertLess(body.index("2026-11-03"), body.index("2026-11-02"))
        self.assertNotIn("2026-11-01", body)
        self.assertIn("共 2 条", body)

        month = self.run_cli("list", "--month", "2026-11")
        self.assertIn("共 3 条", month.stdout)
        empty = self.run_cli("list", "--month", "2026-10")
        self.assertIn("没有记录", empty.stdout)

    def test_bad_input_exits_2_with_chinese_error(self):
        for args in (
            ("add", "abc"),
            ("add", "0"),
            ("add", "-5"),
            ("add", "1", "--date", "11/08/2026"),
            ("list", "--month", "2026-13"),
            ("list", "--limit", "-1"),
        ):
            with self.subTest(args=args):
                result = self.run_cli(*args)
                self.assertEqual(result.returncode, 2, (args, result.stdout, result.stderr))
                self.assertIn("错误", result.stderr)

    def test_balance_on_missing_file(self):
        result = self.run_cli("balance")
        self.assertEqual(result.returncode, 0)
        self.assertIn("当前余额：+0.00", result.stdout)
        self.assertIn("记录条数：0", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
