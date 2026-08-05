---
name: perpetuum
description: 为一个或多个项目建立、运行和管理长期 Agent 队伍。适用于用户希望让 Agent 在每天的时间窗口内持续研究、实现和验证长期目标，或希望查看、暂停、恢复、调整、汇报现有 Perpetuum 项目时；也适用于搭建 Root → Project → Task Supervisor 层级、Explorer → Executor → Validator 循环、本地监控前端和文件化人类介入机制。
---

# Perpetuum

把长期工作组织成由本地 Runner 定时唤醒的 Supervisor 树。所有 Agent 上下级调用通过 `cc-use` 完成；不要复制或硬编码 `cc-use` 的命令和参数。

## 先按意图读取参考

| 用户意图 | 必读参考 |
|---|---|
| 初始化或注册项目 | [setup.md](references/setup.md)、[architecture.md](references/architecture.md)、[runtime.md](references/runtime.md) |
| 启动、停止、查看或调整运行 | [runtime.md](references/runtime.md) |
| 调整 Supervisor 行为 | 对应的 Supervisor、Explorer、Executor 或 Validator 参考 |
| 处理人类指令、问题或管控异常 | [human-communication.md](references/human-communication.md) |
| 生成或检查日报 | [reporter.md](references/reporter.md) |

## 工作原则

1. 把一个实际目录视为一个 Project。
2. 用 `goal.md` 保存长期业务契约；用 `plan.md` 保存 Explorer 维护的 Task 列表。
3. 只在 Task 层运行 Explorer → Executor → Validator。Root 和 Project 层只做管控。
4. 同一 Project 同时最多运行一个 Task；不要设置跨 Project 的全局并发上限。
5. 时间窗口只决定是否可以开始新 Task。已经开始的 Task 允许继续完成。
6. 对无法自行决定的业务问题写入 `questions.md`；对环境、权限、进程和基础设施问题写入 `escalations.md`。两者都必须让脱离现场的人能看懂。
7. 不自动更新 Codex、Claude Code、Skill、插件、模型或认证配置。遇到更新提示时跳过并继续；无法继续时记录管控异常。

## 使用脚本

只使用本 Skill 的单一入口 `scripts/perpetuum` 管理 Runner、项目注册和本地前端。先用绝对路径调用；若用户自行放入 `PATH`，再使用简写 `perpetuum`。

初始化时优先使用 MemSearch 回忆项目历史，再检查项目文件并起草 Harness。MemSearch 结果只是线索；用户确认后的 Harness 文件才是事实来源。

## 参考索引

- [architecture.md](references/architecture.md)：层级、职责和调用方向
- [root-supervisor.md](references/root-supervisor.md)：Root Supervisor
- [project-supervisor.md](references/project-supervisor.md)：Project Supervisor
- [task-supervisor.md](references/task-supervisor.md)：Task Supervisor
- [explorer.md](references/explorer.md)：Task 发现与排序
- [executor.md](references/executor.md)：Task 执行
- [validator.md](references/validator.md)：独立验证
- [reporter.md](references/reporter.md)：逐项目日报
- [human-communication.md](references/human-communication.md)：Inbox、Questions、Escalations 与人类回复
- [runtime.md](references/runtime.md)：目录、状态、调度、前端和进程生命周期
