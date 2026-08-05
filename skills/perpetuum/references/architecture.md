# 架构

## 唯一主干

```text
Local Runner / Frontend Service
        ↓
Root Supervisor
        ↓
Project Supervisor
        ↓
Task Supervisor
        ├── Explorer
        ├── Executor
        └── Validator
```

Runner 不是 Agent。它周期性读取 `activation.yaml`，找出当前具备时间资格的项目，然后从 Root 向下启动调用链。业务判断始终由 Agent 完成。

## 各层职责

- **Root Supervisor**：管理本次被激活的项目集合，调用 Project Supervisor，聚合结果并回收直属 session。
- **Project Supervisor**：读取一个项目的完整 Harness，处理人类输入，判断是否值得开始工作，并保证该项目同一时刻只有一个 Task。
- **Task Supervisor**：只负责一个 Task 的生命周期，调度 Explorer、Executor 和 Validator，并在结束前回收自己创建的 session。
- **Explorer**：维护 Task 列表、调整优先级、选择当前 Task。Task 是唯一的业务工作粒度。
- **Executor**：完成当前 Task，可使用一轮或多轮对话。
- **Validator**：独立检查结果，决定接受、退回或请求人类判断。
- **Reporter**：独立于 Root 的每日检查 Agent，分别为每个项目写日报。

## 调用规则

所有 Agent 上下级调用都使用当前安装的 `cc-use` Skill，并将子节点的项目目录、Harness 路径、职责参考和完成条件用自然语言传入。Perpetuum 不保存 `cc-use` 的具体命令或参数。

每个父节点只管理自己创建的直属 session。父节点结束前必须确认直属子 session 已经关闭；Runner 最后关闭 Root 或 Reporter session。所有 session 使用唯一名称，不复用固定名称，也不以“先替换同名 session”作为正常流程。

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
