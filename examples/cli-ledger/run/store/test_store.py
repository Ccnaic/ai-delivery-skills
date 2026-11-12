"""worker A 自测：数据层。运行：python run/store/test_store.py"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ledger_store import Ledger, parse_amount  # noqa: E402


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "nested" / "ledger.jsonl"
        self.ledger = Ledger(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_add_writes_and_new_instance_reads(self):
        self.ledger.add("35.5", category="餐饮", note="午饭", when="2026-11-01 12:00:00")
        other = Ledger(self.path)
        rows = other.entries()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["amount"], "-35.50")
        self.assertEqual(rows[0]["category"], "餐饮")
        self.assertEqual(rows[0]["note"], "午饭")
        # 副作用：文件里确实有 1 行合法 JSON
        lines = self.path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])["amount"], "-35.50")

    def test_balance_is_exact_to_cent(self):
        self.ledger.add("100.10", when="2026-11-01", income=True)
        self.ledger.add("0.1", when="2026-11-02")
        self.ledger.add("0.2", when="2026-11-03")
        got = self.ledger.balance()
        self.assertEqual(got["total_income"], Decimal("100.10"))
        self.assertEqual(got["total_expense"], Decimal("0.30"))
        self.assertEqual(got["balance"], Decimal("99.80"))
        self.assertEqual(got["count"], 3)

    def test_order_limit_and_income(self):
        self.ledger.add("10", when="2026-11-01")
        self.ledger.add("20", when="2026-11-03", income=True)
        self.ledger.add("30", when="2026-11-02")
        rows = self.ledger.entries()
        self.assertEqual([r["ts"][:10] for r in rows], ["2026-11-03", "2026-11-02", "2026-11-01"])
        self.assertEqual(rows[0]["amount"], "+20.00")
        self.assertEqual(len(self.ledger.entries(limit=2)), 2)

    def test_month_filter(self):
        self.ledger.add("10", when="2026-10-31")
        self.ledger.add("20", when="2026-11-01")
        self.ledger.add("30", when="2026-11-30")
        self.assertEqual(len(self.ledger.entries(month="2026-11")), 2)
        self.assertEqual(len(self.ledger.entries(month="2026-10")), 1)
        self.assertEqual(len(self.ledger.entries(month="2026-12")), 0)

    def test_rejects_bad_amounts(self):
        for bad in ("abc", "", "0", "-5", "NaN", "Infinity"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    parse_amount(bad)
                with self.assertRaises(ValueError):
                    self.ledger.add(bad)

    def test_rejects_bad_date_and_month(self):
        with self.assertRaises(ValueError):
            self.ledger.add("1", when="11/08/2026")
        with self.assertRaises(ValueError):
            self.ledger.entries(month="2026-13")
        with self.assertRaises(ValueError):
            self.ledger.entries(limit=-1)

    def test_empty_ledger(self):
        self.assertEqual(self.ledger.entries(), [])
        got = self.ledger.balance()
        self.assertEqual(got["count"], 0)
        self.assertEqual(got["balance"], Decimal("0.00"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
