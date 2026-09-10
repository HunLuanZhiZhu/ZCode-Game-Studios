# CCGS Studio Hooks — 说明文档

本插件把 Claude Code Game Studios 的自动化 hook 集打包成一个 Claude Code 兼容插件，
可在 ZCode（运行受支持的子集）与 Claude Code 插件市场（完整声明）中工作。

> 配套清单：
> - `.claude-plugin/plugin.json` — 插件清单
> - `hooks/hooks.json` — 全部 hook 的事件绑定
> - `hooks/*.sh` — 15 个脚本（2 个守卫包装器 + 13 个实际 hook 逻辑）
> - 仓库根 `.claude-plugin/marketplace.json` — 插件市场登记

---

## 1. 守卫机制（核心前提）

插件会安装在用户机器上，**每个工作区**都会触发。为避免在非 CCGS 项目里误动作，
所有脚本通过两个包装器做"标记文件"守卫：

| 包装器 | 守卫逻辑 | 用于 |
|--------|----------|------|
| `ccgs-guard.sh <script>` | 若工作区根**没有** `.zcode/docs/technical-preferences.md` 标记文件 → `exit 0` 静默跳过；有则 `exec` 实际脚本 | 会拦截/会改动作的 hook（`validate-*`、`log-agent*`、`notify`） |
| `ccgs-context.sh <script>` | 同上先检查标记文件；再把脚本输出的**纯文本**用 Python 包成 `{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":...}}` JSON 注入模型上下文（纯文本 stdout 进不了模型上下文）。无 Python 时退化打印纯文本 | `SessionStart` 类信息型 hook |

**结论**：只有被识别为 CCGS 工作区（存在 `technical-preferences.md`）时，hook 才真正执行；
其它项目里全部空跑。这是该插件安全性的关键。

---

## 2. Hook 一览表

下表为 `hooks.json` 中**实际绑定**的 14 个事件处理器（注意数量与清单里写的"12 hooks"不符，见 §6）。

| # | 事件 | matcher | 脚本 | 作用 | 退出码 | 守卫 |
|---|------|---------|------|------|--------|------|
| 1 | SessionStart | （空） | `session-start.sh` | 输出会话上下文 | 0 | ccgs-context |
| 2 | SessionStart | （空） | `detect-gaps.sh` | 检测文档缺口并给建议 | 0 | ccgs-context |
| 3 | SessionStart | `compact` | `post-compact.sh` | 压缩后提示恢复状态 ⚠️见 §6 | 0 | ccgs-context |
| 4 | PreToolUse | `Bash\|Read` | `validate-dangerous.sh` | 拦截危险命令/密钥读取 | 2=拒绝 | ccgs-guard |
| 5 | PreToolUse | `Bash` | `validate-commit.sh` | 提交前校验（设计文档/GDD/JSON/硬编码） | 2=阻断 | ccgs-guard |
| 6 | PreToolUse | `Bash` | `validate-push.sh` | 推送到受保护分支提醒 | 2=可阻断 | ccgs-guard |
| 7 | PreToolUse | `Agent\|Task` | `log-agent.sh` | 记录 agent 调用审计 | 0 | ccgs-guard |
| 8 | PostToolUse | `Write\|Edit` | `validate-assets.sh` | 资产文件命名/JSON 校验 | 1=阻断* | ccgs-guard |
| 9 | PostToolUse | `Write\|Edit` | `validate-skill-change.sh` | skill 改动提醒跑测试 | 0 | ccgs-guard |
| 10 | PostToolUse | `Agent\|Task` | `log-agent-stop.sh` | 记录 agent 完成审计 | 0 | ccgs-guard |
| 11 | PermissionRequest | （空） | `notify.sh` | Windows 气泡通知提醒用户 | 0 | ccgs-guard |
| 12 | Notification | （空） | `notify.sh` | 同上（ZCode 忽略此事件，仅 CC 触发） | 0 | ccgs-guard |
| 13 | PreCompact | （空） | `pre-compact.sh` | 压缩前 dump 会话状态 | 0 | ccgs-guard |
| 14 | Stop | （空） | `session-stop.sh` | 会话结束归档状态与提交 | 0 | ccgs-guard |

