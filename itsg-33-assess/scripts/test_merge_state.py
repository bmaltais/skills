import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "merge-state.py"


class MergeStateTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.fragments_dir = Path(self.tmpdir.name) / "fragments"
        self.fragments_dir.mkdir()
        self.old_state_path = Path(self.tmpdir.name) / "old-state.yaml"
        self.new_state_path = Path(self.tmpdir.name) / "new-state.yaml"

    def write_fragment(self, family, controls):
        (self.fragments_dir / f"{family}.json").write_text(
            json.dumps({"family": family, "controls": controls})
        )

    def run_merge(self, profile="PBMM"):
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(self.fragments_dir),
             str(self.old_state_path), str(self.new_state_path), profile],
            capture_output=True,
            text=True,
        )

    def read_new_state(self):
        return json.loads(self.new_state_path.read_text())

    def test_fresh_merge_no_old_state(self):
        self.write_fragment("AU", {
            "AU-2": {"finding": "Fail", "confidence": "no audit logging found",
                      "files_read": {"k8s/deployment.yaml": "a" * 64}},
        })
        self.write_fragment("RA", {
            "RA-5": {"finding": "Pass", "confidence": "scanner runs on every PR",
                      "files_read": {}},
        })
        result = self.run_merge()
        self.assertEqual(result.returncode, 0, result.stderr)
        state = self.read_new_state()
        self.assertIn("last_run", state)
        self.assertEqual(state["controls"]["AU-2"]["finding"], "Fail")
        self.assertEqual(state["controls"]["RA-5"]["finding"], "Pass")

    def test_cached_control_uses_old_state_value_not_fragment(self):
        self.old_state_path.write_text(json.dumps({
            "last_run": "2026-01-01T00:00:00+00:00",
            "controls": {
                "SC-2": {"finding": "Pass", "confidence": "TRUE ORIGINAL TEXT",
                          "files_read": {"k8s/deployment.yaml": "b" * 64}},
            },
        }))
        self.write_fragment("SC", {
            "SC-2": {"finding": "Pass", "confidence": "a paraphrased rewording",
                      "files_read": {"k8s/deployment.yaml": "b" * 64}, "cached": True},
        })
        result = self.run_merge()
        self.assertEqual(result.returncode, 0, result.stderr)
        state = self.read_new_state()
        self.assertEqual(state["controls"]["SC-2"]["confidence"], "TRUE ORIGINAL TEXT")

    def test_cached_control_missing_old_entry_fails(self):
        self.write_fragment("SC", {
            "SC-2": {"finding": "Pass", "confidence": "whatever",
                      "files_read": {}, "cached": True},
        })
        result = self.run_merge()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sc-2", result.stderr.lower())
        self.assertIn("cached", result.stderr.lower())

    def test_cached_control_with_incomplete_old_entry_fails_cleanly(self):
        self.old_state_path.write_text(json.dumps({
            "last_run": "2026-01-01T00:00:00+00:00",
            "controls": {
                "SC-2": {"finding": "Pass", "files_read": {}},
            },
        }))
        self.write_fragment("SC", {
            "SC-2": {"finding": "Pass", "confidence": "whatever",
                      "files_read": {}, "cached": True},
        })
        result = self.run_merge()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sc-2", result.stderr.lower())
        self.assertIn("missing", result.stderr.lower())

    def test_fresh_control_with_missing_field_fails_cleanly(self):
        self.write_fragment("AU", {
            "AU-2": {"finding": "Fail", "files_read": {}},
        })
        result = self.run_merge()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("au-2", result.stderr.lower())
        self.assertIn("missing", result.stderr.lower())

    def test_duplicate_control_across_fragments_fails(self):
        self.write_fragment("AU", {
            "AU-2": {"finding": "Fail", "confidence": "x", "files_read": {}},
        })
        self.write_fragment("SI", {
            "AU-2": {"finding": "Pass", "confidence": "y", "files_read": {}},
        })
        result = self.run_merge()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("au-2", result.stderr.lower())

    def test_malformed_fragment_json_fails(self):
        (self.fragments_dir / "AU.json").write_text("{not valid")
        result = self.run_merge()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("json", result.stderr.lower())

    def test_malformed_old_state_fails(self):
        self.old_state_path.write_text("{not valid")
        self.write_fragment("AU", {
            "AU-2": {"finding": "Fail", "confidence": "x", "files_read": {}},
        })
        result = self.run_merge()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("json", result.stderr.lower())

    def test_no_fragments_found_fails(self):
        result = self.run_merge()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no fragment", result.stderr.lower())

    def test_plausibility_check_triggers_for_all_na_sc_and_ia(self):
        self.write_fragment("SC", {
            "SC-2": {"finding": "Not Assessable", "confidence": "x", "files_read": {}},
        })
        self.write_fragment("IA", {
            "IA-2": {"finding": "Not Assessable", "confidence": "y", "files_read": {}},
        })
        result = self.run_merge(profile="PBMM")
        self.assertEqual(result.returncode, 0, result.stderr)
        state = self.read_new_state()
        self.assertIn("PLAUSIBILITY-WARNING", state["controls"])
        self.assertEqual(state["controls"]["PLAUSIBILITY-WARNING"]["finding"], "Not Assessable")

    def test_plausibility_check_not_triggered_for_non_pbmm_profile(self):
        self.write_fragment("SC", {
            "SC-2": {"finding": "Not Assessable", "confidence": "x", "files_read": {}},
        })
        self.write_fragment("IA", {
            "IA-2": {"finding": "Not Assessable", "confidence": "y", "files_read": {}},
        })
        result = self.run_merge(profile="unclassified")
        self.assertEqual(result.returncode, 0, result.stderr)
        state = self.read_new_state()
        self.assertNotIn("PLAUSIBILITY-WARNING", state["controls"])

    def test_plausibility_check_not_triggered_when_some_pass(self):
        self.write_fragment("SC", {
            "SC-2": {"finding": "Pass", "confidence": "x", "files_read": {}},
        })
        self.write_fragment("IA", {
            "IA-2": {"finding": "Not Assessable", "confidence": "y", "files_read": {}},
        })
        result = self.run_merge(profile="PBMM")
        self.assertEqual(result.returncode, 0, result.stderr)
        state = self.read_new_state()
        self.assertNotIn("PLAUSIBILITY-WARNING", state["controls"])


if __name__ == "__main__":
    unittest.main()
