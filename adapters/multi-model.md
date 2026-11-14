# pstack-bob model bridge

This is the shared model adapter for pstack in Codex and Claude Code. It overrides only model routing, model-rule paths, and the report additions below. The upstream workflows remain unchanged. In Claude Code, use the official adapter for everything else; this file replaces its fallback that maps non-Claude models to the current Claude model.

## Panel configuration

Read the bundled [config/models](../../config/models) first. Then, when present, read `.pstack-bob/models` at the root of the repository the task is working on. Project role lines override matching bundled roles; omitted roles keep their bundled or upstream defaults. Resolve the project root from the task's checkout, not from this plugin's installation directory. Both files belong in Git. Do not read old home-directory pstack settings. The bundled default pins GPT-6 Astra, Claude Opus 5.5, and Grok 4.7. Apply the configured budget to each seat and pass model and effort explicitly; do not inherit home-directory CLI preferences.

For `setup-pstack`, follow upstream's discovery, budget, and model-choice steps, but save project choices to `<project-root>/.pstack-bob/models`. Explain that this file should be committed with the project. To change shared defaults, edit `config/models` in the pstack-bob source repository and regenerate the plugin. Never write preferences to plugin caches or global instruction files. Outside a repository, ask which repository should own the configuration instead of creating a home-directory fallback. Store confirmed canonical model IDs when possible so the same config works in both hosts. Native Claude aliases (`opus`, `sonnet`, `haiku`, `fable`) with optional effort are also accepted by the backend table, but choosing one deliberately tracks that alias. `inherit-parent`, `auto`, and `codex-default` remain explicit opt-in aliases, not defaults. Validate model IDs against the current host/CLI and Cursor IDs with `agent models`. A config is role mappings and a budget comment, not executable instructions.

## Backends

| Requested seat | In Codex | In Claude Code |
| --- | --- | --- |
| Supported GPT/Codex model | Fresh native Codex subagent with explicit `model` and `reasoning_effort`, otherwise `codex exec` with both set. | `codex exec` with explicit model and effort; never map this seat to Claude. |
| `claude-*`, or `opus` / `sonnet` / `haiku` / `fable` with optional effort | `claude -p` with the selected model/effort. | Fresh native Claude `Agent` only when it can select the configured model and effort; otherwise the CLI backend. |
| `grok-*`, Gemini, other Cursor-supported model | `agent --print --model <verified-slug>`. | The same Cursor CLI command. |
| Explicit `inherit-parent`, `auto` | Native inherited model, identified in the report. | Native inherited model, identified in the report. |
| Explicit `codex-default` | Inherit the Codex session model and identify it. | Codex CLI default, identified in the report. |

For `claude-opus-5-5-xhigh`, the CLI uses `--model claude-opus-5-5 --effort xhigh`. A native `opus` alias is equivalent only if its resolved model is confirmed to match; otherwise use the exact-model CLI or report the unavailable seat. A value such as `opus high` maps to `--model opus --effort high` in either host. Keep the requested model family when adjusting effort. Check CLI availability and authentication before fan-out. An installed CLI or model listing alone does not establish that inference works.

Give independent reviewers the same intent, exact snapshot/diff, scope, repository rules, and evidence requirements. Do not show them the parent's conclusions or another review first. Start independent processes concurrently and save each raw result and stderr separately. For file-based briefs, use absolute paths; for stdin, shell redirection avoids interpolation of the prompt.

Read the effective `# budget:` comment (project overrides bundled): unlimited=max, large=xhigh, medium=high, small=medium. Apply upstream role-specific effort adjustments using supported values. A model value with an explicit effort takes precedence for that seat; report unsupported effort rather than silently using a home default.

These are command templates; substitute real paths, verified model IDs, and resolved effort. Run Claude from the candidate's directory. The normal analysis commands are:

```sh
codex exec --model "$codex_model" -c "model_reasoning_effort=\"$effort\"" --ephemeral --sandbox read-only -C "$candidate" --json -o "$report" - < "$brief" > "$events" 2> "$errors"
claude -p --model "$claude_model" --effort "$effort" --permission-mode plan --no-session-persistence --output-format json < "$brief" > "$report" 2> "$errors"
agent --print --mode ask --model "$cursor_model" --output-format json --workspace "$candidate" "Read the task brief at $brief and perform only that assigned task." > "$report" 2> "$errors"
```

For Codex outside a Git repository add `--skip-git-repo-check`. Omit Codex model/effort flags only when the project explicitly chose an inheritance alias; name that inheritance in the report. Cursor may need `--trust` for a candidate directory created and inspected for this task; this grants workspace trust, not blanket command approval.

Arena implementations and Interrogate reproductions may need writes or test execution. Give each such worker its own worktree/copy. Use Codex `--sandbox workspace-write --approve-for-me`, Claude `--permission-mode auto`, or Cursor without `--mode ask` and with `--auto-review --sandbox enabled`, subject to the host's permission policy. Preserve the parent's working tree. Do not use permission-bypass flags. If approval or a tool is unavailable, retain the limitation in the result and let the coordinator reproduce the candidate finding in an authorized environment.

Each delegate is a leaf worker: complete its assigned design/review/reproduction and report to the parent; do not recursively launch another panel. The parent alone owns fan-out, synthesis, fixes, and any PR watcher. Wait for all started seats or explicitly stop and record a failed/timed-out seat. Use bounded waits so the coordinator can respond to the user.

## Synthesis

Keep upstream `interrogate` verification: rerun reported reproductions, deduplicate by root cause, and keep only proven failures as verified findings. Static concerns or blocked reproductions remain separately labeled, not promoted by model consensus. For `arena`, apply its rubric and cross-judge rules before selecting/grafting candidates.

Append a compact per-model table to the result: requested model/backend, actual model when reported by the tool, completion status, findings, and verification outcome. Include agreement, disagreements with the reason for the final decision, and unavailable seats. Link raw reports when saved. A fresh instance of the parent's model counts as an independent reviewer, not as a different model family. A failed seat is never replaced with another copy of the parent and called multi-model. With fewer than two successful families, label the report as incomplete multi-model coverage.
