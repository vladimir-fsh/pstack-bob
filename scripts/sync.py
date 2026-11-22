#!/usr/bin/env python3
"""Merge a newer cursor/plugins commit into plugin/.

plugin/ is this repository's source. Each upstream file is translated with
substitutions.json at the old pin and at the new commit, and the difference
between the two is merged into the local file, so local edits survive.
"""

import argparse
from dataclasses import dataclass, field
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PIN = ROOT / "upstream.json"
RULES = ROOT / "substitutions.json"
PLUGIN = ROOT / "plugin"
MANIFESTS = (PLUGIN / ".claude-plugin/plugin.json", PLUGIN / ".codex-plugin/plugin.json")
CONFLICT_MARKER = re.compile(r"^(<{7} ours|>{7} upstream)$", re.MULTILINE)


class SyncError(Exception):
    pass


@dataclass
class Rule:
    match: re.Pattern
    files: re.Pattern | None
    replacement: str
    label: str


@dataclass
class Report:
    added: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    merged: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    kept: list[str] = field(default_factory=list)
    cursorisms: list[str] = field(default_factory=list)
    stale_rules: list[str] = field(default_factory=list)

    def changed(self):
        return self.added + self.updated + self.merged + self.removed + self.conflicts

    def needs_a_person(self):
        return self.conflicts + self.kept + self.cursorisms + self.stale_rules


def git(*args, cwd=None, binary=False):
    output = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True).stdout
    return output if binary else output.decode().strip()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_rules(document):
    rules = []
    for rule in document["substitutions"]:
        source = rule.get("pattern")
        match = re.compile(re.escape(source) if source is not None else rule["regex"])
        files = re.compile(rule["files"]) if rule.get("files") else None
        rules.append(Rule(match, files, rule["replacement"], source or rule["regex"]))
    denylist = [
        (re.compile(re.escape(entry["token"]) if "token" in entry else entry["regex"]), entry["hint"])
        for entry in document.get("denylist", [])
    ]
    return rules, denylist


def translate(text, rules, relative_path, used=None):
    for rule in rules:
        if rule.files is None or rule.files.search(relative_path):
            text, count = rule.match.subn(lambda _: rule.replacement, text)
            if count and used is not None:
                used.add(rule.label)
    return text


def fetch(repository, ref, cache):
    if not (cache / ".git").exists():
        git("init", "--quiet", str(cache))
    git("fetch", "--quiet", "--depth=1", repository, ref, cwd=cache)
    return git("rev-parse", "FETCH_HEAD", cwd=cache)


def export(cache, commit, subtree, target):
    target.mkdir(parents=True)
    archive = git("archive", f"{commit}:{subtree}", cwd=cache, binary=True)
    with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
        bundle.extractall(target, filter="data")


def is_excluded(relative_path, excluded):
    return any(
        relative_path.startswith(entry) if entry.endswith("/") else relative_path == entry
        for entry in excluded
    )


def upstream_files(directory, excluded):
    return {
        path.relative_to(directory).as_posix()
        for path in directory.rglob("*")
        if path.is_file() and not path.is_symlink()
        and not is_excluded(path.relative_to(directory).as_posix(), excluded)
    }


def translated(directory, relative_path, rules, used=None):
    """An upstream file in this plugin's wording, or its raw bytes when it is not text."""
    data = (directory / relative_path).read_bytes()
    if b"\0" in data:
        return data
    try:
        return translate(data.decode("utf-8"), rules, relative_path, used).encode("utf-8")
    except UnicodeDecodeError:
        return data


def merge_three_way(local, base, theirs):
    """Return the merged bytes and whether Git left conflict markers in them."""
    with tempfile.TemporaryDirectory() as scratch:
        paths = [Path(scratch) / name for name in ("ours", "base", "upstream")]
        for path, data in zip(paths, (local, base, theirs)):
            path.write_bytes(data)
        result = subprocess.run(
            ["git", "merge-file", "-p", "-L", "ours", "-L", "base", "-L", "upstream", *map(str, paths)],
            capture_output=True,
        )
    if result.returncode < 0 or result.returncode > 127:
        raise SyncError(f"git merge-file failed: {result.stderr.decode()}")
    return result.stdout, result.returncode > 0


def add_file(source, destination, data):
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    shutil.copymode(source, destination)


def sync_tree(old_dir, new_dir, local_dir, rules, excluded, label, report, used=None):
    """Carry the upstream change from old_dir to new_dir into local_dir; return the paths written."""
    written = []
    old_files = upstream_files(old_dir, excluded)
    new_files = upstream_files(new_dir, excluded)
    for relative_path in sorted(old_files | new_files):
        name = f"{label}/{relative_path}"
        local_path = local_dir / relative_path
        local = local_path.read_bytes() if local_path.is_file() else None
        base = translated(old_dir, relative_path, rules) if relative_path in old_files else None
        theirs = translated(new_dir, relative_path, rules, used) if relative_path in new_files else None

        if base == theirs or local == theirs:
            continue
        if theirs is None:
            if local is None:
                continue
            if local == base:
                local_path.unlink()
                report.removed.append(name)
            else:
                report.kept.append(f"{name}: upstream deleted it, this plugin had edited it")
            continue
        if base is None:
            if local is None:
                add_file(new_dir / relative_path, local_path, theirs)
                report.added.append(name)
                written.append(relative_path)
            else:
                report.kept.append(f"{name}: upstream added it, this plugin already has its own")
            continue
        if local is None:
            report.kept.append(f"{name}: upstream changed it, this plugin had deleted it")
            continue
        if local == base:
            local_path.write_bytes(theirs)
            report.updated.append(name)
            written.append(relative_path)
            continue
        if b"\0" in local or b"\0" in theirs:
            report.kept.append(f"{name}: binary file changed on both sides")
            continue
        merged, conflicted = merge_three_way(local, base, theirs)
        local_path.write_bytes(merged)
        (report.conflicts if conflicted else report.merged).append(name)
        written.append(relative_path)
    return written


