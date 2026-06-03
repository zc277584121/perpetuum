# perpetuum

> An "**explore → execute → escalate**" loop framework that lets a coding agent
> work on the same kind of task across sessions, across days, across weeks —
> without spinning out, without losing memory, without locking you in front
> of the screen.

中文叫 **永动机**——名字是个 ironic 的自嘲:物理上永动机不可能存在,但只要把
"循环驱动"、"决策探索"、"任务执行" 三件事分离、把人类介入做成异步分叉、把
状态全部物化进文件系统,agent 就真的可以"永远"工作下去。

## What it is

`perpetuum` is an [Agent Skill](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)
that turns *any* task with the shape:

> "find more of X / make it closer to Y / keep watch for Z, **and report back the things only I can decide**"

…into a three-layer loop that the host coding agent (Claude Code, Codex CLI,
or any compatible TUI agent) can configure, launch, supervise and control —
all by talking to it in natural language.

Typical fits:

- adversarial testing / fuzz / vulnerability hunting
- documentation polish, error-message tightening, observability gap scanning
- writing-style distillation against a reference corpus
- watching GitHub issues / PRs / external feeds and acting on changes
- API surface auditing for naming/signature consistency

It is *not* a fit for one-shot tasks, strongly linear builds, or anything that
needs a human to make the very next decision. See
[`skills/perpetuum/references/setup.md`](skills/perpetuum/references/setup.md)
for the suitability gate the skill walks the user through before initializing.

## Architecture in one picture

```
┌──────────────────────────────────────────────────────────────┐
│ Layer 4   the host agent you are talking to                  │  optional
│           (it called this skill, it can monitor + relay)     │  ← human-friendly
└────────────────────────┬─────────────────────────────────────┘
                         │ spawns
┌────────────────────────▼─────────────────────────────────────┐
│ Layer 3   trigger.sh — schedule / conditional / webhook      │  ← stupid heartbeat
└────────────────────────┬─────────────────────────────────────┘
                         │ pastes prompt into
┌────────────────────────▼─────────────────────────────────────┐
│ Layer 2   middle agent (persistent CC TUI in tmux)           │  ← smart explorer +
│           reads plan + inbox + escalations history           │     judge + dispatcher
│           dispatches, judges, records, escalates             │
└────────────────────────┬─────────────────────────────────────┘
                         │ cc-use delegate
┌────────────────────────▼─────────────────────────────────────┐
│ Layer 1   inner agent (fresh-context CC)                     │  ← stupid worker,
│           does the actual work this round, reports back      │     no priors
└──────────────────────────────────────────────────────────────┘
```

Everything is files. State, memory, signals, history, human input — all
markdown + git + tmux + a couple of `touch` flags. No vector DB, no
framework, no daemon, no agent SDK.

## Install

```bash
# Clone this repo and link the skill into your skills directory
git clone https://github.com/zilliztech/perpetuum  ~/perpetuum
ln -s ~/perpetuum/skills/perpetuum  ~/.claude/skills/perpetuum

# Or copy if you prefer not to symlink
cp -r ~/perpetuum/skills/perpetuum  ~/.claude/skills/perpetuum
```