> \* `validate-assets.sh` 声明 `exit 1` 为"阻断错误"，但 `PostToolUse` 在多数宿主下**无法真正阻止
> 已发生的写入**（工具已经执行完）。它的退出码实际只起到"报错/日志"作用。真正能拦截的只有
> `PreToolUse` 事件（exit 2）。详见 §5。

---

## 3. 逐个 hook 详解

### 3.1 `session-start.sh`（事件 SessionStart）
会话开始时输出项目上下文，经 `ccgs-context.sh` 注入模型：
- 当前 git 分支 + 最近 5 条提交
- 活跃 sprint（`production/sprints/sprint-*.md` 最新一个）、活跃 milestone
- 未解决 BUG 数（`tests/playtest`、`production` 下 `BUG-*.md`）
- `src/` 中 `TODO`/`FIXME` 数量
- 若 `production/session-state/active.md` 存在，预览末尾 20 行，提示恢复上下文

### 3.2 `detect-gaps.sh`（事件 SessionStart）
检测"代码/原型存在但文档缺失"的缺口：
1. **全新项目判定**：未配置引擎 + 无 `design/gdd/game-concept.md` + `src/` 无源码 → 提示运行 `/start`
2. **代码多设计少**：`src/` 源文件 >50 且 `design/gdd/*.md` <5 → 建议 `/reverse-document` 或 `/project-stage-detect`
3. **原型无文档**：`prototypes/*` 子目录缺 `README.md`/`CONCEPT.md` → 建议补文档
4. **核心系统无架构**：有 `src/core` 或 `src/engine` 但无 `docs/architecture/`（或 ADR <3）→ 建议 `/architecture-decision`
5. **玩法系统无设计稿**：`src/gameplay/<sys>/` 含 ≥5 文件但缺 `design/gdd/<sys>-system.md` → 建议补 GDD
6. **无生产计划**：源码 >100 但无 `production/sprints`、`production/milestones` → 建议 `/sprint-plan`
全程 Windows Git Bash 兼容（`grep -E` 而非 `-P`）。

### 3.3 `post-compact.sh`（绑定在 SessionStart/matcher=compact，⚠️见 §6）
压缩后提示从 `production/session-state/active.md` 恢复工作上下文（含任务、决策、进行中文件、待决问题）。

### 3.4 `validate-dangerous.sh`（事件 PreToolUse，matcher `Bash|Read`）
安全护栏，命中即 `exit 2` 拒绝（`stderr` 显示原因）：
- **Read**：路径匹配 `*/.env`、`*.env`、`*.env.*` → 拒绝读取密钥文件
- **Bash** 拦截：`rm -rf`（任意 `-r/-f` 组合）、`git push --force`/`-f`、`git reset --hard`、`git clean -f`、`sudo`、`chmod 777`、重定向或 `cat`/`type` 读取 `.env`
- 与 `.zcode/settings.json` 的 `permissions.deny` 列表保持一致（双保险）。

### 3.5 `validate-commit.sh`（事件 PreToolUse，matcher `Bash`）
仅处理 `git commit`，仅校验已 `git add` 的文件：
- **设计文档**：`design/gdd/*.md` 缺必需章节（Overview / Player Fantasy / Detailed / Formulas / Edge Cases / Dependencies / Tuning Knobs / Acceptance Criteria）→ 警告（不阻断）
- **JSON 数据**：`assets/data/*.json` 非法 JSON → `exit 2` 阻断
- **硬编码数值**：`src/gameplay/` 中出现 `damage|health|speed|... = 数字` → 警告（建议抽到数据文件）
- **TODO 无 owner**：`src/` 中 `TODO|FIXME|HACK` 未带 `(name)` 标签 → 警告
- 警告走 `stderr` 非阻断；JSON 非法才 `exit 2` 阻断。

### 3.6 `validate-push.sh`（事件 PreToolUse，matcher `Bash`）
仅处理 `git push`。若推到受保护分支（`develop`/`main`/`master`，按当前分支或命令中显式分支名判断）→
输出提醒"确保构建/单测通过、无 S1/S2 bug"，**默认放行**（`exit 0`）。脚本中已留 `exit 2` 阻断写法，按需取消注释即可改为强制拦截。

### 3.7 `log-agent.sh`（事件 PreToolUse，matcher `Agent|Task`）
记录 agent 调用审计：解析 agent 名称（兼容 CC 的 `agent_type` 与 ZCode 的 `tool_input.subagent_type`），
追加 `production/session-logs/agent-audit.log`：`时间戳 | Agent invoked: <name>`。非阻断。

