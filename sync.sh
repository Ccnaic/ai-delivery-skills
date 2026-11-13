#!/usr/bin/env bash
# sync.sh — 一键安装 / 同步本仓库的 skill 到用户级目录
#
# 它做一件事：把本目录下的 5 个 skill 复制到 ~/.workbuddy/skills/
#
# 用法：
#   ./sync.sh             安装 / 同步
#   ./sync.sh --dry-run   只看会改什么，不动文件
#
# 三种场景都适用：
#   1. 刚 clone 下来，想装上         → 直接跑
#   2. 改完 skill，想同步到已装的    → 直接跑（旧版自动备份成 .bak_时间戳）
#   3. 只想看会改什么                → 加 --dry-run
#
# 只碰下面 SKILLS 里列出的 5 个，其余（比如你自己的 deja-history）一概不动。
#
# 注意：这 5 个必须一起装。recipe/swarm/verify-app/encode-lessons 互相独立，
#       但 deliver 依赖它们四个——只装 deliver 会在第一个重档任务里断掉。
# 装完要新开一个会话才生效——技能清单是会话启动时生成的。

set -uo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
DST="$HOME/.workbuddy/skills"
SKILLS=(deliver recipe swarm verify-app encode-lessons)

DRY=0
[ "${1:-}" = "--dry-run" ] && DRY=1

# ---------- 前置检查 ----------
if [ ! -d "$SRC" ]; then
  echo "✗ 源目录不存在: $SRC"
  exit 1
fi
if [ ! -d "$DST" ]; then
  echo "→ 用户级目录不存在，创建: $DST"
  [ "$DRY" -eq 0 ] && mkdir -p "$DST"
fi

echo "源  : $SRC"
echo "目标: $DST"
[ "$DRY" -eq 1 ] && echo "模式: dry-run（不改文件）"
echo

# ---------- 逐条同步 ----------
changed=0
skipped=0
failed=0

for s in "${SKILLS[@]}"; do
  src_file="$SRC/$s/SKILL.md"
  dst_dir="$DST/$s"
  dst_file="$dst_dir/SKILL.md"

  # 源必须存在
  if [ ! -f "$src_file" ]; then
    printf "✗ %-16s 源里没有 SKILL.md\n" "$s"
    failed=$((failed + 1))
    continue
  fi

  # frontmatter 必须完整（name + description）
  if ! head -20 "$src_file" | grep -q '^name:' || ! head -20 "$src_file" | grep -q '^description:'; then
    printf "✗ %-16s frontmatter 缺 name 或 description\n" "$s"
    failed=$((failed + 1))
    continue
  fi

  # 不存在 → 新增
  if [ ! -f "$dst_file" ]; then
    printf "＋ %-16s 新增" "$s"
    if [ "$DRY" -eq 0 ]; then
      mkdir -p "$dst_dir" && cp "$src_file" "$dst_file"
    fi
    echo
    changed=$((changed + 1))
    continue
  fi

  # 内容一致 → 跳过
  if cmp -s "$src_file" "$dst_file"; then
    printf "= %-16s 已是最新\n" "$s"
    skipped=$((skipped + 1))
    continue
  fi

  # 有差异 → 备份后覆盖
  printf "↑ %-16s 有更新" "$s"
  if [ "$DRY" -eq 0 ]; then
    cp "$dst_file" "$dst_file.bak_$(date +%Y%m%d_%H%M%S)"
    cp "$src_file" "$dst_file"
    printf "（旧版已备份）"
  fi
  echo
  changed=$((changed + 1))
done

# ---------- 结果 ----------
echo
echo "─────────────────────────────"
printf "改动 %d / 跳过 %d / 失败 %d\n" "$changed" "$skipped" "$failed"

if [ "$failed" -gt 0 ]; then
  echo "✗ 有失败项，先修好再同步"
  exit 1
fi
if [ "$DRY" -eq 1 ]; then
  echo "（dry-run，未写入）"
elif [ "$changed" -eq 0 ]; then
  echo "全部已是最新，无需同步"
else
  echo
  echo "✓ 已同步。**新开一个会话才生效**——技能清单在会话启动时生成。"
fi
