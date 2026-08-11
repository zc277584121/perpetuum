# 运行时

## 目录

```text
~/.perpetuum/
├── activation.yaml
├── runner/
│   ├── state.json
│   └── events.log
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

`activation.yaml` 和 `project.yaml` 使用 JSON 兼容的 YAML 子集，因此文件既是有效 YAML，也能由无第三方依赖的 Runner 直接读取。不要在其中加入 YAML 专有语法。

## 激活配置

全局配置包含时区、检查间隔、日报时间、前端监听地址和各项目时间窗口。默认每 30 分钟检查一次。窗口支持跨午夜；`00:00-24:00` 表示全天。

Runner 只判断项目是否具备时间资格，不读取 Goal 或决定具体业务。它先从所有项目中找出满足时间的叶子，再计算需要激活的父路径，最终始终从 Root 向下调用。

时间窗口只限制新 Task 的开始。窗口关闭时不打断正在执行的 Task，也不设置固定 Task 时长。

## 状态

`runner/state.json` 记录服务 PID、最近检查、下次检查、Root/Reporter session 和最后错误。项目 `runtime/state.json` 记录 `idle`、`working`、`waiting_human`、`control_blocked` 或 `paused`，以及当前 Task、最近活动和活动 session。

`events.log` 使用一行一个 JSON 事件，只保存运行流水。完成 Task 的可信结论写入 `history.md`，不要把每次轮询或每轮对话都写入 History。

状态文件需要先写临时文件再原子替换。日志使用追加写。Runner 的临时 dispatch 和 receipt 位于 Runner 内部临时目录，完成后清理，不成为业务事实来源。

## 进程与 Session

单一命令入口：

```text
perpetuum start
perpetuum stop
perpetuum restart
perpetuum status
```

`start` 启动一个轻量本地后台进程，同时运行 Scheduler、HTTP API 和前端。Runner 直接管理 Root 与 Reporter session；其他 session 由各自父 Supervisor 通过 `cc-use` 管理。所有 session 名必须唯一。

调用 `start` 前先检查配置的监听地址。若该地址已经提供 Perpetuum API，直接复用现有服务，不重新启动，也不为了获得新进程而改用其他端口。只有用户明确要求时才执行 `restart`。若端口属于其他服务，报告冲突并停止；不要自动关闭对方或选择备用端口。

Runner 不通过 TUI 屏幕文本判断完成。它为 Root 和 Reporter 提供一次性回执路径，Agent 原子写入回执后，Runner 才回收顶层 session。TUI 屏幕只用于人类观察和软性诊断。

## 前端

默认监听 `127.0.0.1:8765`。前端展示所有项目的 Goal、Plan、History、Inbox、Questions、Escalations、Reports、runtime 状态和 Runner 健康，并允许追加人类指令、回复问题、调整时间窗口、暂停、恢复和立即触发项目。

Linux 服务器上的前端可从本地电脑通过 SSH 转发访问：

```bash
ssh -L 8765:127.0.0.1:8765 <server>
```

然后打开 `http://127.0.0.1:8765`。默认不要监听公网地址，也不要引入数据库或云服务。
