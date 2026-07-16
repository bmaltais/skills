import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "gh-create-issue.sh"


class GhCreateIssueTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.bin_dir = Path(self.tmpdir.name) / "bin"
        self.bin_dir.mkdir()
        self.body_file = Path(self.tmpdir.name) / "body.md"
        self.body_file.write_text("Control ID: AC-2\nFinding: Fail\n")

    def _stub_gh(self, body):
        path = self.bin_dir / "gh"
        path.write_text(body)
        path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    def _run(self, args):
        env = os.environ.copy()
        env["PATH"] = f"{self.bin_dir}:{env['PATH']}"
        return subprocess.run(
            ["bash", str(SCRIPT), *args], env=env, capture_output=True, text=True
        )

    def test_success_prints_number_and_url(self):
        self._stub_gh(
            "#!/usr/bin/env bash\n"
            'if [[ "$1" == "issue" && "$2" == "create" ]]; then\n'
            '  echo "https://github.com/acme/repo/issues/42"\n'
            "  exit 0\n"
            "fi\n"
            "exit 1\n"
        )
        result = self._run(
            ["[itsg-33:gap] AC-2 — Account Management", "itsg-33:gap,P1", str(self.body_file)]
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "42 https://github.com/acme/repo/issues/42")

    def test_passes_each_label_separately(self):
        capture_file = Path(self.tmpdir.name) / "captured_args"
        self._stub_gh(
            "#!/usr/bin/env bash\n"
            f'echo "$@" > {capture_file}\n'
            'echo "https://github.com/acme/repo/issues/1"\n'
            "exit 0\n"
        )
        self._run(["title", "itsg-33:gap,P1", str(self.body_file)])
        captured = capture_file.read_text()
        self.assertIn("--label itsg-33:gap", captured)
        self.assertIn("--label P1", captured)

    def test_missing_body_file_fails(self):
        result = self._run(["title", "itsg-33:gap,P1", "/no/such/file.md"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("body file not found", result.stderr)

    def test_gh_failure_surfaces_reason(self):
        self._stub_gh('#!/usr/bin/env bash\necho "rate limited" >&2\nexit 1\n')
        result = self._run(["title", "itsg-33:gap,P1", str(self.body_file)])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("gh issue create failed", result.stderr)


if __name__ == "__main__":
    unittest.main()