If your agent host supports the community
[`skills`](https://www.npmjs.com/package/skills) installer:

```bash
npx skills install zilliztech/perpetuum
```

After installation, Claude Code users can do `/reload-skills` to pick it up
without restarting the TUI. Other agents may need to restart — check your
agent docs.

**Dependency: `cc-use`.** `perpetuum` requires the
[`cc-use`](https://github.com/anthropics/skills) skill (or equivalent) to be
installed because Layer 2 uses it to dispatch to Layer 1. The skill checks at
init time and prompts you to install if missing.

## Quick start

Inside any project directory, in your host agent:

> I want to use perpetuum to run continuous adversarial testing on this
> project — find bugs and improvements over the next few days.

The agent will:

1. Read this skill, check `cc-use` + `tmux` are installed
2. Walk you through the **suitability gate** (is this really a perpetuum task?)
3. Pick the closest example from `skills/perpetuum/examples/`
4. Materialize `.perpetuum/<task-name>/` in your project with the right files
5. Show you what's in there and how to control it
6. Start it (or let you start it manually)

Then you can leave it running for hours/days. Come back, read `plan.md`, answer
anything new in `escalations.md`, optionally write a one-liner into `inbox.md`
to nudge it, repeat.

## What's inside this repo

```
perpetuum/
├── README.md                          ← you are here
├── LICENSE
└── skills/
    └── perpetuum/                     ← the actual skill
        ├── SKILL.md                   ← entry point the agent reads
        ├── scripts/                   ← shared helpers
        ├── examples/                  ← copy-as-starting-point templates
        │   ├── adversarial-testing/
        │   ├── github-watcher/
        │   ├── style-distill/
        │   ├── article-polish/
        │   └── observability-gap/
        └── references/                ← deep-dive docs, loaded on demand
            ├── setup.md               ← initialize a new task
            ├── control.md             ← pause / resume / stop
            ├── feedback.md            ← inbox / escalations
            ├── status.md              ← see what's running
            ├── worktree.md            ← parallel lines via git worktree
            ├── trigger.md             ← writing trigger.sh per task
            └── design.md              ← 8 ideas the design is built from
```

## How it works — 8 ideas combined

`perpetuum` is the combination of eight ideas that, individually, are not
new. None of the existing projects we know of combine all eight. See
[`references/design.md`](skills/perpetuum/references/design.md) for the
full discussion. In short:

| Idea | Source / inspiration |
|---|---|
| Discriminator / Generator separation | GANs (Goodfellow 2014) |
| Monotonic ratchet (only-better commits) | Coverage ratchet, `recursive-improve`, [Karpathy AutoResearch](https://github.com/karpathy/autoresearch) |
| Three-layer architecture (stupid → smart → stupid) | This project |
| Exploration vs Exploitation prompt split | RL theory; operationalized via two-prompt sequence here |
| File-based persistent memory | [Karpathy AutoResearch](https://github.com/karpathy/autoresearch), [Ralph Loop](https://ghuntley.com/loop/) |
| Asynchronous human escalation | This project (existing skills assume sync human-in-loop) |
| Trigger abstraction (schedule / conditional / webhook) | This project |
| File-as-contract (who can change what) | [Karpathy AutoResearch](https://github.com/karpathy/autoresearch) |

## About `cc-use`

[`cc-use`](https://github.com/anthropics/skills) is a separate skill (by
@anthropics) that lets an outer coding-CLI agent (Claude Code, Codex CLI)
spawn and supervise an *inner* coding-CLI agent in a tmux session. The outer
agent stays focused on planning and judgment; the inner agent does focused
execution; the two communicate by observing the tmux pane.

Perpetuum's Layer 2 uses `cc-use` to dispatch each test/finding/operation to
Layer 1 as a fresh-context request. This is what gives perpetuum its
"exploration independence" — Layer 1 has no memory of what the project is
"supposed to" look like, so it can't accidentally validate away genuine
problems the way a context-saturated agent would.

If you're not familiar with `cc-use`, the
[cc-use SKILL.md](https://github.com/anthropics/skills/blob/main/skills/cc-use/SKILL.md)
is a good 10-minute read.

## Prior art

- [Ralph Loop / Ralph Wiggum](https://ghuntley.com/loop/) — bash `while true`
  loop around a coding agent; the spiritual ancestor.
- [Karpathy AutoResearch](https://github.com/karpathy/autoresearch) — three-file
  contract + scalar metric + git ratchet, the cleanest single-loop instance.
- `recursive-improve`, `SkillOpt`, EvoSkills, Darwin Gödel Machine — self-evolving
  agent lines that get deeper on the model/framework side; perpetuum stays light
  but adds the human and trigger axes.
- Persona-distillation skills like `nuwa-skill`, `ex-skill`,
  `migueldeguzman/persona` — single-shot persona extraction; perpetuum makes
  the loop that lets such distillation actually converge.

## License

MIT — see [LICENSE](LICENSE).
