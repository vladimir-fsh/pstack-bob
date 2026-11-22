# External seats

An **external seat** is a panel entry that runs on another vendor's CLI in place of a native subagent. The sheet writes it as `<cli>:<model>`, with the same `@<level>` effort suffix a native entry takes:

- `codex:<model>` runs GPT through Codex CLI.
- `claude:<model>` runs Claude through Claude Code CLI.

When the prefix names the host you are running on, the entry is a native seat: drop the prefix and dispatch it as usual. So `codex:sol` is external on Claude Code and native on Codex, and `claude:opus` is the reverse.

An external seat is a family of its own. It always differs from the parent's family, so it qualifies as an `arena` cross-judge and counts toward a panel's model diversity.

External seats belong to the four panel roles: `arena runners`, `arena cross-judge pool`, `interrogate reviewers`, and `thermos reviewers`. In any other role, say the entry is unsupported and use that role's default.

A seat that fails its check or its run is dropped and named in the output with the reason. Keep the calling skill's minimum panel size with the remaining seats. A dropped seat's work never reruns on a host model under the seat's name.

## Seat mode

| Role | Mode | The seat may |
| --- | --- | --- |
| `arena runners`, `interrogate reviewers` | worktree | write and run commands inside its own worktree |
| `arena cross-judge pool`, `thermos reviewers` | read-only | read files and nothing else |

## Brief

The seat starts with no history, so write the brief the native subagent would get to a file, in full: the task or scope, the intent, every path it needs as an absolute path, the repository rules that apply, where to put its output, and the reply format the calling skill asks for. Add two lines: the seat starts no subagents or reviewers, and a worktree seat leaves its changes uncommitted for the parent to commit.

For `thermos reviewers`, each pass's brief opens with the body of that reviewer's agent file, [bugs and security](../../../agents/thermo-nuclear-review-subagent.md) or [code quality](../../../agents/thermo-nuclear-code-quality-review-subagent.md).

Create one private temporary directory per seat and round. Set `brief`, `result`, `events`, and `log` to absolute paths inside it.

## Codex CLI seat

Check `codex --version` and `codex login status`. If logged out, tell the user to run `codex login` and drop the seat.

Resolve `<model>` against `codex debug models`, counting only slugs with `"visibility": "list"`. A family word (`sol`, `astra`, `terra`, `luna`) is the newest `gpt-*-<family>` slug listed. A full slug must be listed as written.

```bash
PSTACK_SESSION_HOOK=off codex exec --model "$model" \
  -c model_reasoning_effort='"<level>"' \
  --sandbox <read-only|workspace-write> -C "$dir" \
  --ephemeral --color never --json -o "$result" - \
  < "$brief" > "$events" 2> "$log"
```

- Read-only seat: `--sandbox read-only`, with `$dir` the repository root.
- Worktree seat: `--sandbox workspace-write`, with `$dir` the seat's worktree.
- Leave out the `-c model_reasoning_effort` line when the effort is `session`.
- `PSTACK_SESSION_HOOK=off` keeps a pstack install inside Codex from routing the seat into its own poteto-mode run.

The sandbox blocks the network, and in a worktree it blocks writes to the Git directory. A seat that needs either reports that in its reply.

`result` holds the seat's final message. The event stream in `events` does not name the model, so the seat's identity is the model and effort you requested.

## Claude Code CLI seat

Check `claude --version` and `claude auth status`. If logged out, tell the user to run `claude auth login` and drop the seat.

`<model>` is a family alias (`opus`, `fable`, `sonnet`, `haiku`) or a full model ID, passed as written.

```bash
cd "$dir" && claude --safe-mode -p --model "$model" --effort <level> \
  --tools '<tools>' --allowedTools '<tools>' \
  --permission-mode dontAsk \
  --strict-mcp-config --mcp-config '{"mcpServers":{}}' \
  --no-session-persistence --output-format json \
  < "$brief" > "$result" 2> "$log"
```

- Read-only seat: `<tools>` is `Read,Glob,Grep`, with `$dir` the repository root.
- Worktree seat: `<tools>` is `Read,Glob,Grep,Edit,Write,Bash`, with `$dir` the seat's worktree.
- Leave out `--effort` when the effort is `session`.
- `--safe-mode` skips hooks, plugins, skills, and project instructions, which is why the brief carries the repository rules.

The CLI needs the network. Inside Codex's sandbox the run fails with `Can't reach the API server`. Run this one command with escalated permissions. When the host cannot escalate, drop the seat and tell the user that `network_access = true` under `[sandbox_workspace_write]` in `~/.codex/config.toml` lets the seat run inside the sandbox.

`result` is JSON: the reply is in `result`, an error shows in `is_error` or `subtype`, and `modelUsage` names the model that ran. A model outside the one you requested is a failed seat.

## Lifecycle

Start every seat, native and external, before waiting on any of them. Run each external seat as a background process and keep its handle.

A seat is done when its process exited with status 0, `result` is non-empty, no error is recorded, and the reply has what the brief asked for. On a failure, read `log`, stop the process, and retry once in a fresh directory. A second failure drops the seat.

Later rounds start a fresh process with the earlier findings in the brief.
