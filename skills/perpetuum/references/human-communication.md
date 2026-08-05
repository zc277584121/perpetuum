# 人类通信

所有通信文件都放在各自项目 Harness 中。前端只聚合，不在全局复制 Inbox、Questions、Escalations 或 Reports。

## Inbox：人类业务指令

人类可随时在文件末尾的追加区写入目标修正、优先级、暂停某类工作、资源说明或新的边界。Project Supervisor 处理后保留原文，并补充处理时间、采取的动作和影响范围。

## Questions：业务判断

Question 必须脱离现场也能理解。至少写清：

- 为什么现在需要询问；
- 当前 Task 和长期 Goal 的关系；
- 已经做过什么；
- 已知事实和证据；
- 为什么 Agent 不能自行决定；
- 可选方案及各自权衡；
- 系统建议及理由；
- 人类暂不回答的后果；
- 相关项目与 Harness 文件路径。

最终 Question 由 Project Supervisor 结合 Goal、Plan 和 History 整理。不要直接粘贴 Executor 的技术片段。

## Escalations：管控问题

Escalation 用于环境、权限、配额、认证、进程、session、磁盘、网络或基础设施问题。至少写清：

- 发生了什么；
- 影响了哪些项目和 Task；
- 已尝试哪些安全恢复；
- 为什么不能自动处理；
- 人类需要执行或决定什么；
- 处理后怎样验证恢复；
- 原始日志与状态文件路径。

不要用自动更新 Agent、Skill、插件或认证来“修复” Escalation。

## 人类回复

前端把回复追加到对应文件末尾的“人类回复（追加区）”，保留时间和原问题标识。Project Supervisor 在下一次激活时吸收回复，并记录它如何改变 Plan 或执行边界。

## 报告

日报位于每个项目自己的 `reports/`。`latest.md` 便于前端读取，日期文件保留历史。日报是摘要，不替代 `history.md` 的可信业务结论，也不替代 `runtime/events.log` 的运行流水。
