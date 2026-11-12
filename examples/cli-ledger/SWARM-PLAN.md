# SWARM-PLAN：命令行记账工具

> 对应 `swarm/SKILL.md` 的 Phase A → D。

## Phase A：切

### A1. done predicate（一句话，可判定）

| 块 | done predicate |
|---|---|
| **A · store（数据层）** | `python run/store/test_store.py` 退出码 0；临时账本中 3 笔的余额等于手算值（精确到 0.01）；非法金额抛 `ValueError`；另起实例能读到旧数据。证据：`run/store/EVIDENCE.txt`。 |
| **B · todo（命令层）** | `python run/todo/ledger_cli.py --help` 退出码 0 且列出 `add/balance/list`；用临时 `--data` 连续执行 add×3 → list → balance，输出与退出码符合预期；非法输入退出码 2 且 stderr 含「错误」。证据：`run/todo/EVIDENCE.txt`。 |
| **C · 收口（集成 / 无主需求）** | 根目录 `python accountant.py --help` / add / balance / list 全部走通；`verify.py` 全绿；变异版本必须 FAIL。证据：`evidence/verify_*.txt`、`evidence/mutation_test.txt`。 |

### A2. 形状

**partition（切片）**，不是 race。
声明选法：不适用（没有多版本竞争）。

**依赖说明（重要）**：A 与 B 不是零依赖。B 的 CLI 要调用 A 的存储 API。
处置：**接口契约先行冻结**（见下），B 只按契约编程，不读 A 的实现；A、B 各自目录，物理上不共享文件。
这仍然是"共享契约"，不是"共享状态"。此偏离已记入 `PROBLEMS.md`。

### A3. 切域 + 独立输出目录

```
run/store/   ← A：数据模型 + JSONL 持久化 + 余额计算
run/todo/    ← B：argparse 命令层 + 输出格式 + 错误处理
（root）     ← C：收口、无主需求、verify.py、README
```

#### 冻结接口契约（B 按此编码）

```python
# run/store/ledger_store.py
DEFAULT_DATA_PATH: pathlib.Path

def parse_amount(raw) -> Decimal        # 非法或 <=0 抛 ValueError
class Ledger:
    def __init__(self, path=DEFAULT_DATA_PATH)
    def add(self, amount, category="未分类", note="", when=None, income=False) -> dict
    def entries(self, limit=None, month=None) -> list[dict]   # 最新在前
    def balance(self) -> dict  # {"total_income": Decimal, "total_expense": Decimal, "balance": Decimal, "count": int}
```

账本行格式（JSONL，一行一笔）：

```json
{"id":"...","ts":"2026-11-08T20:00:00","amount":"-35.50","category":"餐饮","note":"午饭"}
```

### A4. 回查：每条需求归谁？

| 需求 / 原话 | 归属 | 说明 |
|---|---|---|
| 做一个命令行记账工具 | B + C | B 提供 CLI；C 做根入口 |
| 能记一笔 | A（写入）+ B（命令） | 写入正确性归 A，参数与回显归 B |
| 查余额 | A（计算）+ B（展示） | 数值正确性归 A，格式归 B |
| 看记录 | A（读取/排序）+ B（展示/筛选参数） | `--month` 过滤逻辑归 A，参数解析归 B |
| 做得实用点 | **部分无主** | 见下 |
| 零依赖 / help 可读 | B | 命令层 |
| 中文错误 + 非 0 退出码 | B | 命令层 |
| 数据不丢 / 重复运行可读 | A | 持久化 + fsync |
| 数据路径可配置 | B（`--data`）+ A（构造器） | 契约已含 |
| 默认数据路径 | **无主** | 归 C |
| 根入口 / README / 验证脚本 | **无主** | 归 C |
| 按月份筛选（Q2） | A + B | 已覆盖 |
| 收入记录（待定项） | A + B | `--income`，已覆盖 |

**无主条目（洞）**：默认数据路径、根入口、README、verify 脚本、端到端证据目录 → **单独成块 C**。

> 若不单独设 C，这些"不归属任何技术模块"的需求会掉出去——正是 skill 里「符文/镶嵌」教训的同类问题。

---

## Phase B：发

### 本环境限制（如实记录）

真实 swarm 应在**同一个响应**里并发派 2 个 subagent。本次运行是**单进程** `opencode run`，无法真并行。

因此实际执行方式：**A → B → C 串行**。
所以这次**不能验证"并行省 35%"的收益**；只能验证切分是否干净、契约是否够用、聚合规则是否可执行。
这是测试环境限制，不是 skill 缺陷。

### 每个 worker brief 的自包含五项（真实派发时应原样使用）

**A · store**

1. 目标：实现账本数据层，保证写入落盘、读取有序、余额精确。
2. 范围：只做 `run/store/ledger_store.py` 与 `run/store/test_store.py`；不做 CLI、不做帮助文本、不碰根目录。
3. 怎么验：`python run/store/test_store.py` 全绿，证据写入 `run/store/EVIDENCE.txt`。
4. 报告：`PASS / ISSUES / BLOCKED` + 证据路径 + 关键输出。
5. 目录：`run/store/`，不许越界。

**B · todo**

1. 目标：实现 `add / balance / list` 三个命令，输出可读、错误友好。
2. 范围：只做 `run/todo/ledger_cli.py` 与 `run/todo/test_cli.py`；按冻结契约调用 store，不读 A 的实现；不碰根目录。
3. 怎么验：`python run/todo/test_cli.py` 全绿，证据写入 `run/todo/EVIDENCE.txt`。
4. 报告：`PASS / ISSUES / BLOCKED` + 证据路径 + 关键输出。
5. 目录：`run/todo/`，不许越界。

**C · 收口**

1. 目标：把 A、B 接成用户真正会敲的命令，并补齐无主需求。
2. 范围：`accountant.py`、`README.md`、`verify.py`、`mutation_test.py`、`evidence/`；不改 A/B 的内部实现（发现 bug 先报告）。
3. 怎么验：`python verify.py` 全绿；变异测试必须 FAIL。
4. 报告：`PASS / ISSUES / BLOCKED` + 证据路径。
5. 目录：仓库根 + `evidence/`。

### 统一报告格式

```
PASS      全部达成，附证据位置
ISSUES    有问题，列出能证明的全部问题（不是只报第一个）
BLOCKED   做不了，说明卡在哪
```

---

## Phase C：收（聚合规则）

1. 没记录证据的块 → 丢弃重跑一次。
2. 第二次还拿不出证据 → 记 **gap**，gap 不算 pass。
3. 覆盖检查（partition）：A、B、C 三块都必须有结果。
4. 掉线处理：本次若某块失败，用其余块继续，但报告必须写明缺哪块。

### 实际聚合结果

| 任务 | 结果 | 证据 | 备注 |
|---|---|---|---|
| A · store | PASS | `run/store/EVIDENCE.txt` | 单测全绿；余额精确到分 |
| B · todo | PASS | `run/todo/EVIDENCE.txt` | 3 命令可用；非法输入退出 2 |
| C · 收口 | PASS | `evidence/verify_*.txt`、`evidence/mutation_test.txt` | 端到端全绿；变异必须 FAIL |

**完成：3/3，0 个 gap。**

> 注：每块的证据是**跑完才写**的，不是先写"PASS"再补。见各 EVIDENCE 文件的时间戳与实际命令输出。
