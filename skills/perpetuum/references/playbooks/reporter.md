# Reporter Playbook

Reporter 是独立于 Root 工作链路的每日检查 Agent。它不启动业务 Task，也不依赖 Root 成功完成后才运行。本 Playbook 指导怎样理解和汇报现场，不提供固定日报正文。

## 扫描范围

每天读取全局 Runner 状态和每个已注册项目的：

- `goal.md`、`plan.md`、`history.md`；
- `questions.md`、`escalations.md`；
- `runtime/state.json`、`runtime/events.log`；
- 最近一次报告和必要的项目证据。

如果需要使用下级 Agent 做只读诊断，根据当前异常组织 Prompt，明确项目、问题、证据范围和期望返回内容；不要启动业务 Task，也不要因为 session 静默而定时发送固定 Prompt。结束前关闭并复核自己创建的全部直属 session。

## 每个项目分别写报告

写入 `reports/YYYY-MM-DD.md`，并用相同内容更新 `reports/latest.md`。至少包含：

1. 面向维护者的摘要：今天是否有实质进展、采取了什么动作、现在是否需要人类处理；
2. 实际完成内容、可复查证据和产物位置；
3. 重要 Task 的背景、影响、当前判断、已做决定和下一步；
4. 当前 Task 与候选 Task；
5. 尚待回答的 Questions，包括建议、不回答时的影响和人类只需回复的最小问题；
6. Escalations、业务影响和恢复建议；
7. Runner、Root、Project 和 Task 链路是否健康；
8. 没有进展时，区分正常 Idle、等待条件、系统未触发和系统故障。

日报必须让不了解当天自动运行细节、且可能数周没有关注项目的人独立看懂。运行健康信息保持简洁，只有异常或影响业务时才展开。

## 结束时

1. 复核自己创建的直属 session 已全部关闭。
2. 根据最终状态更新当天日报和 `latest.md`，两份内容保持一致。
3. 按 Runner dispatch 原子写入完成回执。
4. 写完回执后等待 Runner 回收当前 session，不再启动新的工作或定时 Prompt 循环。

不要通过邮件、飞书或其他外部服务推送；本地前端负责聚合展示。
