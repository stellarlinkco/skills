# Harness — 长时任务自动驾驶框架

Harness 是一个基于 [Codex Hooks](https://github.com/stellarlinkco/codex/blob/main/docs/hooks.md) 的 Skill，让 AI Agent 能够跨多个 Session 持续执行任务列表，自动恢复进度、处理失败回滚、管理任务依赖。

## 工作原理

Harness 通过 4 个生命周期 Hook 实现"无限循环"：

| Hook 事件 | 脚本 | 作用 |
|---|---|---|
| `Stop` | `harness-stop.py` | Agent 想停止时，检查是否还有未完成任务。有则 **block 停止**，强制继续 |
| `SessionStart` | `harness-sessionstart.py` | 新 Session 启动时，注入当前任务状态摘要作为上下文 |
| `TeammateIdle` | `harness-teammateidle.py` | 多 Agent 协作时，阻止 Teammate 空闲（仍有任务可做） |
| `SubagentStop` | `harness-subagentstop.py` | 阻止子 Agent 在拥有进行中任务时停止 |

此外还有两个工具脚本（非 Hook，由 Agent 主动调用）：

| 脚本 | 作用 |
|---|---|
| `harness-claim.py` | 原子化认领下一个 eligible 任务（加锁 → 选任务 → 设 lease → 写回） |
| `harness-renew.py` | 续租当前任务的 lease（并发模式下防止 lease 过期被回收） |

安全阀：`harness-stop.py` 内置连续 block 计数器（默认 8 次无进展后放行），防止无限循环。

## 前置要求

- **Codex CLI** 已安装并可运行
- **Python 3.10+**（Hook 脚本为纯标准库 Python，无第三方依赖）
- **Git**（任务回滚依赖 `git reset --hard`）

## 安装步骤

### 1. 复制 Skill 文件

将整个 `harness/` 目录放到 Codex 的 skills 路径下：

```bash
# 假设 skills 仓库已 clone 到本地
cp -r harness/ ~/.codex/skills/harness/
```

确认目录结构：

```
~/.codex/skills/harness/
├── SKILL.md                          # Skill 定义（含 YAML frontmatter hooks 声明）
├── README.md                         # 本文档
└── hooks/
    ├── _harness_common.py            # 共享工具库
    ├── harness-stop.py               # Stop hook
    ├── harness-sessionstart.py       # SessionStart hook
    ├── harness-teammateidle.py       # TeammateIdle hook
    ├── harness-subagentstop.py       # SubagentStop hook
    ├── harness-claim.py              # 任务认领（CLI 工具）
    ├── harness-renew.py              # Lease 续租（CLI 工具）
    └── self-reflect-stop.py          # 全部任务完成后触发自省
```

### 2. 配置 `~/.codex/config.toml`

在 `config.toml` 中注册 Hooks。以下是 harness 所需的完整 hook 配置：

```toml
[hooks]

# --- Harness Hooks ---

[[hooks.stop]]
command = "python3 \"$HOME/.codex/skills/harness/hooks/harness-stop.py\""
timeout = 10

[[hooks.session_start]]
command = "python3 \"$HOME/.codex/skills/harness/hooks/harness-sessionstart.py\""
timeout = 10

[[hooks.teammate_idle]]
command = "python3 \"$HOME/.codex/skills/harness/hooks/harness-teammateidle.py\""
timeout = 10

[[hooks.subagent_stop]]
command = "python3 \"$HOME/.codex/skills/harness/hooks/harness-subagentstop.py\""
timeout = 10
```

**可选 — 自省 Hook（任务全部完成后触发反思检查）：**

```toml
[[hooks.stop]]
command = "python3 \"$HOME/.codex/skills/harness/hooks/self-reflect-stop.py\""
timeout = 10
```

> Hook 执行模型：同一事件的多个 Hook 并行执行，互相独立。`harness-stop.py` 和 `self-reflect-stop.py` 分别对 `stop` 事件注册，不会冲突。

### 3. 信任项目目录（如使用项目级配置）

如果你的项目有自己的 `.codex/config.toml`，需要在全局配置中信任该路径：

```toml
[projects."/path/to/your/project"]
trust_level = "trusted"
```

### 4. 验证安装

```bash
# 确认 hook 脚本可执行
python3 ~/.codex/skills/harness/hooks/harness-stop.py <<< '{}'
# 预期输出：空（无 harness-tasks.json 时 hook 为 no-op，退出码 0）

echo $?
# 预期：0
```

## 使用方法

## 懒人使用方法

```
$harness 开发 prd.md 完成之后自检 prd 之后进行测试 修复 测试
```

### 完整使用方法 - 初始化项目

在 Codex 中运行：

```
$harness init /path/to/your/project
```

这会在项目目录下创建：
- `harness-tasks.json` — 结构化任务状态
- `harness-progress.txt` — 追加式执行日志
- `.harness-active` — 激活标记（Hook 生效前提）

### 添加任务

```
$harness add "实现用户认证模块"
```

或直接编辑 `harness-tasks.json`，每个 task 的关键字段：

```json
{
  "id": "task-001",
  "title": "实现用户认证模块",
  "status": "pending",
  "priority": "P0",
  "depends_on": [],
  "attempts": 0,
  "max_attempts": 3,
  "validation": {
    "command": "npm test -- --testPathPattern=auth",
    "timeout_seconds": 300
  },
  "on_failure": {
    "cleanup": null
  }
}
```

> `validation.command` 是必填项。没有验证命令的任务不会被标记为 completed。

### 启动执行

```
$harness run
```

Agent 将进入无限循环：选任务 → 执行 → 验证 → 记录结果 → 选下一个，直到所有任务完成或达到 session 限制。

### 查看状态

```
$harness status
```

### 手动过滤日志

```bash
grep "ERROR" harness-progress.txt                    # 所有错误
grep "STATS" harness-progress.txt                    # 每个 session 的统计摘要
grep "CHECKPOINT" harness-progress.txt               # 所有检查点
grep "SESSION-3" harness-progress.txt                # 第 3 个 session 的全部活动
```

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `HARNESS_STATE_ROOT` | _(自动发现)_ | 指定 `harness-tasks.json` 所在目录 |
| `HARNESS_WORKER_ID` | `hostname:pid` | 并发模式下的 Worker 标识 |
| `HARNESS_LEASE_SECONDS` | `1800` | 任务认领的 lease 时长（秒） |
| `HARNESS_LOCK_TIMEOUT_SECONDS` | `5` | 获取锁的超时时间（秒） |
| `HARNESS_HOOK_LOG` | _(空 = 关闭)_ | 设置后将 hook 执行记录追加到指定文件（调试用） |
| `REFLECT_MAX_ITERATIONS` | `5` | 自省 hook 最大迭代次数（`0` 禁用） |

## 激活标记机制

所有 Hook 的第一步都是检查 `.harness-active` 文件是否存在。不存在时 Hook 是完全的 no-op（退出码 0，无输出）。

- `$harness init` 和 `$harness run` 创建该文件
- 所有任务完成后，`harness-stop.py` 自动删除该文件
- 手动删除该文件可立即停用所有 Hook

## 并发模式

默认为 `exclusive`（独占），同一时刻只有一个 Agent 执行任务。

切换为并发模式：在 `harness-tasks.json` 中设置：

```json
{
  "session_config": {
    "concurrency_mode": "concurrent",
    "max_tasks_per_session": 20,
    "max_sessions": 50
  }
}
```

并发模式要求：
- 每个 Worker 使用独立的 git worktree 或 clone
- 必须设置 `HARNESS_WORKER_ID` 环境变量
- 所有 Worker 指向同一个 `HARNESS_STATE_ROOT`

## 故障恢复

| 错误类型 | 自动恢复策略 |
|---|---|
| `TASK_EXEC` | `git reset --hard` 回滚到任务开始前的 commit，执行 cleanup，重试 |
| `TEST_FAIL` | 回滚后分析测试输出，针对性修复并重试 |
| `TIMEOUT` | kill 进程 + cleanup + 重试 |
| `ENV_SETUP` | 重跑 `harness-init.sh`，仍失败则停止 |
| `CONFIG` | 停止并等待人工修复 |
| `DEPENDENCY` | 标记为 blocked，跳过 |
| `SESSION_TIMEOUT` | 新 session 按恢复矩阵判定（验证通过 → completed，否则 → failed + 回滚） |
| JSON 损坏 | 从 `harness-tasks.json.bak` 恢复，无有效备份则停止 |

## 卸载

1. 删除 `~/.codex/config.toml` 中的 harness 相关 `[[hooks.*]]` 条目
2. 删除 `~/.codex/skills/harness/` 目录
3. 删除项目中的 harness 文件：`harness-tasks.json`、`harness-progress.txt`、`.harness-active`
