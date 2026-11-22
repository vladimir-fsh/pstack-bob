#!/usr/bin/env python3
"""Render plugin/ from the pinned upstream commit, patches.json, and overlay/."""

import argparse
import filecmp
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PIN = ROOT / "upstream.json"
PATCHES = ROOT / "patches.json"
OVERLAY = ROOT / "overlay"
VERSION = ROOT / "VERSION"
PLUGIN = ROOT / "plugin"
MANIFESTS = (".claude-plugin/plugin.json", ".codex-plugin/plugin.json")
HOMEPAGE = "https://github.com/vladimir-fsh/pstack-bob"
CREDIT = (
    " Built from michael-denyer/pstack-claude with external seats:"
    " panels can run the other vendor's model through Codex CLI or Claude Code CLI."
)


class BuildError(Exception):
    pass


def git(*args, cwd=None, binary=False):
    output = subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True
    ).stdout
    return output if binary else output.decode().strip()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def fetch(repository, ref, cache):
    """Fetch one ref into a scratch repository and return its commit."""
    if not (cache / ".git").exists():
        git("init", "--quiet", str(cache))
    git("fetch", "--quiet", "--depth=1", repository, ref, cwd=cache)
    return git("rev-parse", "FETCH_HEAD", cwd=cache)


def export(cache, commit, subtree, target):
    archive = git("archive", f"{commit}:{subtree}", cwd=cache, binary=True)
    with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
        bundle.extractall(target, filter="data")


def drop_excluded(target, excluded):
    for entry in excluded:
        path = target / entry
        if not path.exists():
            raise BuildError(f"upstream.json excludes {entry}, which upstream no longer has")
        shutil.rmtree(path) if path.is_dir() else path.unlink()


def apply_patches(target, patches):
    failures = []
    for number, patch in enumerate(patches, start=1):
        path = target / patch["file"]
        anchor = patch.get("after") or patch["replace"]
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        found = text.count(anchor)
        if found != 1:
            failures.append(f"  rule {number} ({patch['file']}): anchor found {found} times: {anchor[:70]!r}")
            continue
        replacement = anchor + patch["insert"] if "after" in patch else patch["with"]
        path.write_text(text.replace(anchor, replacement), encoding="utf-8")
    if failures:
        raise BuildError("patches.json no longer matches upstream:\n" + "\n".join(failures))


def copy_overlay(target):
    for source in sorted(OVERLAY.rglob("*")):
        if source.is_dir():
            continue
        destination = target / source.relative_to(OVERLAY)
        if destination.exists():
            raise BuildError(f"overlay/{source.relative_to(OVERLAY)} would overwrite an upstream file")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def stamp_manifests(target, version, upstream_version):
    for name in MANIFESTS:
        path = target / name
        manifest = read_json(path)
        manifest["version"] = version
        manifest["description"] = manifest["description"] + CREDIT + f" Upstream {upstream_version}."
        manifest["homepage"] = HOMEPAGE
        manifest["repository"] = HOMEPAGE
        write_json(path, manifest)


def render(pin, version, cache, target):
    export(cache, pin["commit"], pin["path"], target)
    drop_excluded(target, pin["exclude"])
    apply_patches(target, read_json(PATCHES))
    copy_overlay(target)
    stamp_manifests(target, version, pin["version"])


def differing_paths(left, right):
    comparison = filecmp.dircmp(left, right)
    paths = [*comparison.left_only, *comparison.right_only, *comparison.funny_files]
    _, mismatch, errors = filecmp.cmpfiles(left, right, comparison.common_files, shallow=False)
    paths += mismatch + errors
    for name in comparison.common_dirs:
        paths += [f"{name}/{path}" for path in differing_paths(left / name, right / name)]
    return sorted(paths)


def next_patch(version):
    major, minor, patch = map(int, version.split("."))
    return f"{major}.{minor}.{patch + 1}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail when plugin/ differs from a fresh render")
    parser.add_argument("--ref", help="move the pin to this upstream ref, bump VERSION, and render")
    parser.add_argument("--repo", help="fetch from this repository instead of upstream.json's")
    args = parser.parse_args()

    pin = read_json(PIN)
    version = VERSION.read_text().strip()
    repository = args.repo or pin["repository"]
    with tempfile.TemporaryDirectory() as scratch:
        cache = Path(scratch) / "upstream"
        cache.mkdir()
        if args.ref:
            commit = fetch(repository, args.ref, cache)
            if commit == pin["commit"]:
                print(f"Pin already at {commit[:7]}; nothing to do.")
                return
            pin["commit"] = commit
            pin["version"] = git("show", f"{commit}:VERSION", cwd=cache)
            version = next_patch(version)
        else:
            fetch(repository, pin["commit"], cache)

        target = Path(scratch) / "plugin"
        target.mkdir()
        render(pin, version, cache, target)

        if args.check:
            changed = differing_paths(target, PLUGIN) if PLUGIN.exists() else ["plugin/ is missing"]
            if changed:
                raise BuildError("plugin/ is stale; run scripts/build.py:\n  " + "\n  ".join(changed[:20]))
            print("plugin/ matches the pin, patches, and overlay.")
            return

        if args.ref:
            write_json(PIN, pin)
            VERSION.write_text(version + "\n")
        if PLUGIN.exists():
            shutil.rmtree(PLUGIN)
        shutil.copytree(target, PLUGIN, symlinks=True)
        print(f"Rendered plugin/ {version} from upstream {pin['version']} @ {pin['commit'][:7]}.")


if __name__ == "__main__":
    try:
        main()
    except (BuildError, subprocess.CalledProcessError) as error:
        detail = getattr(error, "stderr", b"")
        sys.exit(f"build failed: {error}" + (f"\n{detail.decode()}" if detail else ""))
