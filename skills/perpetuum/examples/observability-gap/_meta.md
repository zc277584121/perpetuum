# Task metadata

- **task name**: <TASK_NAME>
- **created**: <YYYY-MM-DD>
- **worktree path**: <abs path>
- **branch**: <branch — strongly recommend a feature branch for this>
- **started from**: <branch>@<sha>
- **parent repo**: <abs path>
- **merge target**: <branch>
- **trigger type**: schedule
- **conventions doc**: <path to conventions.md, or inline below>

## Conventions for this codebase

<!-- Fill in before running. The agent reads this to keep additions
consistent. -->

- **Log library**: <e.g. slog | zap | structlog>
- **Log levels**:
  - DEBUG: <when>
  - INFO: <when>
  - WARN: <when>
  - ERROR: <when>
- **Metric library**: <e.g. prometheus | opentelemetry>
- **Metric naming**: <e.g. service.subsystem.event_unit>
- **Trace library**: <e.g. otel>
- **Span boundaries**: <which external calls deserve a span>
- **PII**: <fields never to log>
