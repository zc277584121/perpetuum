# Perpetuum

> 把长期目标组织成一支可持续运行、可观察、可干预的 Agent 队伍。

Perpetuum 是一个 Agent Skill。它用轻量本地 Runner 唤醒分层 Supervisor，并在项目最底层运行“探索 → 执行 → 验证”循环。长期目标、任务计划、人类指令、问题、管控异常和日报都落在文件里；本地前端只聚合这些文件，不引入数据库或云服务。

这里的 Supervisor 是负责调度的管理 Agent，Task 是一次可以执行和验证的业务工作，Harness 是某个项目保存在 `~/.perpetuum/projects/<project-id>/` 下的长期运行资料。

完整的 Agent 使用说明见 [SKILL.md](skills/perpetuum/SKILL.md)。

## 架构

```text
Local Runner / Frontend Service
        ├── Root Supervisor
        │       └── Project Supervisor
        │               └── Task Supervisor
        │                       ├── Explorer
        │                       ├── Executor
        │                       └── Validator
        └── Reporter
```

Runner 只处理时间窗口、进程、HTTP 服务和顶层触发；Root 与 Project Supervisor 只处理管控；Task Supervisor 负责一次 Task 选择、执行和验证循环。所有 Agent 上下级调用都通过 `cc-use` 完成。

## 特点

- 一个实际项目目录对应一套自包含 Harness。
- Explorer 持续维护唯一的 Task 列表。
- 同一项目同时最多运行一个 Task，不同项目可以并行。
- 时间窗口只限制新 Task 开始，已开始的 Task 可以跨出窗口完成。
- 每个新 session 只接收一次启动 Prompt；角色根据 Playbook 和当前上下文组织后续 Prompt，不按时间重复灌入固定内容。
- Questions 与 Escalations 分别承载业务判断和管控问题，并要求写清完整背景。
- Reporter 独立检查运行状态，即使主工作链路中断也能在日报中暴露。
- 前端默认监听 `127.0.0.1:8765`，远端机器可通过 SSH 端口转发查看。
- 无人值守运行期间不自动更新 Codex、Claude Code、模型或认证配置。

## 依赖

- [cc-use](https://github.com/zc277584121/cc-use) 是必需依赖，负责 Agent 上下级之间的交互式 TUI session 管理。请先按其仓库说明完成安装。
- [MemSearch](https://github.com/zilliztech/memsearch) 是可选依赖，只在初始化时帮助召回项目历史；未安装不影响 Perpetuum 的核心运行。

## 使用

通过 [npx skills](https://skills.sh) 安装到支持的 Agent：

```bash
npx skills add zc277584121/perpetuum --all -g
```

安装或同步后需要重新进入 Agent TUI，使新版本 Skill 生效。由 Agent 调用 `perpetuum` Skill 完成项目初始化。

供 Agent 和维护者使用的命令入口位于已安装 Skill 的 `scripts/perpetuum`。直接调用时应先找到实际安装目录并使用绝对路径，例如：

```bash
<skill-directory>/scripts/perpetuum status
```

下面的简写仅适用于已经把该脚本加入 `PATH` 的环境。常用命令：

```bash
perpetuum start
perpetuum status
perpetuum stop
perpetuum restart
perpetuum project list
perpetuum project window <project-id> 00:00-06:00
```

运行时数据默认保存在 `~/.perpetuum/`。源码仓库和运行时 Harness 相互独立。
