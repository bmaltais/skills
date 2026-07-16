import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "ado-create-work-item.sh"


class AdoCreateWorkItemTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.bin_dir = Path(self.tmpdir.name) / "bin"
        self.bin_dir.mkdir()
        self.desc_file = Path(self.tmpdir.name) / "desc.html"
        self.desc_file.write_text("<p>Finding: Fail</p>")

    def _stub_az(self, body):
        path = self.bin_dir / "az"
        path.write_text(body)
        path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    def _run(self, args):
        env = os.environ.copy()
        env["PATH"] = f"{self.bin_dir}:{env['PATH']}"
        return subprocess.run(
            ["bash", str(SCRIPT), *args], env=env, capture_output=True, text=True
        )

    def test_success_prints_id_and_url(self):
        self._stub_az(
            "#!/usr/bin/env bash\n"
            'if [[ "$1" == "extension" && "$2" == "list" ]]; then\n'
            '  echo "azure-devops"\n'
            "  exit 0\n"
            "fi\n"
            'if [[ "$1" == "boards" && "$2" == "work-item" && "$3" == "create" ]]; then\n'
            '  echo \'{"id": 555}\'\n'
            "  exit 0\n"
            "fi\n"
            "exit 1\n"
        )
        result = self._run(
            [
                "https://dev.azure.com/acme",
                "MyProject",
                "Issue",
                "[itsg-33:gap] AC-2 — Account Management",
                "itsg-33:gap; P1",
                str(self.desc_file),
            ]
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.strip(),
            "555 https://dev.azure.com/acme/MyProject/_workitems/edit/555",
        )

    def test_missing_description_file_fails(self):
        result = self._run(
            [
                "https://dev.azure.com/acme",
                "MyProject",
                "Issue",
                "title",
                "itsg-33:gap; P1",
                "/no/such/file.html",
            ]
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("description file not found", result.stderr)

    def test_az_failure_surfaces_reason(self):
        self._stub_az(
            "#!/usr/bin/env bash\n"
            'if [[ "$1" == "extension" && "$2" == "list" ]]; then\n'
            '  echo "azure-devops"\n'
            "  exit 0\n"
            "fi\n"
            'echo "VS402625: work item type does not exist" >&2\n'
            "exit 1\n"
        )
        result = self._run(
            [
                "https://dev.azure.com/acme",
                "MyProject",
                "Issue",
                "title",
                "itsg-33:gap; P1",
                str(self.desc_file),
            ]
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("az boards work-item create failed", result.stderr)


if __name__ == "__main__":
    unittest.main()
