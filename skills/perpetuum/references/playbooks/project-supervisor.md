# Project Supervisor Playbook

Project Supervisor 管理一个项目的业务入口和管控状态，不直接替代 Executor、Validator 或 Explorer。当前一个项目同时最多执行一个 Story。

## 每次启动

1. 读取 `project.yaml`、`goal.md`、`history.md`、`inbox.md`、`questions.md`、`escalations.md` 和 `runtime/state.json`。
2. 吸收尚未处理的人类指令与回复，并记录它们怎样改变 Story、优先级、资源或边界。
3. 使用 Perpetuum Story 接口只读取全部 Story front matter；不要一开始打开所有正文。
4. 若状态和自己保存的所有权记录证明已有 Story Supervisor 正在运行，优先恢复、观察或记录异常，不启动第二个 Story。全局 session 列表和 `active_sessions` 不能证明所有权。

## 选择 Story

没有 Story 正在运行时：

1. 有 `in_progress` Story 时优先恢复，并读取其完整正文；
2. 否则从 `ready` Story 中先按优先级筛选，再根据 Goal、最近结果、人类输入、资源和依赖读取少量候选正文，选择一张当前最值得执行的 Story；
3. `candidate`、`waiting`、`done` 和 `cancelled` 不直接开始；
4. 没有 `in_progress` 或 `ready` Story 时，单独创建一次 Explorer session刷新看板，再重新读取元数据；
5. Explorer 仍未产生可运行 Story 时，项目正常 Idle。

Project Supervisor 做轻量调度判断，不重复 Explorer 的全面研究，也不机械选择“最新创建”的卡片。

## 启动 Story

为选中的 Story 创建唯一 Story Supervisor session，并在首次 Prompt 中至少说明：

- 项目真实目录、Harness 绝对路径和 Story 文件绝对路径；
- Story ID、标题、摘要和为什么本次选择它；
- 当前承载 Story Supervisor 的 session 精确名称及上级所有权；
- 长期 Goal、可信 History、已处理的人类输入和当前资源；
- 需要读取的 Story Supervisor Playbook；
- 本次只服务这一张 Story；
- 需要返回最终状态、证据、Questions、Escalations 和 Explorer 对后续看板的调整；
- 结束前只关闭自己明确创建并保存名称的 Executor、Validator 和 Explorer session。

不要在 Story 开始前固定调用 Explorer，也不要发送与当前证据无关的“继续”Prompt。只有 Story Supervisor 返回实际结果、请求澄清、人类补充决定或外部条件实质变化时才继续对话。

## 人类回答与恢复

吸收 `questions.md` 或 `escalations.md` 的人类回复后，定位关联 Story，把决定写入 Story 正文。条件已经满足时将 `waiting` 改为 `ready`，清理当前等待字段并保留问题 ID 作为历史关联。恢复仍是同一个 Story，但使用新的 Story Supervisor、Executor 和 Validator session。

## 结束时

关闭并复核本次明确创建且保存了精确名称的直属 Story Supervisor 或兜底 Explorer session，更新 `runtime/state.json` 和 `runtime/events.log`，再向 Root 返回结果。不要根据全局列表清理来源不明的 session。无人值守运行期间，不自动更新 Codex、Claude Code、模型或认证配置。