### 3.8 `validate-assets.sh`（事件 PostToolUse，matcher `Write|Edit`）
仅检查写入 `assets/` 下的文件：
- **命名规范**（警告，不阻断）：文件名含大写/空格/连字符 → 提示改为小写+下划线
- **JSON 合法性**（声明 `exit 1` 阻断）：`assets/data/*.json` 非法 JSON → 报错
- 见 §2 脚注与 §5：PostToolUse 的退出码在多数宿主下不真正阻止写入。

### 3.9 `validate-skill-change.sh`（事件 PostToolUse，matcher `Write|Edit`）
仅当写入/编辑 `.zcode/skills/` 下文件时，提醒运行 `/skill-test static <skill-name>` 做结构合规校验。纯提醒，非阻断。

### 3.10 `log-agent-stop.sh`（事件 PostToolUse，matcher `Agent|Task`）
与 3.7 对应，记录 agent 完成：`时间戳 | Agent completed: <name>` 追加到同一 `agent-audit.log`。非阻断。

### 3.11 `notify.sh`（事件 PermissionRequest / Notification）
解析通知消息，去重（同一条 10 秒内只弹一次），用 PowerShell 弹 Windows 气泡通知（toast）提醒用户"ZCode 需要你关注"。
- `PermissionRequest` 下：ZCode 与 CC 都会触发
- `Notification` 下：`hooks.json` 注明 ZCode 忽略此事件，仅 CC 触发

### 3.12 `pre-compact.sh`（事件 PreCompact）
压缩前把关键状态 dump 进对话（确保压缩摘要不丢）：
- `production/session-state/active.md` 全文（>100 行截断）
- git 工作树改动（未暂存/已暂存/未跟踪文件清单）
- 设计文档中的 WIP 标记（`TODO|WIP|PLACEHOLDER|[TO BE|[TBD]`）
- 记入 `production/session-logs/compaction-log.txt`

### 3.13 `session-stop.sh`（事件 Stop）
会话结束时归档：
- 把 `production/session-state/active.md` 追加进 `production/session-logs/session-log.md`（**只归档不删除**，供多会话恢复）
- 记录近 8 小时的提交与未提交改动

---

## 4. 退出码约定

| 退出码 | 含义 | 生效范围 |
|--------|------|----------|
| 0 | 通过 / 仅信息或警告 | 全部事件 |
| 1 | `validate-assets.sh` 声明的"阻断错误" | PostToolUse 下实际不阻止写入（见 §5） |
| 2 | 拒绝 / 阻断 | 仅 `PreToolUse` 真正拦截工具调用 |

---

## 5. ZCode 与 Claude Code 的兼容差异

**是的，ZCode 支持的 hook 事件比 Claude Code 少。** 据 ZCode 官方 hook 规范，ZCode 只支持
**恰好 7 个事件**：

`SessionStart` · `UserPromptSubmit` · `PreToolUse` · `PermissionRequest` · `PostToolUse` · `PostToolUseFailure` · `Stop`

Claude Code 除此之外还支持（与本插件相关或常见）：`Notification` · `PreCompact` · `PostCompact` ·
`SubagentStart` · `SubagentStop` 等。所以本插件里：

| 本插件用到的事件 | ZCode 支持？ | 触发情况 |
|---|---|---|
| `SessionStart`（含 `compact` matcher） | ✅ | `session-start.sh` / `detect-gaps.sh` 正常；`post-compact.sh` 通过 `compact` matcher 在压缩后触发 |
| `PreToolUse` | ✅ | `validate-dangerous/commit/push`、`log-agent` 全部生效 |
| `PostToolUse` | ✅ | `validate-assets`、`validate-skill-change`、`log-agent-stop` 生效 |
| `PermissionRequest` | ✅ | `notify.sh` 弹通知生效 |
| `Stop` | ✅ | `session-stop.sh` 生效 |
| `PreCompact` | ❌ 不支持 | `pre-compact.sh` **在 ZCode 下不触发**（仅 CC 有） |
| `Notification` | ❌ 不支持 | `notify.sh` 的这条**在 ZCode 下不触发**（但 `PermissionRequest` 那条生效，通知仍能弹） |

