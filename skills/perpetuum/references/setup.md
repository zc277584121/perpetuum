# 初始化项目

## 前置检查

确认以下能力可用：

- 当前 Agent 能加载 `perpetuum` 与 `cc-use` Skill；
- `tmux` 可用；
- 对应的交互式 Codex 或 Claude Code TUI 可启动；
- Python 3.8 或更高版本可用；
- MemSearch 若已安装则可正常检索。

不要在初始化过程中更新 Agent、Skill、插件或认证。版本不兼容时记录问题并让用户决定。

## 初始化步骤

1. 解析用户指定或当前所在的项目目录，取得绝对路径。
2. 默认继承当前调用 Perpetuum 的 Agent 类型。只有用户明确要求时才覆盖为其他 Agent。
3. 若 MemSearch 可用，检索这个项目的历史目标、近期进展、用户偏好、可用资源、边界、已做决定和可能的下一步。
4. 检查项目中的说明文档、配置、最近状态和可验证证据。不要把 MemSearch 记忆直接当成事实。
5. 起草 `goal.md`、`plan.md` 和 `history.md`。先向用户展示摘要，只询问无法可靠推断且会改变行为的内容，通常是工作时间窗口和明确边界。
6. 用户确认后，调用单一入口注册项目：

```bash
<skill-directory>/scripts/perpetuum project add <project-path> \
  --name "<project-name>" \
  --agent <codex-or-claude> \
  --window "<HH:MM-HH:MM>"
```

7. 用确认后的内容替换自动生成的 `goal.md`、`plan.md`、`history.md`，再检查其他通信文件的标题和项目背景。
8. 启动服务并展示前端地址：

```bash
<skill-directory>/scripts/perpetuum start
```

## Goal 的要求

`goal.md` 不是一句口号。根据项目需要写清：

- 长期目标和为什么值得持续推进；
- 当前背景与已知进度；
- 可用环境、数据、服务、机器和其他资源；
- 禁止触碰的边界、成本底线、安全限制和业务约束；
- 在长期目标之外必须兼顾的具体要求；
- 什么证据能够说明进展真实、什么情况需要人类判断。

Explorer 后续产生的每一条具体工作统一称为 Task。

## 项目标识

默认项目 ID 由目录名和绝对路径哈希组成，避免同名目录冲突。全局 Harness 通过 `project.yaml` 中的绝对路径映射到实际项目，不创建镜像目录或软链接。
