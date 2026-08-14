# 初始化项目

## 前置检查

初始化只收集信息和建立 Harness，不负责安装或升级 Agent、模型或认证环境。先确认：

- 当前 Agent 能加载 `perpetuum` 与必须依赖的 `cc-use` Skill；
- `uv` 与 `tmux` 可用；
- 对应的交互式 Codex 或 Claude Code TUI 可启动；
- MemSearch 是可选依赖；可用时检索历史，不可用时直接跳过。

不要在初始化过程中更新 Codex、Claude Code、模型或认证配置。版本不兼容时说明现状和影响，让用户决定是否另行处理。

## 初始化步骤

1. 解析用户指定或当前所在的项目目录，取得绝对路径。
2. 默认继承当前调用 Perpetuum 的 Agent 类型。只有用户明确要求时才覆盖。
3. 若 MemSearch 可用，检索项目历史目标、近期进展、用户偏好、资源、边界、已做决定和可能的下一步；再用项目文件和可验证证据复核。
4. 在对话中起草完整初始化契约，不提前在运行时目录创建半成品 Harness。
5. 至少确认项目名称与目录、长期 Goal、背景和进度、资源与权限、边界与底线、进展证据、时间窗口，以及长期目标之外必须兼顾的要求。
6. 根据这些信息起草第一批 Story。每张 Story 必须有标题、摘要、优先级、标签、背景、边界和验收标准；不要把环境检查、下载、单次 smoke 或其他纯步骤单独建成 Story。
7. 对无法可靠推断、互相矛盾或会改变行为的内容逐项询问。用户回答后重新给出合并后的完整摘要；只有用户明确确认 `goal.md`、初始 Story 和运行配置后才能继续。
8. 调用项目注册入口：

```bash
<skill-directory>/scripts/perpetuum project add <project-path> \
  --name "<project-name>" \
  --agent <codex-or-claude> \
  --window "<HH:MM-HH:MM>"
```

9. 用确认后的内容替换 `goal.md` 和 `history.md`，再通过 Story 接口创建全部初始卡片。注册完成时应该至少存在一张 `ready` Story；如果用户明确确认项目当前应当 Idle，可以没有 `ready` Story，但必须在最终摘要中说明。
10. 复核 Story 列表只返回元数据，逐张抽查正文和 front matter；确认没有遗留 `plan.md` 作为第二事实来源。
11. 启动服务并展示前端地址。若配置地址已经运行同一运行时目录的 Perpetuum 前端，直接复用，不重启，也不另选端口：

```bash
<skill-directory>/scripts/perpetuum start
```

若端口被其他服务或不同运行时目录的 Perpetuum 占用，停止并向用户说明冲突；不要擅自结束该服务、重启它或自动换端口。

注册结果只在 `project.yaml` 中记录 Agent 类型。不要把 shell alias、可执行文件绝对路径、权限参数或 cc-use 运行参数写入项目配置；这些由 Runner 和 cc-use 各自统一管理。

## 注册确认门槛

“用户说了一个长期方向”不等于已经授权建立 Harness。初始化 Agent 必须让用户能够看清最终会长期执行什么、第一批 Story 是什么、使用哪些资源、在什么时间运行、哪些边界不能越过，以及用什么证据判断进展。

用户尚未确认时，把草稿保留在当前对话中，不写入 `~/.perpetuum/projects/`。用户修改任一关键内容后，重新给出合并后的完整摘要并再次确认。

## Goal 的要求

`goal.md` 不是一句口号。根据项目需要写清长期目标、当前背景、可用资源、禁止触碰的边界、成本和安全底线、长期有效的特殊要求，以及什么证据能够说明真实进展。

Goal 不保存 Story 列表。具体业务工作统一保存在 `stories/*.md`；执行过程中的步骤不进入全局 Story 模型。
