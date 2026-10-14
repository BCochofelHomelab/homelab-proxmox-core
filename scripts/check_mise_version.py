#!/usr/bin/env python3
"""Fail when a workflow's jdx/mise-action step doesn't pin the same mise
version as .devcontainer/post-create.sh's MISE_VERSION (which
docs/SETUP.md's install command also reads): your workstation, the
devcontainer and CI all run one mise.

Usage: check_mise_version.py (from the repo root; no arguments)
"""

import glob
import re
import sys

POST_CREATE = ".devcontainer/post-create.sh"
WORKFLOWS = ".github/workflows/*.y*ml"

MISE_VERSION = re.compile(r"MISE_VERSION=v?([0-9][0-9.]*)")
USES_MISE_ACTION = re.compile(r"^(\s*)(?:-\s+)?uses:\s*jdx/mise-action@")
VERSION_INPUT = re.compile(r"^\s+version:\s*[\"']?v?([0-9][0-9.]*)[\"']?")
STEP_START = re.compile(r"^\s*-\s")


def wanted():
    with open(POST_CREATE, encoding="utf-8") as f:
        m = MISE_VERSION.search(f.read())
    if not m:
        sys.exit(f"{POST_CREATE}: no MISE_VERSION=... found")
    return m.group(1)


def mise_action_versions(path):
    """(line number, pinned version or None) for each mise-action step."""
    lines = open(path, encoding="utf-8").read().splitlines()
    found = []
    for i, line in enumerate(lines):
        m = USES_MISE_ACTION.match(line)
        if not m:
            continue
        indent = len(m.group(1))
        version = None
        for nxt in lines[i + 1:]:
            if nxt.strip() and (len(nxt) - len(nxt.lstrip()) < indent or STEP_START.match(nxt)):
                break  # the next step, or the end of this job's steps
            v = VERSION_INPUT.match(nxt)
            if v:
                version = v.group(1)
        found.append((i + 1, version))
    return found


def main():
    want = wanted()
    problems = []
    for path in sorted(glob.glob(WORKFLOWS)):
        for line, version in mise_action_versions(path):
            if version != want:
                got = f"pins {version}" if version else "pins no version"
                problems.append(f"{path}:{line}: jdx/mise-action {got}, {POST_CREATE} has {want}")
    for p in problems:
        print(p)
    if problems:
        print("Every jdx/mise-action step sets `version:` to post-create.sh's MISE_VERSION (CONTRIBUTING.md, Toolchain).")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
