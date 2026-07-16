import json
import os
import stat
import subprocess
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "gh-list-tagged-issues.sh"


class GhListTaggedIssuesTest(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.bin_dir = Path(self.tmpdir.name) / "bin"
        self.bin_dir.mkdir()

    def _stub_gh(self, body):
        path = self.bin_dir / "gh"
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

    def test_success_prints_gh_output(self):
        self._stub_gh(
            "#!/usr/bin/env bash\n"
            'if [[ "$1" == "issue" && "$2" == "list" && "$4" == "itsg-33:gap" ]]; then\n'
            "  echo '[{\"number\": 1, \"title\": \"[itsg-33:gap] AC-2 — Account Management\"}]'\n"
            "  exit 0\n"
            "fi\n"
            "exit 1\n"
        )
        result = self._run(["itsg-33:gap"])
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data[0]["number"], 1)

    def test_gh_failure_surfaces_reason(self):
        self._stub_gh(
            "#!/usr/bin/env bash\n"
            'echo "error: not authenticated" >&2\n'
            "exit 1\n"
        )
        result = self._run(["itsg-33:gap"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("gh issue list failed", result.stderr)
        self.assertIn("error: not authenticated", result.stderr)

    def test_missing_arg_fails_fast(self):
        result = self._run([])
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
