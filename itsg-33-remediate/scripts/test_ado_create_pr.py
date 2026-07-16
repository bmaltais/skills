import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "ado-create-pr.sh"


class AdoCreatePrTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.bin_dir = Path(self.tmpdir.name) / "bin"
        self.bin_dir.mkdir()
        self.body_file = Path(self.tmpdir.name) / "body.md"
        self.body_file.write_text("## Control\nAC-2\n")

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

    def _common_args(self, target_branch=None):
        args = [
            "https://dev.azure.com/acme",
            "MyProject",
            "myrepo",
            "itsg33/fix/AC-2",
            "fix(AC-2): title",
            str(self.body_file),
            "555",
        ]
        if target_branch:
            args.append(target_branch)
        return args

    def test_auto_detects_default_branch_when_omitted(self):
        self._stub_az(
            "#!/usr/bin/env bash\n"
            'if [[ "$1" == "extension" && "$2" == "list" ]]; then\n'
            '  echo "azure-devops"\n'
            "  exit 0\n"
            "fi\n"
            'if [[ "$1" == "repos" && "$2" == "show" ]]; then\n'
            '  echo "refs/heads/main"\n'
            "  exit 0\n"
            "fi\n"
            'if [[ "$1" == "repos" && "$2" == "pr" && "$3" == "create" ]]; then\n'
            '  echo \'{"pullRequestId": 77}\'\n'
            "  exit 0\n"
            "fi\n"
            "exit 1\n"
        )
        result = self._run(self._common_args())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.strip(),
            "77 https://dev.azure.com/acme/MyProject/_git/myrepo/pullrequest/77",
        )

    def test_skips_default_branch_detection_when_given(self):
        self._stub_az(
            "#!/usr/bin/env bash\n"
            'if [[ "$1" == "extension" && "$2" == "list" ]]; then\n'
            '  echo "azure-devops"\n'
            "  exit 0\n"
            "fi\n"
            'if [[ "$1" == "repos" && "$2" == "show" ]]; then\n'
            '  echo "SHOULD NOT BE CALLED" >&2\n'
            "  exit 1\n"
            "fi\n"
            'if [[ "$1" == "repos" && "$2" == "pr" && "$3" == "create" ]]; then\n'
            '  echo \'{"pullRequestId": 77}\'\n'
            "  exit 0\n"
            "fi\n"
            "exit 1\n"
        )
        result = self._run(self._common_args(target_branch="develop"))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_body_file_fails(self):
        args = self._common_args()
        args[5] = "/no/such/file.md"
        result = self._run(args)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("body file not found", result.stderr)

    def test_empty_default_branch_fails(self):
        self._stub_az(
            "#!/usr/bin/env bash\n"
            'if [[ "$1" == "extension" && "$2" == "list" ]]; then\n'
            '  echo "azure-devops"\n'
            "  exit 0\n"
            "fi\n"
            'if [[ "$1" == "repos" && "$2" == "show" ]]; then\n'
            '  echo ""\n'
            "  exit 0\n"
            "fi\n"
            "exit 1\n"
        )
        result = self._run(self._common_args())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("could not determine default branch", result.stderr)

    def test_az_pr_create_failure_surfaces_reason(self):
        self._stub_az(
            "#!/usr/bin/env bash\n"
            'if [[ "$1" == "extension" && "$2" == "list" ]]; then\n'
            '  echo "azure-devops"\n'
            "  exit 0\n"
            "fi\n"
            'if [[ "$1" == "repos" && "$2" == "show" ]]; then\n'
            '  echo "refs/heads/main"\n'
            "  exit 0\n"
            "fi\n"
            'echo "TF401398: policy required" >&2\n'
            "exit 1\n"
        )
        result = self._run(self._common_args())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("az repos pr create failed", result.stderr)


if __name__ == "__main__":
    unittest.main()
