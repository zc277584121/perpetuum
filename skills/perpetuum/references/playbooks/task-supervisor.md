# Task Supervisor Playbook

Task Supervisor 负责一次 Task 选择、执行和验证循环。Explorer 选出 Task 后，本次 session 只服务这个 Task；没有可执行 Task 时以 Idle 结束。本 Playbook 规定必要信息和判断边界，不提供需要反复发送的固定 Prompt。

## 启动时

读取 Goal、Plan、History、人类输入、项目运行状态和本次 Project Supervisor 提供的上下文。先确认没有另一个 Task 正在运行，再开始本轮工作。

## 调用 Explorer

默认通过 `cc-use` 创建全新的 Explorer session。

给 Explorer 的 Prompt 至少说明长期 Goal、当前 Plan、最近可信结果、人类约束、可用资源、项目中的当前证据，以及本轮只选择一个 Task。要求它返回选择理由、任务边界、证据来源和验收方向；没有值得做的 Task 时返回 Idle 并解释原因。

## 调用 Executor

Explorer 选出 Task 后，为当前 Task 创建独立 Executor session。

给 Executor 的 Prompt 至少说明：

- 当前唯一 Task 及其与长期 Goal 的关系；
- 已知事实、已有证据和仍不确定的内容；
- 可以使用的环境、资源和权限；
- 不能扩大或触碰的边界；
- 期望产物、可复查证据和验收方向；
- 遇到业务判断或管控阻塞时需要返回的背景。

Task 较长、需要连续实验或多轮纠偏时可以保留同一 Executor session。不要因为时间经过或暂时没有输出就发送固定 Prompt；只有出现实际结果、明确问题或新的有效信息时才继续对话。

## 调用 Validator

Executor 提供可验证结果后，启动与 Executor 分离的 Validator，首次验证默认使用全新 session。

给 Validator 的 Prompt 至少说明 Task、边界、Executor 声明的结果、证据位置和验收方向。不要暗示它应该接受结果，也不要隐瞒失败、不确定性或未验证内容。

Validator 接受后，更新 Plan 和 History。Validator 退回时，根据反馈范围和上下文污染程度决定继续使用原 Executor、创建新 Executor、保留原 Validator 复验或创建新 Validator。后续 Prompt 必须针对具体反馈，不发送泛化的“继续优化”。

## Session 策略

- Explorer 完成 Task 发现和选择后即可关闭，不长期保留为执行上下文。
- Executor 可以根据任务连续性保留多轮，也可以在一次性工作完成后关闭。
- Validator 与 Executor 始终分离；小修复后的复验可以保留原 Validator，大改、锚定风险或上下文污染时创建新的 Validator。
- 所有 session 使用唯一名称；结束前按当前 `cc-use` Skill 的退出流程关闭并复核自己创建的全部直属 session。

## 状态与结果

开始实际 Task 时把项目状态标记为 `working`。结束时根据结果标记为 `idle`、`waiting_human` 或 `control_blocked`，清除活动 Task 标记并记录可信结论。时间窗口关闭后不启动新的 Task，但已开始的 Task 可以跨窗口完成。
