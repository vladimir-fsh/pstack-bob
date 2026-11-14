# pstack-bob host adapter

Apply this adapter before upstream instructions in this plugin. User instructions, repository rules, and host permissions still take precedence. Invoking a workflow is not itself authorization to send messages, merge, or deploy.

- In Codex, read [codex.md](codex.md).
- In Claude Code, read [claude-code.md](claude-code.md), then [multi-model.md](multi-model.md). The latter overrides upstream model routing and setup paths, particularly the non-Claude-to-parent fallback.
- In either host, run bundled skills by reading this plugin's `skills/<name>/SKILL.md`. In Claude Code, user-facing commands and agent names use `pstack-bob:` instead of `pstack:`. Thus `/pstack:poteto-mode` becomes `/pstack-bob:poteto-mode`, and `pstack:poteto-agent` becomes `pstack-bob:poteto-agent`.

The parent gives every delegate the absolute path to this adapter and the relevant bundled skill or persona. Resolve the plugin from that supplied path; do not select a different installed copy by scanning Cursor's cache. Models and panel results follow [multi-model.md](multi-model.md). Global rules from a previous pstack installation do not override this plugin's adapter.
