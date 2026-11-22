# pstack-bob

[pstack](https://github.com/cursor/plugins/tree/main/pstack) for Claude Code and
Codex, where a review panel can include the other vendor's model. From Claude
Code, GPT runs through Codex CLI. From Codex, Claude runs through Claude Code
CLI.

`plugin/` started as [michael-denyer/pstack-claude](https://github.com/michael-denyer/pstack-claude)
at commit `b1b9f18`, which had already translated pstack for both hosts. From
there this repository merges Cursor's upstream itself.

## What it adds

An **external seat** is a panel entry written `codex:<model>` or
`claude:<model>`. It runs as a background CLI process in place of a native
subagent, read-only or inside its own worktree.

| Role | Default from Claude Code |
| --- | --- |
| `arena runners` | `opus`, `fable`, `codex:sol`, `codex:astra` |
| `arena cross-judge pool` | `codex:astra`, `codex:sol`, `fable`, `opus` |
| `interrogate reviewers` | `opus`, `fable`, `codex:sol`, `codex:astra` |
| `thermos reviewers` | `opus` |

From Codex the same defaults run Astra and Sol natively and add `claude:opus`
and `claude:fable`. A seat whose CLI is missing or logged out is dropped and
named in the output. Its work never reruns on a host model under its name.
`setup-pstack` changes any of this.

The rules live in
[external seats](plugin/skills/poteto-mode/references/external-seats.md).

## Install

Claude Code:

```bash
claude plugin marketplace add vladimir-fsh/pstack-bob
claude plugin install pstack@pstack-bob --scope user
```

Codex:

```bash
codex plugin marketplace add vladimir-fsh/pstack-bob
codex plugin add pstack@pstack-bob
```

Enable one pstack build per host, since they share skill names. In Codex, trust
the plugin's hook through `/hooks`. Start a new session, then run
`setup-pstack`.

External seats need the other CLI logged in: `codex login` for Claude Code,
`claude auth login` for Codex.

## How it stays current

| Path | Purpose |
| --- | --- |
| `plugin/` | The plugin both hosts install. This is the source; edit it directly |
| `upstream.json` | The `cursor/plugins` commit last merged, and the upstream paths left out |
| `substitutions.json` | Rewrites from Cursor's wording to this plugin's, plus Cursor terms to flag |
| `scripts/sync.py` | Merges a newer upstream commit into `plugin/` |

A sync translates each upstream file at the old pin and at the new commit, then
merges the difference into the local file with a three-way merge. An edit made
here survives unless upstream changed the same lines. Then the file is written
with Git's conflict markers and listed in the report.

A daily workflow runs the sync against upstream's `main` and opens a pull
request with the report. It opens a draft when something needs a person: a
conflict, a file both sides changed in incompatible ways, Cursor wording no rule
covers, or a rule that matches nothing. Upstream commits that touch none of the
carried files open nothing. The workflow needs "Allow GitHub Actions to create
and approve pull requests" under the repository's Actions settings.

```bash
python3 scripts/sync.py              # merge upstream's main into plugin/
python3 scripts/sync.py --ref <sha>  # merge a specific commit
python3 scripts/sync.py --check      # fail on unresolved conflicts
python3 -m unittest discover -s tests
```

Requires Git and Python 3.12 or later.

## License

[MIT](LICENSE). Original pstack © Lauren Tan. Port © Michael Denyer. The
bundled cursor-team-kit and thermos skills © Cursor, under the notices in
`plugin/skills/poteto-mode/references/licenses/`.
