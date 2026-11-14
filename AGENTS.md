# pstack-bob development

Edit `adapters/`, `config/models`, and `scripts/`. `plugin/` is generated and committed for direct plugin installation; regenerate it instead of editing it by hand. Keep upstream playbooks unchanged unless the task explicitly calls for a workflow change.

`upstream.json` pins the official `cursor/plugins` source. Update it through `scripts/sync_upstream.py --ref <commit-or-ref>` and inspect the generated diff. Bump `package.json` for a published plugin release, then regenerate its manifests.

Run `python3 -m unittest discover -s tests -v` and `python3 scripts/sync_upstream.py --check`; use `--source <upstream-checkout>` for offline checks. Validate marketplace and plugin manifests with `claude plugin validate .` and `claude plugin validate plugin` when the CLI is available.

Model preferences belong in Git: shared defaults in `config/models`, project overrides in the task repository's `.pstack-bob/models`. Keep machine paths, credentials, and personal authentication state out of the plugin.
