#!/usr/bin/env python3
"""Render the installable plugin from a pinned upstream commit and local adapters."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def git(*args, cwd=None):
    return subprocess.check_output(['git', *args], cwd=cwd, text=True).strip()


def read_json(path):
    return json.loads(path.read_text())


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


def snapshot(path):
    result = {}
    for item in sorted(path.rglob('*')):
        if item.is_symlink():
            result[str(item.relative_to(path))] = ('link', os.readlink(item))
        elif item.is_file():
            result[str(item.relative_to(path))] = (
                hashlib.sha256(item.read_bytes()).hexdigest(),
                bool(item.stat().st_mode & 0o111),
            )
    return result


def export_source(repo, commit, subtree, output):
    archive = output.parent / 'upstream.tar'
    with archive.open('wb') as stream:
        subprocess.run(['git', '-C', str(repo), 'archive', f'{commit}:{subtree}'],
                       stdout=stream, check=True)
    output.mkdir()
    with tarfile.open(archive) as bundle:
        for member in bundle.getmembers():
            target = (output / member.name).resolve()
            if not target.is_relative_to(output.resolve()) or not (member.isfile() or member.isdir()):
                raise ValueError(f'Unsupported upstream archive entry: {member.name}')
        bundle.extractall(output)


def render(source, target, root):
    shutil.copytree(source, target)
    required = ['skills/poteto-mode/SKILL.md', 'skills/interrogate/SKILL.md',
                'skills/setup-pstack/SKILL.md', 'docs/harness/claude-code.md',
                'agents/poteto-agent.md', 'LICENSE']
    for name in required:
        if not (target / name).is_file():
            raise ValueError(f'Upstream layout changed: missing {name}')
    entries = list((target / 'skills').glob('*/SKILL.md')) + list((target / 'agents').glob('*.md'))
    for entry in entries:
        original = entry.read_text()
        match = re.match(r'\A---\r?\n.*?\r?\n---\r?\n', original, re.S)
        if not match:
            raise ValueError(f'Missing frontmatter: {entry.relative_to(target)}')
        link = os.path.relpath(target / 'docs/harness/bob.md', entry.parent)
        pointer = f'\nBefore following these instructions, read [the pstack-bob adapter]({link}) once per session.\n'
        entry.write_text(original[:match.end()] + pointer + original[match.end():])
    for adapter in (root / 'adapters').glob('*.md'):
        destination = target / 'docs/harness' / adapter.name
        if destination.exists():
            raise ValueError(f'Local adapter would overwrite an upstream file: {adapter.name}')
        shutil.copy2(adapter, destination)
    if (target / 'config/models').exists():
        raise ValueError('Upstream now owns config/models; review the adapter layout')
    (target / 'config').mkdir(exist_ok=True)
    shutil.copy2(root / 'config/models', target / 'config/models')
    package = read_json(root / 'package.json')
    manifest = {
        'name': package['name'], 'version': package['version'],
        'description': package['description'], 'author': {'name': 'vladimir-fsh'},
        'repository': package['repository'], 'license': 'MIT',
    }
    write_json(target / '.claude-plugin/plugin.json', manifest)
    write_json(target / 'plugin.json', manifest)
    write_json(target / '.codex-plugin/plugin.json', {
        **manifest, 'skills': './skills/',
        'interface': {'displayName': 'pstack-bob', 'shortDescription': package['description'],
                      'developerName': 'vladimir-fsh', 'category': 'Productivity'},
    })


def sync(root, source=None, ref=None, check=False):
    lock = read_json(root / 'upstream.json')
    if check and ref:
        raise ValueError('--check verifies the lock; omit --ref')
    with tempfile.TemporaryDirectory(prefix='.pstack-sync-', dir=root) as temporary:
        temp = Path(temporary)
        if source:
            repo = Path(source).resolve()
        else:
            repo = temp / 'repository'
            repo.mkdir()
            git('init', '--quiet', cwd=repo)
            subprocess.run(['git', '-C', str(repo), 'fetch', '--quiet', '--depth=1',
                            lock['repository'], ref or lock['commit']], check=True)
        revision = (ref or lock['commit']) if source else 'FETCH_HEAD'
        commit = git('rev-parse', '--verify', '--end-of-options', revision + '^{commit}', cwd=repo)
        exported = temp / 'upstream'
        export_source(repo, commit, lock['path'], exported)
        version = read_json(exported / 'plugin.json')['version']
        rendered = temp / 'plugin'
        render(exported, rendered, root)
        current = root / 'plugin'
        before, after = snapshot(current), snapshot(rendered)
        changes = sorted(name for name in before.keys() | after.keys() if before.get(name) != after.get(name))
        if check:
            if changes or commit != lock['commit'] or version != lock['version']:
                raise ValueError('Generated plugin differs from pinned source/adapters: ' + ', '.join(changes[:12]))
            print(f'check: ok ({len(after)} files, upstream {version}, {commit[:12]})')
            return
        if changes and current.exists() and (root / '.git').exists():
            dirty = git('status', '--porcelain', '--untracked-files=all', '--ignored', '--', 'plugin', cwd=root)
            if dirty:
                raise ValueError('plugin/ has uncommitted changes. Preserve or commit them before regenerating.')
        if changes:
            backup = temp / 'previous-plugin'
            if current.exists():
                current.rename(backup)
            try:
                rendered.rename(current)
            except BaseException:
                if backup.exists():
                    backup.rename(current)
                raise
        write_json(root / 'upstream.json', {**lock, 'commit': commit, 'version': version})
        print(f'upstream {version} ({commit[:12]}): {len(changes)} generated files changed')
        print('Review git diff; bump package.json version and regenerate before publishing.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, help='Existing upstream checkout for offline regeneration')
    parser.add_argument('--ref', help='New upstream commit, tag, or branch; default is the lock')
    parser.add_argument('--check', action='store_true', help='Fail on generated drift without changing plugin files')
    args = parser.parse_args()
    try:
        sync(ROOT, args.source, args.ref, args.check)
    except (ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
