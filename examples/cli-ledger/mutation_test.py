"""变异测试：证明 verify.py 的判据不是恒真的。

做法：复制一份应用，把 balance() 改成永远返回 0，再跑同一份 verify.py。
期望：基线 PASS，变异版 FAIL。若变异版仍 PASS，说明判据失效。
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VERIFY = ROOT / "verify.py"


def run_verify(root: Path, evidence: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-X", "utf8", str(VERIFY), "--root", str(root), "--evidence-dir", str(evidence)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )


def main() -> int:
    evidence_dir = ROOT / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.TemporaryDirectory()
    base = Path(tmp.name)

    baseline = run_verify(ROOT, base / "baseline_evidence")

    mutant = base / "mutant"
    (mutant / "run" / "store").mkdir(parents=True)
    (mutant / "run" / "todo").mkdir(parents=True)
    shutil.copy2(ROOT / "accountant.py", mutant / "accountant.py")
    shutil.copy2(ROOT / "run" / "store" / "ledger_store.py", mutant / "run" / "store" / "ledger_store.py")
    shutil.copy2(ROOT / "run" / "todo" / "ledger_cli.py", mutant / "run" / "todo" / "ledger_cli.py")

    target = mutant / "run" / "store" / "ledger_store.py"
    source = target.read_text(encoding="utf-8")
    old = "    def balance(self) -> dict:\n        entries = self.entries()"
    new = (
        "    def balance(self) -> dict:\n"
        '        return {"total_income": Decimal("0.00"), "total_expense": Decimal("0.00"), '
        '"balance": Decimal("0.00"), "count": 0}\n'
        "        entries = self.entries()"
    )
    if old not in source:
        print("变异失败：找不到 balance() 的插入点")
        return 1
    target.write_text(source.replace(old, new, 1), encoding="utf-8")

    mutated = run_verify(mutant, base / "mutant_evidence")

    detected = (
        baseline.returncode == 0
        and mutated.returncode != 0
        and "FAIL" in mutated.stdout
        and "balance" in mutated.stdout
    )
    failed_lines = [line for line in mutated.stdout.splitlines() if "[FAIL]" in line]
    mutant_files = sorted((base / "mutant_evidence").glob("verify_*.txt"))
    if mutant_files:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(mutant_files[-1], evidence_dir / f"mutation_verify_{stamp}.txt")

    report = [
        "=" * 72,
        f"变异测试  {datetime.now().isoformat(timespec='seconds')}",
        "=" * 72,
        f"基线 verify.py exit={baseline.returncode}（期望 0）",
        f"变异版 verify.py exit={mutated.returncode}（期望非 0）",
        f"结论：{'检测到破坏，判据有效 (PASS)' if detected else '未检测到破坏，判据失效 (FAIL)'}",
        "",
        "--- 变异版失败项（应该抓到 balance 恒为 0）---",
        *(failed_lines or ["（没有 FAIL 行）"]),
        "",
        "完整变异转录：evidence/mutation_verify_<时间戳>.txt",
        "",
        "--- 变异版 verify 输出（末尾）---",
        "\n".join(mutated.stdout.rstrip().splitlines()[-10:]),
        "",
    ]
    text = "\n".join(report)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = evidence_dir / f"mutation_test_{stamp}.txt"
    out.write_text(text, encoding="utf-8")
    print(text)
    print(f"证据文件：{out}")
    print("（本次输出用时间戳命名，不会覆盖仓库里已提交的 mutation_test.txt）")
    tmp.cleanup()
    return 0 if detected else 1


if __name__ == "__main__":
    raise SystemExit(main())
