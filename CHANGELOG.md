# CHANGELOG

## v0.5 — 2026-11-13

**外部独立 QA 测试结果为 FAIL（1 个 BLOCKER + 4 个次要项），全部修复。**

| 编号 | 级别 | 问题 | 修法 |
|---|---|---|---|
| F1 | **BLOCKER** | `sync.sh` 在 git 里是 `100644`，Linux/macOS 用户 clone 后 `./sync.sh` 直接 `Permission denied`（exit 126） | `git update-index --chmod=+x sync.sh`，并加 CI 断言权限位 |
| F2 | MAJOR | README 声称的实测数据不可复现——仓库里没有 `verify.py` / `accountant.py` / 证据 | 新增 `examples/cli-ledger/`：完整代码 + `verify.py` + `mutation_test.py` + 原始证据，**并已实测在仓库目录下能跑出 20/20** |
| F3 | MINOR | `encode-lessons` 的触发阈值自相矛盾（描述写"第二次"，正文写"第 3 次"） | 统一为「第三次」 |
| F4 | MINOR | CHANGELOG 引用了仓库里不存在的 `archive/skills-superseded/` | 改为明确说明该目录只在维护者本机 |
| F5 | MINOR | `examples/` 落后于当前模板，且差距清单不全 | 新增 `cli-ledger/README.md`，把 5 项差距全部列清（含之前漏掉的 Phase D 和 DELIVERY.md） |

**新增 `.github/workflows/ci.yml`**，防这五类问题回归：

- `sync.sh` 权限位必须是 `100755`
- `shellcheck`
- 五个 SKILL.md frontmatter 完整且 `name` 与目录名一致
- 无机器特定路径（`C://`、`/Users/xxx/`、`/home/xxx/`），但放过 `~/` 安装路径
- 无垃圾/敏感文件
- 安装到隔离 `HOME` 并验证幂等
- **示例必须真的跑出 20/20**（否则 README 的声称失效）

## v0.4 — 2026-11-10

- README 补「WorkBuddy 用户注意：改完要同步」：项目级目录在这个环境里不会被扫描，只认用户级
- 新增 `sync.sh`：项目级（源）→ 用户级（安装副本），支持 `--dry-run`，有更新时自动备份
- 新增 `CHANGELOG.md`、`ATTRIBUTION.md`

## v0.3 — 2026-11-09

**新增追问机制**（`recipe` 增加一节，五小节）

- 四条判据定义"清楚"：有数字 / 有明确边界 / 有可查真值来源 / 有可观测行为
- 四把刀：逼数字（永远第一）→ 逼边界 → 逼反例 → 逼取舍
- 停止条件：满足判据就停；四把刀都试过还模糊 → 标【AI 假设】，**不无限追问**
- 覆盖检查：8 问后对着菜谱 5 个范围决策栏逐格看，空格要么追问要么标假设
- 追问记录：避免同一件事问两遍

**人工介入点从 2 个收到 1 个**

- 原来「复述确认」和 `deliver` 的「G1 硬停」会就同一个假设问两遍
- 改法：假设在复述时**逐条列出、一次确认**；G1 降级为**机械格式检查**
- 新增**自动区间声明**：「范围已锁定，接下来不再打扰你」
- `verify-app` 里"看不出来的才问"改成「不问人，按最保守假设做并记一行」

## v0.2 — 2026-11-09

**新增 `deliver`（入口 / 编排）**

- 够格判断（四条标准，命中任一条才启动）——防小任务被重流程拖慢
- 分两档：轻档（做→验→打勾）、重档（问→拆→做→验→打勾）
- 四道闸门 G1–G4，都只做检查、不问人
- 交付时必须写 `DELIVERY.md`，作为"流程真的跑过"的证据

**清理**

- 归档两个被取代的旧 skill（`dual-agent-loop`、`requirement-interrogation`）到本地 `archive/` 目录——该目录仅存在于维护者本机，**不在本仓库内**
  - `dual-agent-loop`（指向 16 KB 的 PROTOCOL.md v1.0）
  - `requirement-interrogation`（被 `recipe` 取代）

## v0.1 — 2026-11-08

初版四个 skill：

- `recipe` 需求菜谱（8 问 + 菜谱 + 复述 + N/M 打勾）
- `swarm` 并行派活（定标准 → 切域 → 发 → 聚合）
- `verify-app` 装眼睛（生成能驱动应用的验证工具）
- `encode-lessons` 错误变规则

附一次完整运行的产物示例（`examples/`）。
