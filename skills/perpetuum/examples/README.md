# Examples

Each subdirectory here is a fully-formed `.perpetuum/<task>/` template
that an agent can copy into a user's project as a starting point.

| Example | Task shape | Trigger type |
|---|---|---|
| `adversarial-testing/` | "Find bugs and improvements in a project, multi-dimensional exploration, commit fixes, escalate ambiguous design questions" | schedule |
| `github-watcher/` | "Watch new issues/PRs on a repo, process each as it appears" | conditional |
| `style-distill/` | "Iteratively rewrite a draft article to converge on a target author's style" | schedule + scalar oracle |
| `article-polish/` | "Reread a single document repeatedly and improve one paragraph per cycle" | schedule |
| `observability-gap/` | "Scan codebase for missing logs / metrics / error paths" | schedule |

When picking an example, look at the **shape** of the task, not the
domain. A task about polishing API documentation is closer to
`article-polish` than to `adversarial-testing`, even though both
involve a codebase.

## Anatomy of an example

Each example contains the full set of files a `.perpetuum/<task>/`
directory needs:

```
<example>/
├── README.md            describes the task shape and what to customize
├── _meta.md             template with placeholders
├── trigger.sh           customized for this task type
├── prompts/
│   ├── 1_explore.md     prompt 1 customized for this task
│   └── 2_execute.md     prompt 2 customized for this task
├── plan.md              empty skeleton
├── inbox.md             empty skeleton
└── escalations.md       empty skeleton
```

When the user picks an example during `references/setup.md`, copy the
entire directory and adapt each file. The README in each example tells
you exactly what to change.

## Adding a new example

If you find a recurring task shape that doesn't fit existing examples,
add one. The bar:

- It must pass the suitability gate (`references/setup.md` describes it)
- Its `prompts/1_explore.md` and `prompts/2_execute.md` should be 80%+ reusable for the
  task family, with only the domain-specific section needing customization
- It must demonstrate at least one *distinct* idea (different trigger
  type, different oracle, different escalation pattern)

Don't add an example just because it's a different domain — that's
just a customization of an existing example.
