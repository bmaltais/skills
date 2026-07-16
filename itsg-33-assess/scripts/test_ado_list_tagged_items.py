import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "ado-list-tagged-items.sh"


class AdoListTaggedItemsTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.bin_dir = Path(self.tmpdir.name) / "bin"
        self.bin_dir.mkdir()

    def _stub_az(self, body):
        path = self.bin_dir / "az"
        path.write_text(body)
        path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    def _run(self, args, env_extra=None):
        env = os.environ.copy()
        env["PATH"] = f"{self.bin_dir}:{env['PATH']}"
        if env_extra:
            env.update(env_extra)
        return subprocess.run(
            ["bash", str(SCRIPT), *args], env=env, capture_output=True, text=True
        )

    def test_success_when_extension_already_installed(self):
        self._stub_az(
            "#!/usr/bin/env bash\n"
            'if [[ "$1" == "extension" && "$2" == "list" ]]; then\n'
            '  echo "azure-devops"\n'
            "  exit 0\n"
            "fi\n"
            'if [[ "$1" == "boards" && "$2" == "query" ]]; then\n'
            '  echo \'[{"id": 101, "fields": {"System.Title": "[itsg-33:gap] AC-2 — Account Management"}}]\'\n'
            "  exit 0\n"
            "fi\n"
            "exit 1\n"
        )
        result = self._run(["https://dev.azure.com/acme", "MyProject", "itsg-33:gap"])
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data, [{"id": 101, "title": "[itsg-33:gap] AC-2 — Account Management"}])

    def test_installs_extension_when_missing(self):
        marker = Path(self.tmpdir.name) / "installed"
        self._stub_az(
            "#!/usr/bin/env bash\n"
            'if [[ "$1" == "extension" && "$2" == "list" ]]; then\n'
            "  exit 0\n"
            "fi\n"
            'if [[ "$1" == "extension" && "$2" == "add" ]]; then\n'
            f'  touch "{marker}"\n'
            "  exit 0\n"
            "fi\n"
            'if [[ "$1" == "boards" && "$2" == "query" ]]; then\n'
            "  echo '[]'\n"
            "  exit 0\n"
            "fi\n"
            "exit 1\n"
        )
        result = self._run(["https://dev.azure.com/acme", "MyProject", "itsg-33:gap"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(marker.exists())

    def test_empty_stdout_treated_as_no_results(self):
        # Real `az boards query -o json` prints nothing at all (not "[]") when
        # zero work items match — the script must not crash on this.
        self._stub_az(
            "#!/usr/bin/env bash\n"
            'if [[ "$1" == "extension" && "$2" == "list" ]]; then\n'
            '  echo "azure-devops"\n'
            "  exit 0\n"
            "fi\n"
            'if [[ "$1" == "boards" && "$2" == "query" ]]; then\n'
            "  exit 0\n"
            "fi\n"
            "exit 1\n"
        )
        result = self._run(["https://dev.azure.com/acme", "MyProject", "itsg-33:gap"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), [])

    def test_az_query_failure_surfaces_reason(self):
        self._stub_az(
            "#!/usr/bin/env bash\n"
            'if [[ "$1" == "extension" && "$2" == "list" ]]; then\n'
            '  echo "azure-devops"\n'
            "  exit 0\n"
            "fi\n"
            'echo "TF400898: unauthorized" >&2\n'
            "exit 1\n"
        )
        result = self._run(["https://dev.azure.com/acme", "MyProject", "itsg-33:gap"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("az boards query failed", result.stderr)

    def test_missing_arg_fails_fast(self):
        result = self._run(["https://dev.azure.com/acme"])
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
