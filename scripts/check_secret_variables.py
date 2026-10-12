#!/usr/bin/env python3
"""Fail when a secret-named OpenTofu or Packer variable has a default or
isn't sensitive (docs/CREDENTIALS.md, "Secret tiers": a secret never gets
a default, so a missing one fails instead of falling back to a value).

A variable is secret-named when its name matches SECRET_NAME. Names that
only look secret go in ALLOWLIST, each with the reason it isn't one.

Usage: check_secret_variables.py FILE... (*.tf, *.pkr.hcl)
"""

import re
import sys

SECRET_NAME = re.compile(r"token|secret|password|passwd|hash|private_key|api_key")

# name: why it isn't a secret. Reviewed like any other change.
ALLOWLIST = {
    "proxmox_api_token_id": "an identifier (user@realm!token), not the token's secret",
    "ssh_private_key_file": "a path on your machine, not the key",
}

VARIABLE = re.compile(r'^\s*variable\s+"([^"]+)"\s*\{')
HEREDOC = re.compile(r"<<-?([A-Za-z_][A-Za-z0-9_]*)")


def top_level_lines(lines, start):
    """The variable block's own lines from `start` (its `{` line), without
    nested blocks (validation), strings, heredocs or comments. Returns the
    lines at depth 1 and the index after the block."""
    depth, out, i, heredoc = 0, [], start, None
    while i < len(lines):
        line = lines[i]
        if heredoc:
            if line.strip() == heredoc:
                heredoc = None
            i += 1
            continue
        code, j, in_string = "", 0, False
        while j < len(line):
            c = line[j]
            if in_string:
                if c == "\\":
                    j += 1
                elif c == '"':
                    in_string = False
                j += 1
                continue
            if c == '"':
                in_string = True
            elif c == "#" or line.startswith("//", j):
                break
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return out + [code], i + 1
            elif depth == 1:
                code += c
            j += 1
        if depth == 1:
            out.append(code)
        m = HEREDOC.search(line)
        if m and depth >= 1:
            heredoc = m.group(1)
        i += 1
    return out, i


def check(path):
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    problems, i = [], 0
    while i < len(lines):
        m = VARIABLE.match(lines[i])
        if not m:
            i += 1
            continue
        name = m.group(1)
        body, i = top_level_lines(lines, i)
        if not SECRET_NAME.search(name) or name in ALLOWLIST:
            continue
        attrs = {}
        for line in body:
            a = re.match(r"\s*([A-Za-z_]+)\s*=\s*(\S*)", line)
            if a:
                attrs[a.group(1)] = a.group(2)
        if "default" in attrs:
            problems.append(f"{path}: variable \"{name}\" is secret-named and has a default")
        if attrs.get("sensitive") != "true":
            problems.append(f"{path}: variable \"{name}\" is secret-named and isn't sensitive = true")
    return problems


def main(paths):
    problems = [p for path in paths for p in check(path)]
    for p in problems:
        print(p)
    if problems:
        print("A secret gets no default and sensitive = true (docs/CREDENTIALS.md, \"Secret tiers\");")
        print("a name that only looks secret goes in ALLOWLIST in scripts/check_secret_variables.py.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
