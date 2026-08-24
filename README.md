# Perpetuum

> 把长期目标组织成一组可持续运行、可观察、可干预的 Story 看板。

Perpetuum 是一个 Agent Skill。它用轻量本地 Runner 按项目的 cron 计划创建临时 Project Supervisor，再由 Project Supervisor 通过 `cc-use` 调度一条 Story 工作链。每条工作链必有 Executor，Validator 和 Explorer 则按项目的队伍契约选择启用。长期 Goal、队伍契约、Story、人类输入、问题、管控异常和日报都保存在项目自己的 Harness 中；本地前端直接聚合这些文件，不引入数据库或云服务。

完整的 Agent 使用说明见 [SKILL.md](skills/perpetuum/SKILL.md)。

## 架构

```text
Local Runner / Frontend Service
        ├── Project Supervisor A
        │       └── Story Supervisor
        │               ├── Executor（必选）
        │               ├── Validator（可选）
        │               └── Explorer（可选）
        ├── Project Supervisor B
        │       └── Story Supervisor → ...
        └── Reporter
```

Runner 只解释 cron、创建交互式 Agent TUI、维护顶层生命周期和提供前端，不判断业务。Agent 之间的上下级调用全部通过 `cc-use` 完成。

## 特点

- 一个实际项目目录对应一套自包含 Harness 和一个 Story 看板。
- 每个项目用 `team.md` 保存用户确认的角色职责、触发条件、调用顺序和完成门槛。
- 每个项目在 `schedule.yaml` 中保存自己的时区和标准五字段 cron。
- 同一项目同时最多运行一张 Story，不同项目可以并行。
- cron 只决定何时允许开始新的 Project 激活，不中断已经运行的 Story。
- Runner 为每个新建的 Project Supervisor 只发送一次启动 Prompt；后续工作由真实结果推动，不按时间重复灌入固定内容。
- Questions 与 Escalations 分别承载业务判断和管控问题，并要求写清完整背景。
- Reporter 独立检查运行状态，即使业务工作链中断也能在日报中暴露。
- 前端同时提供易读运行计划和 Cron 编辑，并在每个项目旁显示预计下次启动时间。
- 前端默认监听 `127.0.0.1:8765`，远端机器可通过 SSH 端口转发查看。
- 无人值守运行期间不自动更新 Codex、Claude Code、模型或认证配置。

## 依赖

- [cc-use](https://github.com/zc277584121/cc-use) 是必需依赖，负责 Agent 上下级之间的交互式 TUI session 管理。
- [MemSearch](https://github.com/zilliztech/memsearch) 是可选依赖，只在初始化时帮助召回项目历史。
- [uv](https://docs.astral.sh/uv/) 管理本地 Python 运行时。

## 使用

通过 [npx skills](https://skills.sh) 安装到支持的 Agent：

```bash
npx skills add zc277584121/perpetuum --all -g
```

安装或同步后需要重新进入 Agent TUI，使新版本 Skill 生效。由 Agent 调用 `perpetuum` Skill 完成项目初始化。

命令入口位于已安装 Skill 的 `scripts/perpetuum`。下面的简写只适用于已把脚本加入 `PATH` 的环境：

```bash
perpetuum start
perpetuum status
perpetuum stop
perpetuum restart
perpetuum project list
perpetuum project schedule <project-id> "*/5 0-5 * * *" --timezone Asia/Shanghai
```

运行时数据默认保存在 `~/.perpetuum/`。源码仓库和运行时 Harness 相互独立。