def find_cursorisms(local_dir, label, relative_paths, denylist):
    hits = []
    for relative_path in relative_paths:
        path = local_dir / relative_path
        if not path.is_file() or b"\0" in path.read_bytes():
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
            for pattern, hint in denylist:
                if pattern.search(line):
                    hits.append(f"{label}/{relative_path}:{number}: {hint}")
    return hits


def bump_version():
    manifests = {path: read_json(path) for path in MANIFESTS}
    versions = {manifest["version"] for manifest in manifests.values()}
    if len(versions) != 1:
        raise SyncError(f"manifest versions differ: {sorted(versions)}")
    major, minor, patch = map(int, versions.pop().split("."))
    version = f"{major}.{minor}.{patch + 1}"
    for path, manifest in manifests.items():
        manifest["version"] = version
        write_json(path, manifest)
    return version


def render(report, old, new, version):
    sections = [
        ("Conflicts to resolve by hand", report.conflicts),
        ("Left as they were", report.kept),
        ("Cursor wording that needs a rule or a rewrite", report.cursorisms),
        ("Rules in substitutions.json that match nothing upstream now", report.stale_rules),
        ("Merged with local edits", report.merged),
        ("Updated", report.updated),
        ("Added", report.added),
        ("Removed", report.removed),
    ]
    lines = [f"cursor/plugins {old[:7]} -> {new[:7]}, plugin version {version}", ""]
    for title, items in sections:
        if items:
            lines += [f"{title} ({len(items)}):", *(f"- {item}" for item in items), ""]
    return "\n".join(lines)


def check():
    problems = []
    for path in sorted(PLUGIN.rglob("*")):
        if path.is_file() and b"\0" not in (data := path.read_bytes()):
            if CONFLICT_MARKER.search(data.decode("utf-8", errors="replace")):
                problems.append(f"{path.relative_to(ROOT)}: unresolved merge conflict")
    versions = {read_json(path)["version"] for path in MANIFESTS}
    if len(versions) != 1:
        problems.append(f"manifest versions differ: {sorted(versions)}")
    load_rules(read_json(RULES))
    read_json(PIN)
    if problems:
        raise SyncError("\n".join(problems))
    print("plugin/ has no unresolved conflicts, and the manifests agree.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default="main", help="upstream ref to merge (default: main)")
    parser.add_argument("--repo", help="fetch from this repository instead of upstream.json's")
    parser.add_argument("--report", type=Path, help="also write the report to this file")
    parser.add_argument("--check", action="store_true", help="verify plugin/ without fetching anything")
    args = parser.parse_args()
    if args.check:
        return check()

    pin = read_json(PIN)
    rules, denylist = load_rules(read_json(RULES))
    repository = args.repo or pin["repository"]
    with tempfile.TemporaryDirectory() as scratch:
        cache = Path(scratch) / "upstream"
        cache.mkdir()
        old = fetch(repository, pin["commit"], cache)
        new = fetch(repository, args.ref, cache)
        if new == old:
            print(f"Pin already at {old[:7]}; nothing to merge.")
            return

        report = Report()
        used = set()
        for label, component in pin["components"].items():
            old_dir = Path(scratch) / "old" / label
            new_dir = Path(scratch) / "new" / label
            export(cache, old, component["upstreamPath"], old_dir)
            export(cache, new, component["upstreamPath"], new_dir)
            local_dir = ROOT / component["localPath"]
            written = sync_tree(old_dir, new_dir, local_dir, rules, component["exclude"], label, report, used)
            report.cursorisms += find_cursorisms(local_dir, label, written, denylist)
        report.stale_rules = [rule.label for rule in rules if rule.label not in used]

    if not report.changed() and not report.kept:
        print(f"Nothing this plugin carries changed between {old[:7]} and {new[:7]}; pin left alone.")
        return
    pin["commit"] = new
    write_json(PIN, pin)
    text = render(report, old, new, bump_version())
    print(text)
    if args.report:
        args.report.write_text(text + "\n", encoding="utf-8")
    if report.needs_a_person():
        sys.exit(2)


if __name__ == "__main__":
    try:
        main()
    except (SyncError, subprocess.CalledProcessError) as error:
        detail = getattr(error, "stderr", b"")
        sys.exit(f"sync failed: {error}" + (f"\n{detail.decode()}" if detail else ""))
