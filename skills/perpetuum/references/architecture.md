# 架构

## 整体结构

```text
Local Runner / Frontend Service
        ├── Root Supervisor
        │       └── Project Supervisor
        │               └── Story Supervisor
        │                       ├── Executor
        │                       ├── Validator
        │                       └── Explorer（Story 收口后）
        └── Reporter
```

Project 是真实项目目录；Harness 是该项目在 `~/.perpetuum/projects/<project-id>/` 下的长期运行资料。一个 Project 在前端对应一个看板页面，一个 Story 文件对应一张卡片。Story 是系统中唯一的业务工作粒度，session 是一个由 tmux 承载的交互式 Agent TUI 会话。

Runner 不是 Agent。它继续按照现有时间窗口读取 `activation.yaml`，找出当前允许开始新 Story 的项目，然后从 Root 向下启动调用链。是否真的值得开始业务工作，仍由 Agent 判断。本次 Story 重构不改变 Root 和 Project 的时间调度方式。

## 各层职责

- **Root Supervisor**：管理本次被激活的项目集合，调用 Project Supervisor，聚合结果并回收直属 session。
- **Project Supervisor**：读取一个项目的 Harness 和 Story 元数据，处理人类输入，选择一张已有 Story，并保证项目同一时刻只有一个 Story 在执行。没有可运行 Story 时调用一次 Explorer 做兜底刷新。
- **Story Supervisor**：只服务 Project Supervisor 已经选择的一张 Story，管理 Executor、Validator 和 Story 收口后的 Explorer，并在结束前回收自己创建的 session。
- **Executor**：完成当前 Story。正常情况下一个 Story 只创建一个 Executor session，并允许跨天、多轮持续工作。
- **Validator**：独立检查当前 Story。正常情况下一个 Story 只创建一个 Validator session；退回后继续在同一个 Validator session 中复验原 Executor 的修改。
- **Explorer**：在 Story 达到完成、等待或管控阻塞的稳定状态后，根据刚产生的事实维护未来 Story；没有可运行 Story 时也可以由 Project Supervisor 单独调用一次。
- **Reporter**：独立于 Root 的每日检查 Agent，分别为每个项目写日报。

## Story 工作链

```text
Project Supervisor 从 Story 看板选择一张卡片
        ↓
Story Supervisor 启动 Executor
        ↓
Executor 产生可验证结果
        ↓
Story Supervisor 启动 Validator
        ↓
Validator 退回 ──→ 原 Executor 修改 ──→ 原 Validator 复验
        ↓ 接受、等待或管控阻塞
保存 Story 结果和恢复上下文
        ↓
关闭 Executor 与 Validator
        ↓
启动一次 Explorer，维护后续 Story
        ↓
关闭 Explorer 与 Story Supervisor
```

Validator 的多次退回和 Executor 的多次修改属于同一条连续 Story 工作链，不产生新的 Story 或新的执行循环。只有物理 session 丢失、损坏或无法恢复时才允许替换 Executor 或 Validator；替换仍服务同一 Story，并记录管控事件。

## 渐进式披露

Story 的 front matter 保存看板需要的元数据，正文保存完整背景、边界、验收、进展和证据。Project Supervisor 和 Explorer 先通过 Perpetuum 的 Story 接口读取全部元数据，只打开少量候选或当前 Story 的正文。Executor 和 Validator 只读取当前 Story 及直接相关的 Goal、History 和证据。

不要通过固定行数、`head` 或屏幕文本猜测 front matter。脚本和前端统一使用 PyYAML 解析两个 `---` 分隔符之间的内容。完整格式见 [story.md](story.md)。

## 调用和所有权

所有 Agent 上下级调用都使用当前安装的 `cc-use` Skill。Perpetuum 只用自然语言说明要创建、观察或关闭哪一个下级 session，不保存或复制 `cc-use` 的具体命令和参数。

每个 Supervisor 都运行在上级为它创建的承载 session 中，同时可以为下级创建直属子 session。当前承载 session 不属于它自己管理；每个父节点只管理本次由自己明确创建并保存了精确名称的直属子 session。全局 session 列表、名称、目录、创建时间和项目状态只能用于观察，不能证明所有权。

父节点创建下级后，把下级当前承载 session 的精确名称写入首次 Prompt，并说明该 session 由上级管理；下级不得关闭、接管或向自己的承载 session 发送消息。调用最终返回前，不根据中间状态或临时空输出判断 session 创建成功、失败或回执缺失。

## 并发

同一 Project 同时最多执行一个 Story。不同 Project 可以并行，Root 仍可根据项目数量和资源决定并行或顺序调用 Project Supervisor。本次不实现同一项目多 Story 并行。

## 动力来源

1. 初始化过程根据 Goal、项目证据和人类确认建立第一批 Story。
2. Runner 在时间窗口内激活项目路径。
3. Project Supervisor 从 `in_progress` 或 `ready` Story 中选择一张。
4. Executor 和 Validator把该 Story 推进到稳定结果。
5. Explorer 基于这个结果维护下一轮 Story 池。
6. 下一次唤醒时重复。

没有可运行 Story 时，Project Supervisor 调用一次 Explorer；Explorer 仍没有产生 `ready` Story时，项目正常进入 Idle，由日报说明即可。
