#!/usr/bin/env python3
"""Detect a repo's three check commands: typecheck, single-file test, full suite.

Usage: detect_checks.py [REPO_DIR]
Prints one `name: command` line each; MISSING where nothing was found.
Exit 1 if the directory has no recognisable project manifest.
"""

import json
import re
import sys
from pathlib import Path

TYPECHECK_KEYS = ("typecheck", "type-check", "types", "tsc", "check-types")
SUITE_KEYS = ("test", "tests", "test:unit", "test:all")


def read(path):
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def make_targets(root):
    """Target names defined in a Makefile at root."""
    text = read(root / "Makefile") or read(root / "makefile")
    return set(re.findall(r"^([A-Za-z0-9_.-]+):(?!=)", text, re.M))


def node(root, found):
    manifest = root / "package.json"
    if not manifest.exists():
        return False
    try:
        pkg = json.loads(read(manifest) or "{}")
    except json.JSONDecodeError:
        return True
    scripts = pkg.get("scripts", {})
    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    runner = "npm run"

    for key in TYPECHECK_KEYS:
        if key in scripts:
            found["typecheck"] = f"{runner} {key}"
            break
    else:
        if "typescript" in deps:
            found["typecheck"] = "npx tsc --noEmit"

    for key in SUITE_KEYS:
        if key in scripts:
            found["full suite"] = f"{runner} {key}"
            break

    blob = " ".join(scripts.values())
    if "vitest" in blob or "vitest" in deps:
        found["single-file test"] = "npx vitest run <file>"
    elif "jest" in blob or "jest" in deps:
        found["single-file test"] = "npx jest <file>"
    elif "playwright" in blob or "playwright" in deps:
        found["single-file test"] = "npx playwright test <file>"
    elif "node --test" in blob:
        found["single-file test"] = "node --test <file>"
    return True


def python(root, found):
    markers = ("pyproject.toml", "setup.py", "tox.ini", "requirements.txt")
    if not any((root / n).exists() for n in markers):
        return False
    conf = read(root / "pyproject.toml")
    if "mypy" in conf:
        found["typecheck"] = "mypy ."
    elif "pyright" in conf or (root / "pyrightconfig.json").exists():
        found["typecheck"] = "pyright"
    prefix = "uv run " if (root / "uv.lock").exists() else ""
    found.setdefault("full suite", f"{prefix}pytest")
    found.setdefault("single-file test", f"{prefix}pytest <file>")
    return True


def rust(root, found):
    if not (root / "Cargo.toml").exists():
        return False
    found.setdefault("typecheck", "cargo check --all-targets")
    found.setdefault("full suite", "cargo test")
    found.setdefault("single-file test", "cargo test <name>")
    return True


def go(root, found):
    if not (root / "go.mod").exists():
        return False
    found.setdefault("typecheck", "go build ./...")
    found.setdefault("full suite", "go test ./...")
    found.setdefault("single-file test", "go test ./<package>")
    return True


def detect(root):
    """Return (found, recognised)."""
    found = {}
    targets = make_targets(root)
    for name, keys in (("typecheck", ("typecheck", "check", "lint")), ("full suite", ("test",))):
        for key in keys:
            if key in targets:
                found[name] = f"make {key}"
                break

    recognised = any(f(root, found) for f in (node, python, rust, go))
    return found, recognised or bool(targets)


def selftest():
    import tempfile

    def run(files):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, content in files.items():
                (root / name).write_text(content, encoding="utf-8")
            return detect(root)

    found, ok = run({})
    assert not ok and found == {}, (found, ok)

    found, ok = run(
        {
            "package.json": json.dumps(
                {
                    "scripts": {"typecheck": "tsc --noEmit", "test": "vitest run"},
                    "devDependencies": {"vitest": "^1"},
                }
            )
        }
    )
    assert ok and found == {
        "typecheck": "npm run typecheck",
        "full suite": "npm run test",
        "single-file test": "npx vitest run <file>",
    }, found

    found, _ = run({"package.json": json.dumps({"devDependencies": {"typescript": "^5"}})})
    assert found["typecheck"] == "npx tsc --noEmit", found
    assert "full suite" not in found, found

    found, _ = run({"pyproject.toml": "[tool.mypy]\n", "uv.lock": ""})
    assert found == {
        "typecheck": "mypy .",
        "full suite": "uv run pytest",
        "single-file test": "uv run pytest <file>",
    }, found

    found, ok = run({"Makefile": "test:\n\tgo test ./...\ntypecheck:\n\tgo vet ./...\n"})
    assert ok and found["full suite"] == "make test" and found["typecheck"] == "make typecheck", found

    found, _ = run({"Cargo.toml": "[package]\n"})
    assert found["full suite"] == "cargo test", found

    found, ok = run({"requirements.txt": "flask\n"})
    assert ok and found["full suite"] == "pytest", found

    found, _ = run({"package.json": "{ broken"})
    assert found == {}, found

    print("selftest ok")


def main(argv):
    if argv[:1] == ["--selftest"]:
        selftest()
        return 0

    root = Path(argv[0]) if argv else Path.cwd()
    found, recognised = detect(root)
    if not recognised:
        print(f"{root}: no project manifest found — name the check commands by hand")
        return 1
    for name in ("typecheck", "single-file test", "full suite"):
        print(f"{name}: {found.get(name, 'MISSING')}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
