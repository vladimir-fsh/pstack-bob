# pstack-bob

[pstack](https://github.com/cursor/plugins/tree/main/pstack) workflows for Codex and Claude Code, with independent Codex, Claude, and Grok review seats. The original playbooks stay upstream; a small adapter maps tools, model routing, and configuration to the current host.

Codex can call Claude Code, Claude Code can call Codex, and either can call Grok through Cursor CLI. Review reports identify each seat, failed calls, disagreements, and reproduced findings. Repeating one model does not count as different model families.

## Install

Once this repository is published at `vladimir-fsh/pstack-bob`:

```sh
# Codex
codex plugin marketplace add vladimir-fsh/pstack-bob
codex plugin add pstack-bob@pstack-bob

# Claude Code
claude plugin marketplace add vladimir-fsh/pstack-bob
claude plugin install pstack-bob@pstack-bob --scope user
```

For local development, replace `vladimir-fsh/pstack-bob` with the absolute path to this checkout. Keep only one pstack variant enabled in each host to avoid duplicate skills. Start a new session after changing the installation.

In Codex, select the `pstack-bob` plugin's `poteto-mode` or `interrogate` skill. In Claude Code, use `/pstack-bob:poteto-mode <task>` or `/pstack-bob:interrogate <scope>`.

Authenticate the CLIs needed by your panel: `codex`, `claude`, and Cursor's `agent`. A model listing does not prove inference access. Native subagents are preferred for the host's own models. External seats use CLI calls with task-scoped permissions and isolated workspaces when they need to write. Failed seats remain visible in the report.

## Configuration in Git

- [config/models](config/models) holds shared defaults. Edit it here, regenerate, and commit the result.
- A project's `.pstack-bob/models` overrides matching roles for that project. `/setup-pstack` writes there; commit it with the project.
- No model preferences live in a home-directory config or a plugin cache.

The default review/design panel pins GPT-6 Astra, Claude Opus 5.5, and Grok 4.7. Models and effort are passed explicitly; session-default aliases are opt-in. Other role defaults remain upstream. Model changes use detected IDs and preserve the selected family; a failed external seat is not silently replaced by the coordinator.

## Source and generated files

| Path | Purpose |
| --- | --- |
| `upstream.json` | Exact upstream commit, source subtree, and upstream version |
| `adapters/` | Our host and multi-model instructions; edit these |
| `config/models` | Shared model choices |
| `package.json` | Our plugin name and release version; no npm dependencies |
| `scripts/sync_upstream.py` | Export the pinned upstream subtree and apply the small adaptation |
| `plugin/` | Generated, committed installation artifact for both hosts |

The generator preserves upstream files, adds an adapter pointer to skill/persona entrypoints, copies our adapters/config, and writes the plugin manifests. It does not rewrite upstream playbooks. Upstream's MIT license remains in `plugin/LICENSE`; this repository preserves the license too. The generated artifact is committed because GitHub plugin installation does not run a build step.

## Regenerate and update

Requires Git and Python 3.9+. No package installation is needed. Start with a clean `plugin/`; the generator refuses to overwrite uncommitted changes there.

```sh
# Rebuild exactly the pinned upstream version after editing adapters/config.
python3 scripts/sync_upstream.py

# Check the generated artifact without modifying it.
python3 scripts/sync_upstream.py --check

# Import a newer upstream version, resolving main to an exact commit in the lock.
python3 scripts/sync_upstream.py --ref main
git diff --stat
git diff -- upstream.json plugin/
```

Review the upstream changes and adapter compatibility. Commit the reviewed import. For a release, bump our `package.json` version, regenerate, validate, and commit before pushing. Our version is independent of the upstream version. Updating upstream never publishes a release or modifies installed plugins automatically.

For an existing upstream checkout or offline work, add `--source /absolute/path/to/cursor-plugins`. Without `--ref`, its working tree is ignored and the pinned commit is exported. A new source layout or adapter filename collision fails before replacing the installed artifact.

## Validation

```sh
python3 -m unittest discover -s tests -v
python3 scripts/sync_upstream.py --check
claude plugin validate .
claude plugin validate plugin
```

The offline regression tests exercise repeatable generation, changed upstream content, drift detection, and preservation of local edits. CI also regenerates from the pinned upstream commit. For a routing change, separately run a small real task through each configured backend and verify the result. Structural checks alone do not prove authentication, model availability, runtime behavior, or PR readiness.
