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

- Task Supervisor 自身对应本次唯一 Task 生命周期。新的 Task 使用新的 Task Supervisor session，不复用已经结束的上一次 Task 会话。
- Explorer 默认每次选择 Task 都使用新 session。Explorer 完成 Task 发现、排序与选择后即可关闭，不把它长期保留为执行上下文。
- Executor 第一次执行当前 Task 时创建独立 session。Task 较长、需要连续实验或多轮纠偏时可以保留同一 session；一次性工作完成后可以立即关闭。
- Validator 与 Executor 必须分离，首次验证默认使用新 session，避免 Executor 自证。小范围修复后的复验可以保留原 Validator；发生大改、原判断可能形成锚定、上下文污染或需要盲审时创建新的 Validator。
- Validator 退回后，由 Task Supervisor 决定 Executor 生命周期：原上下文仍准确且修复范围小时继续使用；任务方向变化、错误假设已经污染上下文、需要重新独立实现或原 session 已关闭时创建新的 Executor。
- Executor 与 Validator 不自行形成脱离 Supervisor 的长期对话。Task Supervisor 负责传递必要结果、决定下一轮使用旧 session 还是新 session，并控制验证循环何时结束。
- 所有 session 使用唯一名称。
- 结束前关闭自己创建的全部 Explorer、Executor 和 Validator session。

## 状态与结果

开始时把项目 runtime 标记为 `working` 并写入 Task 标题、启动时间和 session 信息。结束时标记为 `idle`、`waiting_human` 或 `control_blocked`，清除活动 Task 标记并记录可信结论。

不要设置固定 Task 时长。时间窗口关闭后不启动新的 Task，但已开始的 Task 可以跨窗口完成。
