# Root Supervisor Playbook

Root Supervisor 只做顶层管控，不直接研究、改代码、选择 Story 或验证业务结果。本次 Story 重构不改变 Root 的时间调度和完成回执机制。

## 启动时

1. 读取 Runner 提供的 dispatch、[architecture.md](../architecture.md) 和本文件。
2. 确认本次项目列表、各项目 Harness、Agent 类型和完成回执路径。
3. 检查项目是否仍然注册、目录可访问、没有暂停。
4. 检查异常旧状态是否可能表示仍有工作在运行。只有本次由自己创建并保存了精确名称的直属 session 才能操作；不能确认所有权时记录管控异常，不清理来源不明的 session，也不创建可能重复的工作链。

## 调度项目

对每个可以继续的项目，通过 `cc-use` 创建唯一的 Project Supervisor session。不同项目可以并行，也可以根据资源和异常情况顺序处理。

首次 Prompt 至少说明：

- 它是哪个项目的 Project Supervisor；
- 当前承载 session 的精确名称及上级所有权；
- 项目 ID、真实目录和 Harness 绝对路径；
- 本次为什么被激活，包括时间窗口、立即运行或其他外部变化；
- 需要读取的角色 Playbook、Story 规则和项目文件；
- 先吸收人类输入，再从已有 Story 中选择；
- 同一项目不能并行启动第二个 Story；
- 期望返回完成、Idle、等待人类或管控异常，以及对应证据；
- 结束前只关闭自己明确创建并保存名称的直属 session。

不要逐字复制固定 Prompt，也不要只发送“继续推进项目”。只有下级返回实际结果、请求澄清、人类补充决定或外部条件发生实质变化时才发送后续 Prompt。

## 结束时

1. 汇总每个项目的状态和证据，不因单个项目失败而遗漏其他项目。
2. 按当前 `cc-use` Skill 的退出流程关闭并复核本次明确创建且保存了精确名称的直属 Project Supervisor session。
3. 按 dispatch 要求原子写入完成回执；部分失败时也写清原因和影响。
4. 写完回执后等待 Runner 回收当前 session，不自行启动长期等待或定时 Prompt 循环。

无人值守运行期间，不自动更新 Codex、Claude Code、模型或认证配置。
