# 运行时

## 目录

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
    ├── schedule.yaml
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

`activation.yaml` 只保存全局服务、Reporter 和项目注册；`project.yaml` 保存项目目录与 Agent 类型；`schedule.yaml` 保存该项目自己的运行计划；`runner/runs/` 是一次顶层调用的临时交接目录，完成后清理。

## 项目运行计划

每个项目的 `schedule.yaml` 使用：

```yaml
version: 1
timezone: Asia/Shanghai
enabled: true
paused: false
force_run: false
cron:
  - "*/5 0-5 * * *"
```

只支持标准五字段 cron：

```text
分钟 小时 日 月 星期
```

Runner 常驻运行并在进程内解释这些表达式，不调用 Linux cron、Windows Task Scheduler 或 systemd timer 启动每个 Project Supervisor。相同项目在同一个 cron 分钟只触发一次；已有活动 Project Supervisor 时不创建第二个，也不向原 TUI 追加启动 Prompt。

`force_run` 由“立即运行”控制写入，Runner 消费后自动恢复为 `false`。`paused` 阻止新激活；它不结束已经运行的 Story。

## 一次项目激活

cron 匹配或收到立即运行请求后：

1. Runner 创建新的 tmux 和交互式 Codex 或 Claude Code TUI；
2. Runner 生成 `dispatch.json` 和 `receipt.json` 路径；
3. Runner 向 Project Supervisor 发送一次中文启动 Prompt；
4. Project Supervisor 读取 Harness，选择至多一张 Story，并通过 cc-use 启动 Story Supervisor；
5. Story 达到完成、等待、管控阻塞或本轮正常 Idle 后，Project Supervisor 关闭直属 session、更新状态并原子写入回执；
6. Runner 看到回执后回收 Project Supervisor TUI 并清理临时运行目录。

cron 只限制新的激活开始。已经启动的 Story 可以跨出匹配时间继续完成，不设置固定 Story 时长。

## 项目状态

- `idle`：当前没有 Story session 在运行；
- `working`：正在执行或验证一张 Story；
- `waiting_human`：当前 Story 已保存现场并关闭 session，等待人类业务决定；
- `control_blocked`：当前 Story 已保存现场并关闭 session，等待环境或运行机制恢复；
- `paused`：人类已暂停该项目开始新 Story。

`runtime/state.json` 使用：

```json
{
  "version": 1,
  "status": "idle",
  "current_story": null,
  "story_phase": null,
  "active_sessions": [],
  "last_activity_at": "...",
  "last_result": "..."
}
```

`story_phase` 可以是 `executing`、`validating` 或 `exploring`。`active_sessions` 是各层尽力记录，不是 cc-use 或 tmux 的全局权威清单，也不授予关闭权限。

Runner 的 `state.json` 使用 `active_projects` 按项目记录顶层 Project Supervisor，因此不同项目可以并行；`active_reporter` 独立记录 Reporter。

## 等待时关闭

Story 需要等待人类、管控处理或长期外部条件时：

1. 更新 Story 正文的当前进展、证据、等待原因和恢复上下文；
2. front matter 改为 `status: waiting`，并写入 `waiting_on`；
3. 业务问题写入 `questions.md`，管控异常写入 `escalations.md`；
4. 关闭 Executor、Validator 和 Story Supervisor session；
5. 清空 `current_story`、`story_phase` 和 `active_sessions`；
6. Project 后续可以执行其他 `ready` Story。

人类回答或条件恢复后，把原 Story 改回 `ready`，下一次使用新的物理 session 恢复同一个 Story。Validator 普通退回不属于等待，继续使用原 Executor 和原 Validator。

## Prompt 和回执

Runner 的启动 Prompt 是确定性的最小信封，提供项目、Harness、触发原因、Playbook、承载 session、dispatch 和回执路径。它不指定必须选择哪张 Story，不包含 cc-use 的具体命令，也不按时间重复发送。

Project Supervisor 的业务调度是软性的：根据 Playbook、Story 看板、人类输入和真实结果决定选择、Idle、等待和下级 Prompt。写回执前必须关闭并复核自己创建的全部直属 session。Runner 不通过屏幕文本判断业务完成。

## 常用入口

```bash
<skill-directory>/scripts/perpetuum init
<skill-directory>/scripts/perpetuum start
<skill-directory>/scripts/perpetuum status
<skill-directory>/scripts/perpetuum project list
<skill-directory>/scripts/perpetuum project schedule <project-id> "*/5 0-5 * * *" --timezone Asia/Shanghai
<skill-directory>/scripts/perpetuum story list <project-id> --json
<skill-directory>/scripts/perpetuum stop
```

`start` 发现同一 home 的前端已经运行时直接复用；发现不同 home 或其他服务占用端口时明确报错，不自动换端口或结束其他服务。

前端默认只监听 `127.0.0.1:8765`。从另一台电脑查看远程 Linux 机器时使用 SSH 端口转发：

```bash
ssh -L 8765:127.0.0.1:8765 <server>
```

然后在本地打开 `http://127.0.0.1:8765`。默认不要把前端直接监听到公网地址。
