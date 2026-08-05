# Perpetuum

> 把长期目标组织成一支可持续运行、可观察、可干预的 Agent 队伍。

Perpetuum 是一个 Agent Skill。它用轻量本地 Runner 唤醒分层 Supervisor，并在项目最底层运行“探索 → 执行 → 验证”循环。长期目标、任务计划、人类指令、问题、管控异常和日报都落在文件里；本地前端只聚合这些文件，不引入数据库或云服务。

## 架构

```text
Local Runner / Frontend Service
        ↓
Root Supervisor
        ↓
Project Supervisor
        ↓
Task Supervisor
        ├── Explorer
        ├── Executor
        └── Validator
```

Runner 只处理时间资格、进程、HTTP 服务和顶层触发；Root 与 Project Supervisor 只处理管控；Task Supervisor 负责一个具体 Task 的完整闭环。所有 Agent 上下级调用都通过 `cc-use` 完成。

## 特点

- 一个实际项目目录对应一套自包含 Harness。
- Explorer 持续维护唯一的 Task 列表。
- 同一项目同时最多运行一个 Task，不同项目可以并行。
- 时间窗口只限制新 Task 开始，已开始的 Task 可以跨出窗口完成。
- Questions 与 Escalations 分别承载业务判断和管控问题，并要求写清完整背景。
- Reporter 独立检查运行状态，即使主工作链路中断也能在日报中暴露。
- 前端默认监听 `127.0.0.1:8765`，远端机器可通过 SSH 端口转发查看。
- 不自动更新 Codex、Claude Code、Skill、插件或认证配置。

## 使用

通过 `npx skills` 安装到支持的 Agent：

```bash
npx skills add zc277584121/perpetuum --all -g
```

安装或同步后需要重新进入 Agent TUI，使新版本 Skill 生效。由 Agent 调用 `perpetuum` Skill 完成项目初始化。命令入口位于：

```bash
skills/perpetuum/scripts/perpetuum
```

常用命令：

```bash
perpetuum start
perpetuum status
perpetuum stop
perpetuum restart
perpetuum project list
perpetuum project window <project-id> 00:00-06:00
```

运行时数据默认保存在 `~/.perpetuum/`。源码仓库和运行时 Harness 相互独立。