→ ZCode 实际触发 **12 个处理器**（跨 5 个事件）；Claude Code 跑全部 **14 个**（跨 7 个事件）。
本插件未使用 ZCode 多出的 `UserPromptSubmit`、`PostToolUseFailure`，也不受其影响。

其它兼容点：
- **PostToolUse 无法真正拦截**：`validate-assets.sh` 的 `exit 1` 在工具已执行后无效，
  仅作报错/日志。真正拦截要放 `PreToolUse`（exit 2）。ZCode 与 CC 一致。
- **`Stop` 可请求继续**：ZCode 的 `Stop` hook 可最多请求继续 3 次（CC 无此语义）；
  `session-stop.sh` 当前只做归档，没用到该能力。
- **变量**：ZCode 提供 `${CLAUDE_PLUGIN_ROOT}` / `${ZCODE_PLUGIN_ROOT}` 兼容变量，指向插件根目录。
- **命令类型**：`command` 类型 ZCode 与 CC 通用；本插件统一用 `bash "<root>/hooks/...sh"` 调用，规避可执行位问题。
- **JSON 输出格式（待实测）**：`ccgs-context.sh` 把上下文包成 CC 格式
  `{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":...}}`。
  ZCode 文档只说"stdout 解析为 JSON，`additionalContext` 注入对话"，未明确是否接受
  `hookSpecificOutput` 嵌套包装；若 ZCode 期望顶层 `{ "additionalContext": "..." }`，该包装会
  校验失败被丢弃。建议在 ZCode 实测一次 `session-start.sh` 的注入是否真的进模型上下文。

---

## 6. 已知问题 / 待确认（已据 ZCode 官方规范核实）

1. **"12 hooks" 口径**：`plugin.json` 描述写"12 hooks"，而 `hooks.json` 实际声明
   **14 个事件处理器**（13 个不同脚本）。差异来自 2 个仅 CC 支持的事件
   （`PreCompact` 的 `pre-compact.sh`、`Notification` 的 `notify.sh`）。
   12 ≈ ZCode 实际触发的处理器数，14 = CC 全量。建议把口径写清楚（如"14 声明 / 12 在 ZCode 生效"）。
2. **`post-compact.sh` 的绑定是正确做法（非 bug）**：它被放在 `SessionStart` 的
   `matcher:"compact"` 下，因为 ZCode **没有 `PostCompact` 事件**；ZCode 的 `SessionStart`
   在 `compact` matcher 下恰在上下文压缩后触发。所以这是针对 ZCode 的兼容写法，会按预期触发，
   无需改为 `PostCompact`。（之前版本误判它为误绑，已纠正。）
3. **`validate-assets.sh` 的阻断无效**：`PostToolUse` 在工具已执行后无法真正阻止写入，
   其 `exit 1` 仅作报错/日志。需强制拦截非法资产 JSON 应改 `PreToolUse`（exit 2）或在编辑器/CI 侧校验。
4. **`ccgs-context.sh` 的 JSON 包装格式（待实测）**：见 §5 末条。`additionalContext` 注入在
   ZCode 下的 JSON 形状需实测确认，否则 `SessionStart` 上下文可能不进模型上下文。

---

## 7. 安装与验证

**安装（ZCode）**
1. 在 ZCode 客户端打开 **设置 → 插件管理**。
2. 添加/安装本插件（`ccgs-studio-hooks`），来源指向本仓库的 `./ccgs-studio-hooks`。
3. 确保工作区根存在 `.zcode/docs/technical-preferences.md`（CCGS 项目标记），否则所有 hook 空跑。

**安装（Claude Code 市场）**
- 通过仓库根 `.claude-plugin/marketplace.json` 登记的市场安装插件即可，完整事件集生效。

**验证触发**
- 新建一个 CCGS 工作区，开启会话 → 应看到 `session-start.sh` 注入的上下文与 `detect-gaps.sh` 的缺口提示。
- 跑一条 `rm -rf` 或 `git push --force` → `validate-dangerous.sh` / `validate-push.sh` 应拦截或提醒。
- 改一个 `assets/data/*.json` 写成非法 JSON 并提交 → `validate-commit.sh` 应 `exit 2` 阻断。
- 改 `.zcode/skills/xxx/SKILL.md` → `validate-skill-change.sh` 应提醒跑 `/skill-test`。
- 非 CCGS 目录（无 `technical-preferences.md`）下重复上述操作 → 全部应静默跳过（守卫生效）。
