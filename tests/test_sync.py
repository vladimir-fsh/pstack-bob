import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("sync", ROOT / "scripts/sync.py")
sync = importlib.util.module_from_spec(spec)
sys.modules["sync"] = sync
spec.loader.exec_module(sync)

RULES, _ = sync.load_rules({"substitutions": [{"pattern": "Task", "replacement": "Agent", "rationale": "tool name"}]})


def write_tree(root, files):
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


class SyncTree(unittest.TestCase):
    def run_sync(self, old, new, local):
        scratch = Path(self.enterContext(tempfile.TemporaryDirectory()))
        for name, files in (("old", old), ("new", new), ("local", local)):
            (scratch / name).mkdir()
            write_tree(scratch / name, files)
        report = sync.Report()
        sync.sync_tree(scratch / "old", scratch / "new", scratch / "local", RULES, ["docs/"], "pstack", report)
        return report, scratch / "local"

    def test_an_untouched_file_takes_upstream_in_translation(self):
        report, local = self.run_sync({"a.md": "Use Task.\n"}, {"a.md": "Use Task now.\n"}, {"a.md": "Use Agent.\n"})
        self.assertEqual((local / "a.md").read_text(), "Use Agent now.\n")
        self.assertEqual(report.updated, ["pstack/a.md"])

    def test_a_local_edit_survives_an_upstream_change_elsewhere(self):
        old = {"a.md": "one\n\ntwo\n\nthree\n"}
        new = {"a.md": "one\n\ntwo\n\nthree, changed\n"}
        report, local = self.run_sync(old, new, {"a.md": "one, ours\n\ntwo\n\nthree\n"})
        self.assertEqual((local / "a.md").read_text(), "one, ours\n\ntwo\n\nthree, changed\n")
        self.assertEqual(report.merged, ["pstack/a.md"])

    def test_both_sides_changing_one_line_is_a_conflict(self):
        report, local = self.run_sync({"a.md": "one\n"}, {"a.md": "one, theirs\n"}, {"a.md": "one, ours\n"})
        self.assertEqual(report.conflicts, ["pstack/a.md"])
        self.assertIn("<<<<<<< ours", (local / "a.md").read_text())

    def test_upstream_adds_and_removes_files(self):
        report, local = self.run_sync({"gone.md": "x\n"}, {"new.md": "Task\n"}, {"gone.md": "x\n"})
        self.assertFalse((local / "gone.md").exists())
        self.assertEqual((local / "new.md").read_text(), "Agent\n")
        self.assertEqual((report.added, report.removed), (["pstack/new.md"], ["pstack/gone.md"]))

    def test_a_locally_edited_file_outlives_its_upstream_deletion(self):
        report, local = self.run_sync({"a.md": "x\n"}, {}, {"a.md": "x, ours\n"})
        self.assertTrue((local / "a.md").exists())
        self.assertEqual(len(report.kept), 1)

    def test_excluded_paths_and_port_only_files_are_left_alone(self):
        report, local = self.run_sync({"docs/a.md": "x\n"}, {"docs/a.md": "y\n"}, {"ours.md": "z\n"})
        self.assertEqual(report.changed(), [])
        self.assertEqual((local / "ours.md").read_text(), "z\n")


if __name__ == "__main__":
    unittest.main()
