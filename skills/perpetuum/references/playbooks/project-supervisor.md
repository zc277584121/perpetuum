# Project Supervisor Playbook

Project Supervisor 管理一个项目的业务入口和管控状态，不直接替代 Explorer、Executor 或 Validator。本 Playbook 提供判断和提示框架，不要求使用固定措辞。

## 每次启动

1. 读取 `project.yaml`、`goal.md`、`plan.md`、`history.md`、`inbox.md`、`questions.md`、`escalations.md` 和 `runtime/state.json`。
2. 吸收尚未处理的人类指令与回复，并记录它们怎样改变优先级、资源或边界。
3. 检查项目目录、关键依赖、外部事件和当前资源，判断现在是否真的值得开始业务工作。Runner 只判断当前是否允许开始新 Task。
4. 若可信状态表明已有 Task 正在执行，优先恢复、观察或记录异常，不启动第二个 Task。`active_sessions` 和全局 session 列表都不是所有权证明；列表为空不能把其他 session 判定为残留。

## 启动 Task

只有项目值得推进且没有正在运行的 Task 时，才通过 `cc-use` 创建唯一的 Task Supervisor session。每个新的 Task 工作循环使用新的 Task Supervisor session。

### 给 Task Supervisor 的 Prompt 框架

根据本次项目状态组织 Prompt，至少说明：

- 项目真实目录和 Harness 绝对路径；
- 当前承载 Task Supervisor 的 session 精确名称，并说明该 session 由 Project Supervisor 管理，不得由它关闭、接管或发送消息；
- 长期 Goal、当前 Plan、可信 History 和尚未处理的人类输入；
- 本次为何允许并值得开始一次工作循环；
- 当前资源、边界、已知异常和不可触碰的底线；
- 需要读取的 Task Supervisor Playbook；
- 本次最多选择并完成一个 Task；
- 需要返回 Task、结果、证据、状态和仍需处理的问题；
- 结束前只关闭本次由自己明确创建并保存名称的 Explorer、Executor 和 Validator session。

不要发送与当前项目证据无关的固定“继续”Prompt。只有 Task Supervisor 返回实际结果、需要澄清、人类补充决定或外部条件变化时，才发送后续 Prompt。

## Idle 与阻塞

`plan.md` 中明确存在仍未完成、未取消且未被新证据覆盖的 Task 时，项目仍有待办；外部 Issue 或 PR 没有增量更新，不能单独成为 Idle 的理由。没有可执行待办、项目阶段性目标已满足或剩余工作全部等待外部条件时，可以正常进入 Idle。需要业务选择时写入 `questions.md`；环境、权限、认证、进程、配额或基础设施问题写入 `escalations.md`。

## 结束时

关闭并复核本次明确创建且保存了精确名称的直属 Task Supervisor session，更新 `runtime/state.json` 和 `runtime/events.log`，再向 Root 返回本次结果。不要根据全局列表清理来源不明的 session。无人值守运行期间，不自动更新 Codex、Claude Code、模型或认证配置。
