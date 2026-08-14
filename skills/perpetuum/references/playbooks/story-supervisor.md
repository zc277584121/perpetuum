# Story Supervisor Playbook

Story Supervisor 只服务 Project Supervisor 已经选择的一张 Story。它管理一条连续的 Executor ↔ Validator 反馈链，并在 Story 达到稳定结果后调用一次 Explorer 维护未来看板。本 Playbook 不提供需要反复发送的固定 Prompt。

## 启动时

读取 Project Supervisor 指定的 Story 完整正文、Goal、可信 History、人类输入、项目运行状态和直接相关证据。确认当前 Story ID 与文件一致、没有另一个 Story 正在执行，然后把 Story 标记为 `in_progress`，项目状态改为 `working`，写入 `current_story` 和 `story_phase: executing`。

Story Supervisor 不重新选择 Story，也不在开始时调用 Explorer。

## Executor

通过 `cc-use` 创建一个独立 Executor session。Prompt 至少说明：

- 当前唯一 Story 及其与长期 Goal 的关系；
- Story 背景、预期成果、范围、边界和验收标准；
- 当前承载 Executor 的 session 名称及上级所有权；
- 已知事实、已有证据、恢复上下文和仍不确定的内容；
- 可用环境、资源、权限和不可触碰的底线；
- 需要业务判断或管控处理时应返回的完整背景。

正常情况下整个 Story 只使用这一个 Executor session。允许跨天、多轮工作和自动 compaction；不要因为时间经过或暂时没有输出发送固定 Prompt。

## Validator

Executor 提供可验证结果后，创建一个与 Executor 分离的 Validator session，并把 `story_phase` 改为 `validating`。Prompt 至少说明 Story、边界、验收标准、Executor 声明的结果、证据位置和当前承载 session 的上级所有权。

正常情况下整个 Story 只使用这一个 Validator session。Validator 退回时，把具体缺口交给原 Executor；Executor 修改后，再让原 Validator 复验。不要重新启动 Explorer、Executor、Validator 或创建新的 Story 循环。只有物理 session 丢失、损坏或无法恢复时才允许替换，并记录原因。

## 接受

Validator 接受后：

1. 把 Story 正文更新为最终成果、证据和重要决定；
2. front matter 改为 `done`；
3. 把精简可信结论写入 `history.md`；
4. 清除 Story 的等待字段；
5. 关闭并复核 Executor 与 Validator session；
6. 调用一次 Explorer 维护后续 Story；
7. 清空项目 `current_story`、`story_phase` 和活动 session，项目回到 `idle`；
8. 关闭 Explorer，再向 Project Supervisor 返回结果。

## 等待或阻塞

需要人类、管控处理或长期外部条件时：

1. 把当前进展、可信证据、等待原因、恢复条件和恢复第一步写入 Story 正文；
2. Story 改为 `waiting`，设置 `waiting_on`；
3. Question 或 Escalation 写清 Story ID 和完整来龙去脉；
4. 关闭并复核 Executor 与 Validator session；
5. 调用一次 Explorer，让它根据当前 Story 已暂停这一事实调整其他 Story；
6. 清空 `current_story`、`story_phase` 和活动 session；
7. 项目状态使用 `waiting_human`、`control_blocked` 或 `idle`；
8. 关闭 Explorer，再向 Project Supervisor 返回。

等待期间不保留 Story 工作 session。人类回答或条件恢复后，Project Supervisor 把同一个 Story 改回 `ready`，新的 Story Supervisor 根据正文恢复。

## Explorer 收口

Explorer 只在 Story 达到完成、等待或管控阻塞的稳定状态后启动。给它提供刚刚结束的 Story、Validator 结论、History、Goal、人类输入和 Story 元数据列表。Explorer 可以创建、调整优先级、更新或取消未来 Story，但不得改写刚刚验证完成的事实，也不得物理删除 Story 文件。

Explorer 完成后关闭其 session。Story Supervisor 结束前只关闭并复核自己明确创建并保存了精确名称的 Executor、Validator 和 Explorer session，不根据全局列表操作来源不明的 session。
