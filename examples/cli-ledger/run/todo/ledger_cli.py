"""命令行层（worker B）。

按 SWARM-PLAN.md 的冻结契约调用 run/store/ledger_store.py。
"""
from __future__ import annotations

import argparse
import sys
from decimal import Decimal
from pathlib import Path

STORE_DIR = Path(__file__).resolve().parents[1] / "store"
sys.path.insert(0, str(STORE_DIR))

from ledger_store import DEFAULT_DATA_PATH, Ledger  # noqa: E402


class ChineseParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        print(f"错误：{message}", file=sys.stderr)
        raise SystemExit(2)


def fmt(value: Decimal) -> str:
    return f"{value:+.2f}"


def build_parser() -> argparse.ArgumentParser:
    parser = ChineseParser(
        prog="accountant",
        description="命令行记账工具：记一笔、查余额、看记录。数据保存在本地 JSONL 文件。",
        epilog="示例：accountant add 35.5 -c 餐饮 -n 午饭",
    )
    parser.add_argument(
        "--data",
        metavar="路径",
        default=None,
        help=f"账本文件路径（默认：{DEFAULT_DATA_PATH}）",
    )
    sub = parser.add_subparsers(dest="command", metavar="命令", parser_class=ChineseParser)

    p_add = sub.add_parser("add", help="记一笔（默认记支出）")
    p_add.add_argument("amount", metavar="金额", help="正数，精确到分，例如 35.5")
    p_add.add_argument("-c", "--category", default="未分类", help="分类，默认「未分类」")
    p_add.add_argument("-n", "--note", default="", help="备注")
    p_add.add_argument("--date", dest="when", default=None, help="日期，YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS")
    p_add.add_argument("--income", action="store_true", help="记收入（默认记支出）")

    sub.add_parser("balance", help="查余额")

    p_list = sub.add_parser("list", help="看记录（最新在前）")
    p_list.add_argument("--limit", type=int, default=None, help="只看最近 N 条")
    p_list.add_argument("--month", default=None, metavar="YYYY-MM", help="只看某个月")

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0

    ledger = Ledger(args.data or DEFAULT_DATA_PATH)
    try:
        if args.command == "add":
            entry = ledger.add(
                args.amount,
                category=args.category,
                note=args.note,
                when=args.when,
                income=args.income,
            )
            totals = ledger.balance()
            print(
                f"已记账：{entry['amount']}  {entry['category']}  "
                f"{entry['note'] or '—'}  {entry['ts'].replace('T', ' ')}"
            )
            print(f"当前余额：{fmt(totals['balance'])}（收入 {fmt(totals['total_income'])} / 支出 {fmt(-totals['total_expense'])}）")
            return 0

        if args.command == "balance":
            totals = ledger.balance()
            print(f"收入合计：{fmt(totals['total_income'])}")
            print(f"支出合计：{fmt(-totals['total_expense'])}")
            print(f"当前余额：{fmt(totals['balance'])}")
            print(f"记录条数：{totals['count']}")
            return 0

        if args.command == "list":
            rows = ledger.entries(limit=args.limit, month=args.month)
            if not rows:
                print("（没有记录）")
                return 0
            print("记录（最新在前）：")
            for entry in rows:
                print(
                    f"{entry['ts'].replace('T', ' ')}  {entry['amount']:>8}  "
                    f"{entry['category']}  {entry['note'] or '—'}"
                )
            totals = ledger.balance()
            print(f"共 {len(rows)} 条；余额 {fmt(totals['balance'])}")
            return 0
    except (ValueError, OSError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
