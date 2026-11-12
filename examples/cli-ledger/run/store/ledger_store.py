"""账本数据层（worker A）。

只依赖标准库。对外接口见 SWARM-PLAN.md 的冻结契约。
"""
from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

DEFAULT_DATA_PATH = Path(
    os.environ.get("LEDGER_FILE", str(Path.home() / ".ledger-cli" / "ledger.jsonl"))
)

_CENT = Decimal("0.01")
_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def parse_amount(raw) -> Decimal:
    """把用户输入变成精确到分的正数 Decimal；不合法抛 ValueError。"""
    try:
        value = Decimal(str(raw).strip())
    except (InvalidOperation, ValueError, AttributeError):
        raise ValueError(f"金额不是数字：{raw!r}")
    if not value.is_finite():
        raise ValueError(f"金额不是有限数字：{raw!r}")
    if value <= 0:
        raise ValueError(f"金额必须大于 0：{raw!r}")
    return value.quantize(_CENT, rounding=ROUND_HALF_UP)


def _normalize_when(when: str | None) -> str:
    if not when:
        return datetime.now().isoformat(timespec="seconds")
    text = str(when).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).isoformat(timespec="seconds")
        except ValueError:
            continue
    raise ValueError(f"日期格式不对：{when!r}（要 YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS）")


class Ledger:
    def __init__(self, path=DEFAULT_DATA_PATH):
        self.path = Path(path)

    def add(self, amount, category="未分类", note="", when=None, income=False) -> dict:
        value = parse_amount(amount)
        signed = value if income else -value
        entry = {
            "id": str(time.time_ns()),
            "ts": _normalize_when(when),
            "amount": format(signed, "+.2f"),
            "category": (category or "").strip() or "未分类",
            "note": (note or "").strip(),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(entry, ensure_ascii=False, separators=(",", ":"))
        with open(self.path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(line + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        return entry

    def entries(self, limit=None, month=None) -> list[dict]:
        text = None
        if month:
            text = str(month).strip()
            if not _MONTH_RE.match(text):
                raise ValueError(f"月份格式不对：{month!r}（要 YYYY-MM）")
        if limit is not None and limit < 0:
            raise ValueError("--limit 不能是负数")
        if not self.path.exists():
            return []
        result: list[dict] = []
        with open(self.path, "r", encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    float(entry["amount"])  # 至少能转成数
                    entry["ts"]
                except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                    raise ValueError(f"账本第 {lineno} 行损坏：{exc}") from exc
                result.append(entry)
        if text:
            result = [e for e in result if e["ts"][:7] == text]
        result.sort(key=lambda e: (e["ts"], int(e["id"])), reverse=True)
        if limit is not None:
            result = result[:limit]
        return result

    def balance(self) -> dict:
        entries = self.entries()
        total_income = Decimal("0.00")
        total_expense = Decimal("0.00")
        for entry in entries:
            amount = Decimal(entry["amount"])
            if amount >= 0:
                total_income += amount
            else:
                total_expense += -amount
        return {
            "total_income": total_income,
            "total_expense": total_expense,
            "balance": total_income - total_expense,
            "count": len(entries),
        }
