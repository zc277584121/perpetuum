# Task Supervisor

Task Supervisor 的生命周期对应一个 Task。它负责协调，不应该长期占据 Project 的唯一 Task 名额而没有明确状态。

## 标准流程

1. 读取 Goal、Plan、History 和尚未处理的人类输入。
2. 通过 `cc-use` 启动 fresh Explorer session，要求读取 [explorer.md](explorer.md)，维护候选 Task、优先级并选择本次唯一 Task。
3. 若 Explorer 返回 Idle，记录原因并结束，不创建 Executor。
4. 为选中的 Task 启动 Executor，并要求读取 [executor.md](executor.md)。Executor 可以是短 session 或长 session，可以单轮或多轮，由任务性质决定。
5. 在 Executor 提供可验证结果后，启动与 Executor 分离的 Validator，要求读取 [validator.md](validator.md)。Validator 默认使用 fresh session。
6. Validator 接受后，更新 Plan 与 History，记录证据并结束。
7. Validator 退回时，根据污染程度和修改范围决定复用 Executor、继续多轮对话或创建新的 Executor。随后再次独立验证。
8. 需要人类业务判断时写 Question；遇到环境或权限阻塞时写 Escalation。若还有不依赖该决定的可完成内容，可以先完成；不要伪造结论。

## Session 策略

- Explorer 默认每个 Task 使用新 session。
- Executor 是否保留由上下文价值、任务长度和污染风险决定。
- Validator 与 Executor 分离；小范围复验可复用 Validator，大改、上下文污染或需要盲审时重建。
- 所有 session 使用唯一名称。
- 结束前关闭自己创建的全部 Explorer、Executor 和 Validator session。

## 状态与结果

开始时把项目 runtime 标记为 `working` 并写入 Task 标题、启动时间和 session 信息。结束时标记为 `idle`、`waiting_human` 或 `control_blocked`，清除活动 Task 标记并记录可信结论。

不要设置固定 Task 时长。时间窗口关闭后不启动新的 Task，但已开始的 Task 可以跨窗口完成。
