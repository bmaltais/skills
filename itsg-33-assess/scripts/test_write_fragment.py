import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "write-fragment.py"

VALID_CONTROL = {
    "finding": "Fail",
    "confidence": "High: no audit logging configuration found anywhere in the repo.",
    "risk_summary": "An attacker's actions leave no trail.",
    "implementation_approach": "No K8s audit policy, no cloud audit log resource.",
    "evidence_artefacts": ["k8s/deployment.yaml"],
    "client_responsibility": "Configure platform audit logging.",
    "files_read": {
        "k8s/deployment.yaml": "a" * 64,
    },
}


class WriteFragmentTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.input_path = Path(self.tmpdir.name) / "in.json"
        self.output_path = Path(self.tmpdir.name) / "out.json"

    def run_script(self, family, payload):
        self.input_path.write_text(json.dumps(payload))
        return subprocess.run(
            [sys.executable, str(SCRIPT), family, str(self.input_path), str(self.output_path)],
            capture_output=True,
            text=True,
        )

    def test_valid_fragment_writes_canonical_json(self):
        payload = {"family": "AU", "controls": {"AU-2": VALID_CONTROL}}
        result = self.run_script("AU", payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        written = json.loads(self.output_path.read_text())
        self.assertEqual(written, payload)

    def test_empty_files_read_is_valid(self):
        control = dict(VALID_CONTROL, files_read={}, finding="Not Assessable")
        payload = {"family": "CM", "controls": {"CM-10": control}}
        result = self.run_script("CM", payload)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_family_mismatch_fails(self):
        payload = {"family": "AU", "controls": {"AU-2": VALID_CONTROL}}
        result = self.run_script("SI", payload)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("family", result.stderr.lower())
        self.assertFalse(self.output_path.exists())

    def test_missing_required_field_fails(self):
        control = dict(VALID_CONTROL)
        del control["confidence"]
        payload = {"family": "AU", "controls": {"AU-2": control}}
        result = self.run_script("AU", payload)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("confidence", result.stderr.lower())

    def test_invalid_finding_value_fails(self):
        control = dict(VALID_CONTROL, finding="Maybe")
        payload = {"family": "AU", "controls": {"AU-2": control}}
        result = self.run_script("AU", payload)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("finding", result.stderr.lower())

    def test_invalid_files_read_hash_format_fails(self):
        control = dict(VALID_CONTROL, files_read={"k8s/deployment.yaml": "not-a-hash"})
        payload = {"family": "AU", "controls": {"AU-2": control}}
        result = self.run_script("AU", payload)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("files_read", result.stderr.lower())

    def test_malformed_json_input_fails(self):
        self.input_path.write_text("{not valid json")
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "AU", str(self.input_path), str(self.output_path)],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("json", result.stderr.lower())

    def test_cached_true_is_valid(self):
        control = dict(VALID_CONTROL, cached=True)
        payload = {"family": "AU", "controls": {"AU-2": control}}
        result = self.run_script("AU", payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        written = json.loads(self.output_path.read_text())
        self.assertTrue(written["controls"]["AU-2"]["cached"])

    def test_invalid_cached_type_fails(self):
        control = dict(VALID_CONTROL, cached="yes")
        payload = {"family": "AU", "controls": {"AU-2": control}}
        result = self.run_script("AU", payload)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cached", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
