# pstack-bob

[pstack](https://github.com/cursor/plugins/tree/main/pstack) for Claude Code and
Codex, where a review panel can include the other vendor's model. From Claude
Code, GPT runs through Codex CLI. From Codex, Claude runs through Claude Code
CLI.

It is [michael-denyer/pstack-claude](https://github.com/michael-denyer/pstack-claude)
at a pinned commit, plus a short list of edits. That port already translates
pstack for both hosts and tracks Cursor's upstream, so this repository carries
only the difference.

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
[external seats](overlay/skills/poteto-mode/references/external-seats.md).

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
| `upstream.json` | The pinned commit of the port, and the folders left out |
| `patches.json` | Edits to upstream text, each with its reason |
| `overlay/` | Files added beside upstream's |
| `VERSION` | This plugin's version |
| `scripts/build.py` | Renders `plugin/` from the four above |
| `plugin/` | The generated plugin both hosts install |

Each patch names an anchor sentence that must occur exactly once. When upstream
rewords one, the build fails and names the rule.

A daily workflow moves the pin to upstream's `main`, renders again, and opens a
pull request. A failed run means a patch needs rewording. The workflow needs
"Allow GitHub Actions to create and approve pull requests" under the
repository's Actions settings.

```bash
python3 scripts/build.py            # render plugin/ from the pin
python3 scripts/build.py --check    # fail when plugin/ is stale
python3 scripts/build.py --ref main # move the pin and render
```

Requires Git and Python 3.12 or later.

## License

[MIT](LICENSE). Original pstack © Lauren Tan. Port © Michael Denyer. The
bundled cursor-team-kit and thermos skills © Cursor, under the notices in
`plugin/skills/poteto-mode/references/licenses/`.
