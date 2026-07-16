import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "gh-create-pr.sh"


class GhCreatePrTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.bin_dir = Path(self.tmpdir.name) / "bin"
        self.bin_dir.mkdir()
        self.body_file = Path(self.tmpdir.name) / "body.md"
        self.body_file.write_text("## Control\nAC-2\n")
        self.captured_body = Path(self.tmpdir.name) / "captured_body.md"

    def _stub_gh(self, body):
        path = self.bin_dir / "gh"
        path.write_text(body)
        path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    def _run(self, args):
        env = os.environ.copy()
        env["PATH"] = f"{self.bin_dir}:{env['PATH']}"
        env["STUB_CAPTURED_BODY"] = str(self.captured_body)
        return subprocess.run(
            ["bash", str(SCRIPT), *args], env=env, capture_output=True, text=True
        )

    def test_success_without_closes_number(self):
        self._stub_gh(
            "#!/usr/bin/env bash\n"
            'if [[ "$1" == "pr" && "$2" == "create" ]]; then\n'
            '  echo "https://github.com/acme/repo/pull/9"\n'
            "  exit 0\n"
            "fi\n"
            "exit 1\n"
        )
        result = self._run(["fix(AC-2): title", str(self.body_file)])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "https://github.com/acme/repo/pull/9")

    def test_appends_closes_line_when_given(self):
        self._stub_gh(
            "#!/usr/bin/env bash\n"
            'if [[ "$1" == "pr" && "$2" == "create" ]]; then\n'
            '  prev=""\n'
            '  for arg in "$@"; do\n'
            '    if [[ "$prev" == "--body-file" ]]; then\n'
            '      cp "$arg" "$STUB_CAPTURED_BODY"\n'
            "    fi\n"
            '    prev="$arg"\n'
            "  done\n"
            '  echo "https://github.com/acme/repo/pull/9"\n'
            "  exit 0\n"
            "fi\n"
            "exit 1\n"
        )
        result = self._run(["fix(AC-2): title", str(self.body_file), "7"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Closes #7", self.captured_body.read_text())

    def test_missing_body_file_fails(self):
        result = self._run(["title", "/no/such/file.md"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("body file not found", result.stderr)

    def test_gh_failure_surfaces_reason(self):
        self._stub_gh('#!/usr/bin/env bash\necho "no such branch" >&2\nexit 1\n')
        result = self._run(["title", str(self.body_file)])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("gh pr create failed", result.stderr)


if __name__ == "__main__":
    unittest.main()
