---
name: perpetuum
description: 为一个或多个项目建立、运行和管理长期 Agent 队伍。适用于初始化长期自主工作、按时间窗口持续探索和执行 Task、查看或调整运行状态、处理人类输入，以及生成项目日报。
---

# Perpetuum

Perpetuum 把一个或多个真实项目目录组织成可长期运行的 Agent 队伍。本地 Runner 周期性唤醒具备启动条件的项目，Supervisor 再通过 `cc-use` 逐层调用下级 Agent；长期目标、Task 计划、人类输入、运行状态和日报都保存在项目自己的 Harness 中。

## 依赖

- **必须依赖 [cc-use](https://github.com/zc277584121/cc-use)**：负责所有 Agent 上下级之间的交互式 TUI session 创建、观察、继续对话和关闭。当前 Agent 无法加载 `cc-use` 时，不要建立或启动 Harness；先让用户按 cc-use 仓库的说明安装或修复。Perpetuum 只描述调用意图，不复制 cc-use 的具体命令和参数。
- **可选依赖 [MemSearch](https://github.com/zilliztech/memsearch)**：初始化时用于召回项目历史，减少用户重复说明。不可用时直接检查项目文件并通过对话补齐信息，不影响核心运行。

## 核心名词

- **Project**：一个需要长期推进的真实项目目录。
- **Harness**：Perpetuum 为 Project 保存的长期目标、计划、人类输入、报告和运行状态，默认位于 `~/.perpetuum/projects/<project-id>/`；它不是项目源码的副本。
- **Runner**：非 Agent 的本地后台服务，负责读取时间窗口、启动顶层 Agent、维护状态并提供前端，不做业务判断。
- **Supervisor**：只负责调度和管控的 Agent。调用链为 Root Supervisor → Project Supervisor → Task Supervisor。
- **Task**：唯一的业务工作粒度。每个 Task 由 Explorer 选择、Executor 执行、Validator 独立验证。
- **Reporter**：与 Root 工作链路独立的日报 Agent；即使业务链路异常，也会检查并报告运行情况。
- **session**：一个由 tmux 承载的交互式 Agent TUI 会话。每个父节点只管理自己创建的直属 session。
- **Playbook**：某个角色的软性工作指南，说明职责、判断方法、向下级组织 Prompt 时应包含的信息和结束条件；它不是必须逐字发送的固定 Prompt。

完整的层级、职责和调用方向见 [architecture.md](references/architecture.md)。

## 按当前任务读取参考

| 当前任务 | 必读参考 |
|---|---|
| 理解整体结构或职责边界 | [architecture.md](references/architecture.md) |
| 初始化或注册项目 | [setup.md](references/setup.md)，再读 [architecture.md](references/architecture.md) 和 [runtime.md](references/runtime.md) |
| 启动、停止、查看、暂停、恢复或调整时间窗口 | [runtime.md](references/runtime.md) |
| 处理人类指令、业务问题、管控异常或日报 | [human-communication.md](references/human-communication.md) |
| 调整 Root Supervisor | [root-supervisor.md](references/playbooks/root-supervisor.md) |
| 调整 Project Supervisor | [project-supervisor.md](references/playbooks/project-supervisor.md) |
| 调整 Task 调度或 session 复用策略 | [task-supervisor.md](references/playbooks/task-supervisor.md) |
| 调整 Task 的发现、执行或验证 | [explorer.md](references/playbooks/explorer.md)、[executor.md](references/playbooks/executor.md)、[validator.md](references/playbooks/validator.md) |
| 生成或检查日报 | [reporter.md](references/playbooks/reporter.md) |

只读取与当前任务相关的参考；不要把全部参考文档无差别加载进上下文。

## 核心规则

1. 初始化时先检查项目和可用历史，在对话中形成完整契约。信息不足、相互矛盾或会改变长期行为时，继续向用户确认；只有用户明确确认最终内容后才能建立 Harness。
2. `goal.md` 是长期业务契约；`plan.md` 是 Explorer 维护的 Task 列表；`history.md` 只保存已经验证的业务结论和重要决定。
3. Root 和 Project 层只做管控。Explorer → Executor → Validator 循环只发生在 Task 层。
4. 同一 Project 同时最多运行一个 Task；不同 Project 可以并行，不设置跨项目的全局 Task 数上限。
5. 时间窗口只决定能否开始新 Task。已经开始的 Task 可以跨出时间窗口继续完成。
6. 需要人类做业务选择时写入 `questions.md`；环境、权限、认证、进程、配额、磁盘、网络或基础设施问题写入 `escalations.md`。两者都必须写清背景、影响、证据、建议和人类需要做的最小决定。
7. 无人值守运行期间，不自动更新 Codex、Claude Code、模型或认证配置。遇到更新提示时跳过并继续；因此无法继续时记录管控异常。
8. Runner 对每个新建的 Root 或 Reporter session 只发送一次中文启动 Prompt。session 存活期间不按时间重复注入 Prompt，也不因为暂时没有屏幕变化而发送固定的“继续”指令。
9. 父 Supervisor 根据角色 Playbook、当前 Harness 和本次运行时上下文组织下级 Prompt。只有新建 session、收到实际结果、Validator 退回、人类补充决定或外部条件发生实质变化时，才发送新的 Prompt。
10. Explorer 默认使用全新 session，Validator 与 Executor 保持独立；Executor 和 Validator 是否在后续轮次复用，由 Task Supervisor 根据任务上下文决定。详细策略只在 [task-supervisor.md](references/playbooks/task-supervisor.md) 维护。
11. `project.yaml` 只记录 Agent 类型。Runner 通过 `PATH` 解析真实可执行文件并管理 Root 与 Reporter 的启动参数；下级 Agent 的运行细节由 cc-use 管理，不依赖 shell alias，也不写入项目配置。

## 脚本入口

所有运行时操作只使用本 Skill 的 `scripts/perpetuum`。默认用 Skill 安装目录下的绝对路径调用；只有用户明确把它加入 `PATH` 后，才使用 `perpetuum` 简写。

初始化必须遵循 [setup.md](references/setup.md) 的确认流程。查看命令、运行目录、状态、调度和前端行为时读取 [runtime.md](references/runtime.md)。
