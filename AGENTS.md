# pstack-bob

`plugin/` is the source. Edit its files directly.

`scripts/sync.py` merges Cursor's upstream into it. It translates each upstream
file with `substitutions.json` at the old pin and at the new commit, then merges
the difference into the local file, so an edit here survives a sync unless
upstream changed the same lines.

When a sync reports a conflict, the file holds Git's `<<<<<<< ours`,
`=======`, and `>>>>>>> upstream` markers. Keep upstream's new meaning in this
plugin's wording: Claude Code and Codex tool names, family model names, and
external seats. `scripts/sync.py --check` fails while a marker remains.

When a sync reports Cursor wording, add a rule to `substitutions.json` if the
phrase will recur, or rewrite the sentence in `plugin/` if it will not. A rule
that matches nothing upstream is stale: delete it.

Raise the version in both `plugin/.claude-plugin/plugin.json` and
`plugin/.codex-plugin/plugin.json` for a change of ours. A sync raises it.
