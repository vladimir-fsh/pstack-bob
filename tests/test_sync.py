import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('sync', Path(__file__).resolve().parents[1] / 'scripts/sync_upstream.py')
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)


def commit(repo):
    sync.git('add', '.', cwd=repo)
    sync.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
             '-c', 'commit.gpgsign=false', 'commit', '--quiet', '-m', 'fixture', cwd=repo)
    return sync.git('rev-parse', 'HEAD', cwd=repo)


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'project'
        self.source = Path(self.temp.name) / 'source'
        self.root.mkdir()
        self.source.mkdir()
        sync.git('init', '--quiet', cwd=self.source)
        base = self.source / 'harness/pstack/claude-code'
        for name in ['poteto-mode', 'interrogate', 'setup-pstack']:
            path = base / 'skills' / name / 'SKILL.md'
            path.parent.mkdir(parents=True)
            path.write_text(f'---\nname: {name}\ndescription: Fixture\n---\n\n# Keep this upstream workflow\n')
        path = base / 'agents/poteto-agent.md'
        path.parent.mkdir()
        path.write_text('---\nname: poteto-agent\ndescription: Fixture\n---\n\nPersona\n')
        (base / 'docs/harness').mkdir(parents=True)
        (base / 'docs/harness/claude-code.md').write_text('Upstream adapter\n')
        (base / 'LICENSE').write_text('Fixture license\n')
        sync.write_json(base / 'plugin.json', {'version': '1.0.0'})
        executable = base / 'run.sh'
        executable.write_text('#!/bin/sh\nexit 0\n')
        executable.chmod(0o755)
        self.commit = commit(self.source)
        sync.write_json(self.root / 'upstream.json', {'repository': str(self.source), 'commit': self.commit,
                        'path': 'harness/pstack/claude-code', 'version': '1.0.0'})
        sync.write_json(self.root / 'package.json', {'name': 'pstack-bob', 'version': '0.1.0',
                        'description': 'Fixture', 'repository': 'https://example.invalid/plugin'})
        (self.root / 'adapters').mkdir()
        (self.root / 'adapters/bob.md').write_text('Local adapter\n')
        (self.root / 'config').mkdir()
        (self.root / 'config/models').write_text('interrogate reviewers: codex-default, opus\n')

    def run_sync(self, **kwargs):
        sync.sync(self.root, source=self.source, **kwargs)

    def test_repeatable_export_preserves_upstream_and_file_modes(self):
        self.run_sync()
        before = sync.snapshot(self.root / 'plugin')
        self.run_sync()
        self.run_sync(check=True)
        self.assertEqual(before, sync.snapshot(self.root / 'plugin'))
        self.assertEqual((self.root / 'plugin/LICENSE').read_text(), 'Fixture license\n')
        self.assertTrue((self.root / 'plugin/run.sh').stat().st_mode & 0o111)
        self.assertEqual((self.root / 'plugin/config/models').read_text(), (self.root / 'config/models').read_text())

    def test_check_detects_drift_without_repairing_it(self):
        self.run_sync()
        path = self.root / 'plugin/skills/interrogate/SKILL.md'
        path.write_text('local change')
        with self.assertRaisesRegex(ValueError, 'differs'):
            self.run_sync(check=True)
        self.assertEqual(path.read_text(), 'local change')

    def test_update_pins_new_commit_and_keeps_local_adapter(self):
        self.run_sync()
        path = self.source / 'harness/pstack/claude-code/skills/interrogate/SKILL.md'
        path.write_text(path.read_text() + '\nNew upstream behavior\n')
        latest = commit(self.source)
        self.run_sync(ref=latest)
        self.assertEqual(sync.read_json(self.root / 'upstream.json')['commit'], latest)
        self.assertIn('New upstream behavior', (self.root / 'plugin/skills/interrogate/SKILL.md').read_text())
        self.assertEqual((self.root / 'plugin/docs/harness/bob.md').read_text(), 'Local adapter\n')

    def test_dirty_generated_tree_is_preserved(self):
        self.run_sync()
        sync.git('init', '--quiet', cwd=self.root)
        commit(self.root)
        path = self.root / 'plugin/LICENSE'
        path.write_text('uncommitted work')
        with self.assertRaisesRegex(ValueError, 'uncommitted'):
            self.run_sync()
        self.assertEqual(path.read_text(), 'uncommitted work')

    def test_ignored_local_files_are_preserved(self):
        self.run_sync()
        sync.git('init', '--quiet', cwd=self.root)
        (self.root / '.gitignore').write_text('*.local\n')
        commit(self.root)
        path = self.root / 'plugin/notes.local'
        path.write_text('local evidence')
        with self.assertRaisesRegex(ValueError, 'uncommitted'):
            self.run_sync()
        self.assertEqual(path.read_text(), 'local evidence')

    def test_changed_layout_does_not_replace_existing_plugin(self):
        self.run_sync()
        before = sync.snapshot(self.root / 'plugin')
        (self.source / 'harness/pstack/claude-code/docs/harness/claude-code.md').unlink()
        latest = commit(self.source)
        with self.assertRaisesRegex(ValueError, 'layout changed'):
            self.run_sync(ref=latest)
        self.assertEqual(before, sync.snapshot(self.root / 'plugin'))
        self.assertEqual(sync.read_json(self.root / 'upstream.json')['commit'], self.commit)


if __name__ == '__main__':
    unittest.main()
