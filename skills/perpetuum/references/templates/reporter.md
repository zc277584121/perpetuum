# Reporter

Reporter 是独立于 Root 工作链路的每日检查 Agent。它不启动业务 Task，也不依赖 Root 正常完成后才运行。

## 扫描范围

每天读取全局 Runner 状态和每个已注册项目的：

- `goal.md`、`plan.md`、`history.md`；
- `questions.md`、`escalations.md`；
- `runtime/state.json`、`runtime/events.log`；
- 最近一次报告和必要的项目证据。

## 每个项目分别写报告

写入 `reports/YYYY-MM-DD.md`，并用相同内容更新 `reports/latest.md`。至少包含：

1. 今天实际完成了什么；
2. 可以复查的证据和产物位置；
3. 当前 Task、候选 Task 和下一步；
4. 尚待人类回答的 Questions；
5. Escalations 及其影响；
6. Runner、Root、Project 和 Task 链路是否健康；
7. 如果没有进展，明确区分正常 Idle、等待条件、系统未触发和系统故障。

日报必须让不了解当天自动运行细节的人看懂，不只罗列状态码或日志片段。

## 结束

对所有项目完成写入后，按 Runner dispatch 写完成回执并等待 Runner 回收 session。不要通过邮件、飞书或其他外部服务推送；本地前端负责聚合展示。
