"""G1 检查器：把 deliver/SKILL.md 里 G1 的判据机械地算一遍。

判据：
  每格必须是三选一 → `人证 Qn`（附原话）/ `【AI 假设】` / `【待定】`
  「代答」= 没有真人给值 → 按 【AI 假设】 计
  「标了人但没 Q 编号和原话」也无法核验 → 按 【AI 假设】 计
  K =（AI假设 + 待定）的格数。K=0 → ✅；K>0 → ⚠️ 且 N/M 加「其中 K 条分母未经人确认」

用法：
  python tools/g1-check.py <菜谱.md>
  python tools/g1-check.py                      # 默认检查 examples/cli-ledger/RECIPE.md

退出码：0 = ✅ 通过；1 = ⚠️ 降级；2 = 文件或表格不存在
"""
import io
import os
import re
import sys


def parse_table(lines, start_kw):
    """取出 start_kw 之后的第一个 markdown 表，返回 [(项, 决定, 来源)]。"""
    i = 0
    while i < len(lines) and start_kw not in lines[i]:
        i += 1
    if i >= len(lines):
        return []
    # 找表头
    while i < len(lines) and not lines[i].strip().startswith("|"):
        i += 1
    rows = []
    while i < len(lines) and lines[i].strip().startswith("|"):
        cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
        if not set("".join(cells)) <= set("-: "):
            rows.append(cells)
        i += 1
    return rows[1:]  # 去掉表头


def classify(source):
    """返回 (类别, 说明)。类别 ∈ 人证 / AI假设 / 待定 / 无效。"""
    s = source.strip()
    if not s:
        return "无效", "空 —— 不是合法状态"
    if "待定" in s:
        return "待定", "用户明确不知道"
    # 代答 = 没有真人
    if "代答" in s:
        return "AI假设", "代答：没有真人给值"
    if "AI" in s and ("假设" in s or "推断" in s):
        # 混写（既有人的部分又有 AI 推断）也算存在 AI 成分
        return "AI假设", "含 AI 推断成分"
    m = re.search(r"人证\s*Q?\d*", s)
    if m:
        # 人证必须附原话（引号或「」）
        if ("「" in s and "」" in s) or '"' in s:
            return "人证", "有 Q 编号 + 原话"
        return "AI假设", "标了人证但没附原话"
    if s.startswith("人") or "人（" in s or "人(" in s:
        return "AI假设", "标了「人」但无 Q 编号与原话，无法核验"
    return "无效", "不在值域内：%s" % s


def main(path):
    lines = io.open(path, encoding="utf-8").read().split("\n")
    scope = parse_table(lines, "## 范围决策")
    cons = parse_table(lines, "## 约束")

    print("=" * 72)
    print("新 G1 判定：", path)
    print("=" * 72)

    k = 0
    bad = 0
    print("\n【范围决策】")
    for row in scope:
        item = row[0]
        src = row[2] if len(row) > 2 else ""
        cat, why = classify(src)
        if cat in ("AI假设", "待定"):
            k += 1
        if cat == "无效":
            bad += 1
        print("  %-22s → %-6s  %s" % (item[:22], cat, why))

    print("\n【约束】")
    has_budget_row = any("预算" in r[0] for r in scope)
    if not cons:
        if has_budget_row:
            print("  （没有独立约束表，但「预算」在范围决策里，不重复计）")
        else:
            print("  （没有约束表，也没有预算行）→ 计 1")
            k += 1
    else:
        for row in cons:
            item = row[0]
            src = row[2] if len(row) > 2 else ""
            cat, why = classify(src)
            if cat in ("AI假设", "待定"):
                k += 1
            if cat == "无效":
                bad += 1
            print("  %-22s → %-6s  %s" % (item[:22], cat, why))

    total = len(scope) + (len(cons) if cons else (0 if has_budget_row else 1))
    print("\n" + "-" * 72)
    print("  检查格数: %d" % total)
    print("  K = %d   （无效格 %d）" % (k, bad))
    if k == 0 and bad == 0:
        print("  结果: ✅ 通过")
    else:
        print("  结果: ⚠️ 降级 —— N/M 完成（其中 %d 条分母未经人确认）" % k)
    print("=" * 72)
    return 0 if (k == 0 and bad == 0) else 1


if __name__ == "__main__":
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        here = os.path.dirname(os.path.abspath(__file__))
        target = os.path.join(here, "..", "examples", "cli-ledger", "RECIPE.md")
    if not os.path.exists(target):
        print("找不到菜谱：", target)
        sys.exit(2)
    sys.exit(main(target))
