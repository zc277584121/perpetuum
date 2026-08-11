# 运行时

## 目录

```text
~/.perpetuum/
├── activation.yaml
├── runner/
│   ├── state.json
│   ├── events.log
│   └── runs/
│       └── <run-id>/
│           ├── dispatch.json
│           └── receipt.json
└── projects/
    └── <project-id>/
        ├── project.yaml
        ├── goal.md
        ├── plan.md
        ├── history.md
        ├── inbox.md
        ├── questions.md
        ├── escalations.md
        ├── reports/
        │   ├── latest.md
        │   └── YYYY-MM-DD.md
        └── runtime/
            ├── state.json
            └── events.log
```

`~/.perpetuum/` 是默认运行时目录。每个 `projects/<project-id>/` 是一个 Project 的 Harness；它只保存长期运行资料，不复制项目源码。

`runner/runs/` 保存当前顶层调用的临时交接文件：`dispatch.json` 是 Runner 交给 Root 或 Reporter 的本次任务说明，`receipt.json` 是顶层 Agent 完成清理后写回的结果。Runner 处理完成后会删除对应的临时目录，因此它们不是长期业务记录。

`activation.yaml` 和 `project.yaml` 使用 JSON 兼容的 YAML 子集，因此文件既是有效 YAML，也能由无第三方依赖的 Runner 直接读取。不要在其中加入 YAML 专有语法。

`project.yaml` 的 `agent` 只记录 `kind`，值为 `codex` 或 `claude`。项目配置不保存启动命令和宿主机权限参数。

## 激活配置

全局配置包含时区、检查间隔、日报时间、前端监听地址和各项目时间窗口。默认每 30 分钟检查一次。窗口支持跨午夜；`00:00-24:00` 表示全天。

Runner 只判断项目是否位于允许启动新 Task 的时间窗口内，或是否收到“立即运行”请求；它不读取 Goal，也不决定具体业务。Runner 汇总本次符合条件的项目后，始终从 Root 向下调用。

时间窗口只限制新 Task 的开始。窗口关闭时不打断正在执行的 Task，也不设置固定 Task 时长。

## 状态

`runner/state.json` 记录服务 PID、最近检查、下次检查、Root/Reporter session 和最后错误。项目 `runtime/state.json` 记录当前状态：

- `idle`：当前没有 Task 在运行；
- `working`：正在执行一个 Task；
- `waiting_human`：需要人类完成业务判断；
- `control_blocked`：环境、权限、认证、进程或基础设施阻止继续运行；
- `paused`：人类已暂停该项目的新 Task。

项目状态同时保存当前 Task、最近活动时间和活动 session。

`events.log` 使用一行一个 JSON 事件，只保存运行流水。完成 Task 的可信结论写入 `history.md`，不要把每次轮询或每轮对话都写入 History。

状态文件需要先写临时文件再原子替换。日志使用追加写。Runner 的临时 `dispatch.json` 和 `receipt.json` 完成后清理，不成为业务事实来源。

## 进程与 Session

单一命令入口如下。`<skill-directory>` 表示当前安装的 Perpetuum Skill 目录；只有脚本已加入 `PATH` 时才省略前缀。

```text
<skill-directory>/scripts/perpetuum start
<skill-directory>/scripts/perpetuum stop
<skill-directory>/scripts/perpetuum restart
<skill-directory>/scripts/perpetuum status
```

`start` 启动一个轻量本地后台进程，同时运行 Scheduler、HTTP API 和前端。Runner 直接管理 Root 与 Reporter session；其他 session 由各自父 Supervisor 通过 `cc-use` 管理。所有 session 名必须唯一。

Runner 为每个新建的 Root 或 Reporter session 发送一次中文启动 Prompt，主要提供本次 `dispatch.json`、角色 Playbook、`receipt.json` 路径和最小的生命周期边界。启动后，Runner 不再按时间向仍然存活的 session 注入 Prompt。长时间没有输出时保持观察；session 消失且没有回执时记录管控异常。

下级 Prompt 由父 Supervisor 根据 Playbook 和当前上下文组织。新建 session、收到实际结果、验证退回、人类回复或外部条件变化可以触发新的 Prompt；定时轮询和屏幕静默不能单独触发 Prompt。

Runner 通过当前 `PATH` 解析真实可执行文件，并使用参数数组直接启动，不经过 shell alias 或 function。顶层 Codex 使用 `--no-alt-screen --dangerously-bypass-approvals-and-sandbox`，顶层 Claude Code 使用 `--dangerously-skip-permissions`。这些参数只作用于 Runner 直接管理的 Root 与 Reporter；cc-use 独立管理所有下级 Agent 的命令、专用 tmux socket、锁和生命周期。

调用 `start` 前先检查配置的监听地址。若该地址已经提供 Perpetuum API，并且 API 报告的运行时目录与本次 `home` 相同，直接复用现有服务。若属于不同运行时目录，报告冲突并停止；不要假装复用、自动关闭对方或选择备用端口。只有用户明确要求时才执行 `restart`。

Runner 不通过 TUI 屏幕文本判断完成。它为 Root 和 Reporter 提供一次性 `receipt.json` 回执路径，Agent 原子写入结果后，Runner 才回收顶层 session。TUI 屏幕只用于人类观察和软性诊断。

## 前端

默认监听 `127.0.0.1:8765`。前端展示所有项目的 Goal、Plan、History、Inbox、Questions、Escalations、Reports、runtime 状态和 Runner 健康，并允许追加人类指令、回复问题、调整时间窗口、暂停、恢复和立即触发项目。

Linux 服务器上的前端可从本地电脑通过 SSH 转发访问：

```bash
ssh -L 8765:127.0.0.1:8765 <server>
```

然后打开 `http://127.0.0.1:8765`。默认不要监听公网地址，也不要引入数据库或云服务。
