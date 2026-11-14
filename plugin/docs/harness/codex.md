# pstack-bob in Codex

Read this adapter once per session when using pstack in Codex. Keep the upstream playbooks and principles; translate only the host-specific operations below. User instructions, repository rules, and host permissions take precedence over pstack's autonomy language. Installing or invoking pstack alone does not authorize messages to others, merging, or deployment.

| Cursor operation | Codex equivalent |
| --- | --- |
| Run a pstack skill | Read `skills/<name>/SKILL.md` in this plugin. For a user invocation, use `$poteto-mode`, `$interrogate`, or the skill picker. |
| `Task` | Native `collaboration.spawn_agent` for a supported Codex model, or the CLI backend in [multi-model.md](multi-model.md). Use only parameters the current tool exposes. |
| `poteto-agent` | A fresh native agent with the absolute path to `skills/poteto-mode/SKILL.md` and instructions to read it, this adapter, and the scoped task. Keep the parent as coordinator. |
| `generalPurpose`, `comment-sicko` | A fresh native agent with the corresponding task or bundled agent brief; these are prompts, not Codex agent types. |
| `run_in_background`, `resume` | Native agents are asynchronous. Retain their IDs; send messages or follow-ups only when upstream permits reuse. For CLIs retain process IDs and logs. |
| `AskQuestion` | The current host's question tool; use a plain question only if no such tool exists. |
| Todolist | Available plan tool, or a concise checklist when no plan tool exists. |
| Cloud agent / isolated candidate | The host's worktree tool when available, otherwise a separate local copy for each writer. Include relevant uncommitted changes. |
| Read-only agent | A read-only brief and matching CLI mode; native agents share the filesystem, so give writers separate locations. |
| `.cursor/skills`, transcript search | Use the installed Codex skill paths and this project's Codex chat tools. Do not search another host's history. |
| `create-skill` | The installed `skill-creator` skill. |
| `deslop` | Inspect the current diff and remove redundant scaffolding manually if the skill is absent. |
| `control-ui`, `control-cli` | Available browser/computer tools or terminal commands that demonstrate the same behavior. |
| Cursor-only automations or cloud dashboard | Report the unsupported step; continue independent work. Do not invent a substitute scheduled task. |
| PR operations | GitHub connector or `gh`, respecting repository rules and the user's requested scope. |

Before choosing delegates or reviewers, read [multi-model.md](multi-model.md). It overrides Cursor model paths and same-model fallbacks, including when invoking `setup-pstack`. Native model overrides require a fresh context (`fork_turns="none"`) when the current tool schema says so. Ordinary inherited-model delegates may inherit context; independent reviewers receive only the shared review brief.

Use upstream verification and shipping gates. When a required check is unavailable, report the missing evidence rather than treating the skipped step as passed. Keep waiting processes owned by the active task; ending a turn does not arrange a future wakeup.
