# 运行时

## 目录

默认运行目录：

```text
~/.perpetuum/
├── activation.yaml
├── runner/
│   ├── state.json
│   ├── events.log
│   └── runs/<run-id>/
│       ├── dispatch.json
│       └── receipt.json
└── projects/<project-id>/
    ├── project.yaml
    ├── goal.md
    ├── stories/
    │   └── S-*.md
    ├── history.md
    ├── inbox.md
    ├── questions.md
    ├── escalations.md
    ├── reports/
    └── runtime/
        ├── state.json
        └── events.log
```

`activation.yaml` 与 `project.yaml` 使用 JSON 语法保存。Story 使用 YAML front matter + Markdown 正文。`runner/runs/` 是一次顶层调用的临时交接目录，完成后清理，不成为业务事实来源。

## Story 选择与时间窗口

Runner 继续按照现有机制判断项目是否位于允许开始新 Story 的时间窗口内，或是否收到“立即运行”请求；它不读取 Goal 或 Story，也不决定业务优先级。本次重构不改变 Root 和 Project 的时间调度。

Project Supervisor 被激活后：

1. 先吸收人类输入和已回答问题；
2. 读取全部 Story 元数据；
3. 有 `in_progress` Story 时优先恢复；
4. 否则从 `ready` 中选择当前最值得执行的一张；
5. 没有可运行 Story 时调用一次 Explorer，再重新读取列表；
6. 仍然没有则进入 Idle。

时间窗口只限制新 Story 的开始。已开始的 Story 可以跨出窗口继续完成，不设置固定 Story 时长。

## 项目状态

- `idle`：当前没有 Story session 在运行；
- `working`：正在执行或验证一个 Story；
- `waiting_human`：当前 Story 已保存现场并关闭 session，等待人类业务决定；
- `control_blocked`：当前 Story 已保存现场并关闭 session，等待环境或运行机制恢复；
- `paused`：人类已暂停该项目开始新 Story。

新 Harness 的 `runtime/state.json` 使用：

```json
{
  "version": 2,
  "status": "idle",
  "current_story": null,
  "story_phase": null,
  "active_sessions": [],
  "last_activity_at": "...",
  "last_result": "..."
}
```

`story_phase` 可以是 `executing`、`validating` 或 `exploring`。它只用于前端和诊断，不写进 Story front matter。

`active_sessions` 是各层运行中写入的尽力记录，不是 cc-use 或 tmux 的全局权威清单，也不授予关闭权限。Supervisor 只能操作本次由自己明确创建并保存了精确名称的直属子 session。

## 等待时关闭

Story 需要等待人类、管控处理或长期外部条件时：

1. 更新 Story 正文的当前进展、证据、等待原因和恢复上下文；
2. front matter 改为 `status: waiting`，并写入 `waiting_on`；
3. 业务问题写入 `questions.md`，管控异常写入 `escalations.md`，并关联 Story ID；
4. 关闭 Executor、Validator 和 Story Supervisor session；
5. 清空 `current_story`、`story_phase` 和 `active_sessions`；
6. Project 后续可以执行其他 `ready` Story。

人类回答或条件恢复后，Project Supervisor 把原 Story 改回 `ready`，下一次使用新的物理 session 恢复同一个 Story。Validator 普通退回不属于等待，继续使用原 Executor 和原 Validator。

## 状态写入

状态文件先写临时文件再原子替换，日志使用追加写。`events.log` 只保存运行流水；完成 Story 的可信结论写入 `history.md`，未验证的中间进展保存在 Story 正文。

## 顶层生命周期

Runner 为每个新建的 Root 或 Reporter session 发送一次中文启动 Prompt，提供 dispatch、Playbook、receipt 和承载 session。当前承载 session 由 Runner 管理。Runner 不按时间向仍然存活的 session 注入固定 Prompt，也不通过屏幕文本判断完成。

Root 和 Reporter 按既有回执机制工作：直属 session 全部关闭并完成状态更新后，原子写入 `receipt.json`，Runner 才回收顶层 session。

## 常用入口

```bash
<skill-directory>/scripts/perpetuum init
<skill-directory>/scripts/perpetuum start
<skill-directory>/scripts/perpetuum status
<skill-directory>/scripts/perpetuum project list
<skill-directory>/scripts/perpetuum story list <project-id> --json
<skill-directory>/scripts/perpetuum stop
```

`start` 发现同一 home 的前端已经运行时直接复用；发现不同 home 或其他服务占用端口时明确报错，不自动换端口或结束其他服务。

前端默认只监听 `127.0.0.1:8765`。从另一台电脑查看远程 Linux 机器上的看板时，使用 SSH 端口转发：

```bash
ssh -L 8765:127.0.0.1:8765 <server>
```

然后在本地打开 `http://127.0.0.1:8765`。默认不要把前端直接监听到公网地址。
