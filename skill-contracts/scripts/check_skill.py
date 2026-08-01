#!/usr/bin/env python3
"""Check a SKILL.md against the mechanical rules in skill-contracts.

Usage: check_skill.py [PATH ...]     PATH is a SKILL.md or a skill directory.
Exit 1 if any error is found. Warnings do not fail the run.
"""

import re
import sys
from pathlib import Path

SPRAWL_LINES = 150
KNOWN_KEYS = {"name", "description", "disable-model-invocation", "allowed-tools", "license"}

TRIGGER = re.compile(r"\bwhen\b|\btriggers?\b", re.I)
NEGATION = re.compile(r"^\s*(?:[-*]\s*)?(?:\*\*)?(don't|do not|never)\b", re.I)
LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def parse_frontmatter(text):
    """Return (dict, body_offset_line) or (None, 0) if absent/unterminated."""
    if not text.startswith("---\n"):
        return None, 0
    lines = text.split("\n")
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            fm = {}
            for raw in lines[1:i]:
                if not raw.strip() or raw.lstrip().startswith("#"):
                    continue
                key, sep, value = raw.partition(":")
                if sep:
                    fm[key.strip()] = value.strip()
            return fm, i + 1
    return None, 0


def check(path):
    """Return (errors, warnings) for one SKILL.md."""
    errors, warnings = [], []
    text = path.read_text(encoding="utf-8")
    fm, body_start = parse_frontmatter(text)

    if fm is None:
        return ["no terminated YAML frontmatter"], []

    for key in fm:
        near = key.replace("_", "-")
        if key not in KNOWN_KEYS and near in KNOWN_KEYS:
            errors.append(f"frontmatter key {key!r} is inert — did you mean {near!r}?")

    name = fm.get("name")
    if not name:
        errors.append("frontmatter has no name")
    elif name != path.parent.name:
        errors.append(f"name {name!r} does not match directory {path.parent.name!r}")

    user_invoked = fm.get("disable-model-invocation", "").lower() == "true"
    description = fm.get("description", "")
    if not description:
        errors.append("frontmatter has no description")
    elif user_invoked and TRIGGER.search(description):
        warnings.append("user-invoked skill keeps trigger phrasing no agent can read")
    elif not user_invoked and not TRIGGER.search(description):
        warnings.append("model-invoked description lists no trigger — it may never fire")

    for target in {m for line in text.split("\n") for m in LINK.findall(line)}:
        if re.match(r"^[a-z]+:|^[#/]|^~", target):
            continue
        if not (path.parent / target.split("#")[0]).exists():
            errors.append(f"dangling link: {target}")

    body = text.split("\n")[body_start:]
    if len(body) > SPRAWL_LINES:
        warnings.append(f"sprawl: {len(body)} body lines (over {SPRAWL_LINES})")
    for offset, line in enumerate(body, start=body_start + 1):
        if NEGATION.match(line):
            warnings.append(f"line {offset}: negation — state the positive target instead")

    return errors, warnings


def selftest():
    import tempfile

    def run(dirname, content):
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / dirname
            skill.mkdir()
            (skill / "SKILL.md").write_text(content, encoding="utf-8")
            return check(skill / "SKILL.md")

    good = "---\nname: alpha\ndescription: Use when testing.\n---\n\nBody.\n"
    assert run("alpha", good) == ([], []), run("alpha", good)

    errs, _ = run("beta", good)
    assert any("does not match directory" in e for e in errs), errs

    errs, _ = run("alpha", "no frontmatter here\n")
    assert errs == ["no terminated YAML frontmatter"], errs

    errs, _ = run("alpha", "---\nname: alpha\n---\nx\n")
    assert any("no description" in e for e in errs), errs

    errs, _ = run("alpha", "---\nname: alpha\ndisable_model_invocation: true\n---\nx\n")
    assert any("did you mean 'disable-model-invocation'" in e for e in errs), errs

    assert run("alpha", "---\nname: alpha\ndescription: Use when x.\nsource: y\n---\nz\n") == ([], [])

    errs, _ = run("alpha", good + "\nSee [gone](nope.md).\n")
    assert any("dangling link: nope.md" in e for e in errs), errs

    _, warns = run("alpha", good + "\nNever do the thing.\n")
    assert any("negation" in w for w in warns), warns

    quiet = "---\nname: alpha\ndescription: A reference.\ndisable-model-invocation: true\n---\n\nBody.\n"
    assert run("alpha", quiet) == ([], []), run("alpha", quiet)

    print("selftest ok")


def main(argv):
    if argv[:1] == ["--selftest"]:
        selftest()
        return 0

    targets = [Path(a) for a in argv] or [Path.cwd()]
    failed = False
    for target in targets:
        path = target / "SKILL.md" if target.is_dir() else target
        if not path.exists():
            print(f"{target}: no SKILL.md")
            failed = True
            continue
        errors, warnings = check(path)
        for w in warnings:
            print(f"{path}: warn: {w}")
        for e in errors:
            print(f"{path}: error: {e}")
        if errors:
            failed = True
        elif not warnings:
            print(f"{path}: ok")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
