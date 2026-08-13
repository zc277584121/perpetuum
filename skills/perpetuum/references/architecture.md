# 架构

## 整体结构

```text
Local Runner / Frontend Service
        ├── Root Supervisor
        │       └── Project Supervisor
        │               └── Task Supervisor
        │                       ├── Explorer
        │                       ├── Executor
        │                       └── Validator
        └── Reporter
```

Project 是真实项目目录；Harness 是该项目在 `~/.perpetuum/projects/<project-id>/` 下的长期运行资料。Task 是系统中唯一的业务工作粒度，session 是一个由 tmux 承载的交互式 Agent TUI 会话。

Runner 不是 Agent。它周期性读取 `activation.yaml`，找出当前位于时间窗口内或被人类要求立即运行的项目，然后从 Root 向下启动调用链。是否真的值得开始业务工作，仍由 Agent 判断。

Runner 直接启动 Root 与 Reporter 这两个彼此独立的顶层 TUI。Root 负责业务调度链路；Reporter 负责每日检查和报告，不依赖 Root 成功完成。顶层 Agent 启动后，所有下级调用交给 `cc-use`。

## 各层职责

- **Root Supervisor**：管理本次被激活的项目集合，调用 Project Supervisor，聚合结果并回收直属 session。
- **Project Supervisor**：读取一个项目的完整 Harness，处理人类输入，判断是否值得开始工作，并保证该项目同一时刻只有一个 Task。
- **Task Supervisor**：负责一次 Task 选择、执行和验证循环，调度 Explorer、Executor 和 Validator，并在结束前回收自己创建的 session。Explorer 没有选出 Task 时，本次循环以 Idle（没有值得执行的 Task）结束。
- **Explorer**：维护 Task 列表、调整优先级、选择当前 Task。Task 是唯一的业务工作粒度。
- **Executor**：完成当前 Task，可使用一轮或多轮对话。
- **Validator**：独立检查结果，决定接受、退回或请求人类判断。
- **Reporter**：独立于 Root 的每日检查 Agent，分别为每个项目写日报。

## 调用规则

所有 Agent 上下级调用都使用当前安装的 `cc-use` Skill。Perpetuum 只用自然语言说明要创建、观察或关闭哪一个下级 session，不保存或复制 `cc-use` 的具体命令和参数。

调用下级时遵循当前 `cc-use` Skill 的完整调用生命周期。在调用最终返回前，不根据中间状态或临时空输出判断 session 创建成功、失败或回执缺失。

每个角色读取自己的 Playbook。Playbook 是软性工作指南，不是需要逐字复制的固定 Prompt。父 Supervisor 应结合 Playbook、当前 Harness、运行时状态和现场判断，向下级说明本次为什么开始、要读取什么、边界在哪里、期望返回什么以及何时停止。

Runner 对每个新建的 Root 或 Reporter session 只发送一次启动 Prompt。其他 Prompt 由父 Supervisor 在新建下级 session、收到实际结果、Validator 退回、人类补充决定或外部条件发生实质变化时发送。时间经过、session 仍存活或屏幕暂时没有变化，本身都不是发送新 Prompt 的理由。

`project.yaml` 只保存 `codex` 或 `claude` 类型，不保存启动命令。Codex、Claude Code 的顶层启动参数由 Runner 统一管理；cc-use 管理下级 Agent 的启动参数和运行资源。

每个 Supervisor 都运行在上级为它创建的承载 session 中，同时可以为下级创建直属子 session。当前承载 session 不属于它自己管理；每个父节点只管理本次由自己明确创建并保存了精确名称的直属子 session。全局 session 列表、名称、目录、创建时间和项目状态只能用于观察，不能证明所有权。来源不明的 session 保持不动并向上级报告。父节点结束前必须确认直属子 session 已经关闭；Runner 最后关闭 Root 或 Reporter session。所有 session 使用唯一名称，不复用固定名称，也不以“先替换同名 session”作为正常流程。

父节点创建下级后，把下级当前承载 session 的精确名称写入首次 Prompt，并说明该 session 由上级管理；下级不得关闭、接管或向自己的承载 session 发送消息。

## 并发

同一 Project 同时最多一个 Task。不同 Project 可以并行，Root 可根据项目数量和当前资源决定并行或顺序调用 Project Supervisor。不要设置全局 Task 数上限。

## 动力来源

Runner 提供外部唤醒，Explorer 提供持续可扩充的 Task 列表：

1. Runner 在时间窗口内激活项目路径。
2. Project Supervisor 判断是否存在值得推进的业务工作。
3. Explorer 根据长期目标、历史结果和当前证据补充、重排或选择 Task。
4. Executor 和 Validator 完成一个 Task。
5. 下一次唤醒时重复。

当目标阶段性完成且 Explorer 不再产生 Task 时，项目进入 Idle；这不是错误，由日报明确说明即可。
