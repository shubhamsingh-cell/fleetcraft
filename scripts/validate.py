#!/usr/bin/env python3
"""Repo-quality validator for fleetcraft. Stdlib only, no third-party deps.

Run from anywhere; it locates the repo root from this file's own path, then
discovers skills/agents/hooks dynamically (glob, never a hardcoded list) so
it stays correct while those directories are edited independently. CI and
contributors both run this before anything is called done:

    python3 scripts/validate.py [--quiet]

Checks:
  1. Every skills/*/SKILL.md exists, opens with a `---` YAML frontmatter
     block, and that block has non-empty `name:` / `description:`. `name:`
     must match the skill's directory name. `description:` over ~500 chars
     is a WARNING (Claude Code's skill catalog has a description budget;
     long descriptions crowd out other skills), not a failure.
  2. Every agents/*.md has frontmatter with non-empty `name:` / `description:`,
     and `name:` matches the filename stem.
  3. Every hooks/*.py compiles (py_compile) and exits 0 when fed `{}` on
     stdin within a short timeout — a hook that crashes or hangs on an
     empty payload would wedge a real session. hooks/README.md is not a
     .py file so the glob skips it on its own.
  4. No file in the repo contains an absolute `/Users/` or `/home/<name>/`
     path, and no file contains a `[[wikilink]]`. This file is exempt from
     that scan (see SELF_EXEMPT below) because its own source has to spell
     out the literal patterns it's searching for.

Exit status: non-zero if any check FAILs. Warnings never fail the build.
"""
from __future__ import annotations

import argparse
import py_compile
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# This file legitimately contains the literal substrings the leak-scan looks
# for (they're the patterns themselves, not a real absolute path or a real
# wikilink) — exempt it from check 4 rather than let it flag its own source.
SELF_EXEMPT = {Path(__file__).resolve()}

# Directories never worth walking for the repo-wide content scan.
SKIP_DIR_NAMES = {".git", "__pycache__", ".pytest_cache", "node_modules"}

HOOK_STDIN_TIMEOUT_S = 5

ABS_USERS_RE = re.compile(r"/Users/[^\s'\")\]]+")
ABS_HOME_RE = re.compile(r"/home/[A-Za-z0-9_.\-]+/")
WIKILINK_RE = re.compile(r"\[\[([^\[\]\n]+)\]\]")
# Two shapes legitimately use doubled square brackets and are NOT an
# Obsidian-style [[wikilink]]: a POSIX bracket-expression character class
# (`[[:space:]]`, `[[:alpha:]]`, ...) commonly found in shell/grep/sed
# patterns, and bash's `[[ ... ]]` extended test/conditional syntax, which
# in practice always has whitespace right after the opening brackets. A
# real wikilink target never looks like either.
POSIX_CLASS_RE = re.compile(r"^:[A-Za-z]+:$")


def _is_wikilink_false_positive(inner: str) -> bool:
    if POSIX_CLASS_RE.match(inner):
        return True
    if inner[:1] in (" ", "\t"):
        return True
    return False

FRONTMATTER_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):[ \t]?(.*)$")
BLOCK_SCALAR_INDICATORS = {">", ">-", ">+", "|", "|-", "|+"}


class Report:
    def __init__(self, quiet: bool) -> None:
        self.quiet = quiet
        self.failures: list[str] = []
        self.warnings: list[str] = []
        self.checked = 0

    def ok(self, msg: str) -> None:
        self.checked += 1
        if not self.quiet:
            print(f"  ok    {msg}")

    def fail(self, msg: str) -> None:
        self.checked += 1
        self.failures.append(msg)
        print(f"  FAIL  {msg}")

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)
        print(f"  WARN  {msg}")

    def section(self, title: str) -> None:
        if not self.quiet:
            print(f"\n== {title} ==")


def read_text(path: Path) -> str | None:
    """Read a file as UTF-8 text; return None if it isn't text at all."""
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def parse_frontmatter(text: str) -> tuple[dict[str, str] | None, str | None]:
    """Extract top-level keys from a leading `---` YAML frontmatter block.

    This is not a general YAML parser — it only needs to pull scalar and
    folded/literal block-scalar values for a couple of known keys (name,
    description) out of frontmatter shapes actually used in this repo:
    quoted single-line strings, bare single-line strings, and `>`/`>-`
    folded block scalars. Good enough for validation; not a substitute for
    a real parser if the frontmatter grows more structure.
    """
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None, "does not open with a `---` frontmatter delimiter"

    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return None, "frontmatter block is never closed with a second `---`"

    fm_lines = lines[1:end_idx]
    data: dict[str, str] = {}
    i, n = 0, len(fm_lines)
    while i < n:
        line = fm_lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        if line[:1] in (" ", "\t"):
            # Not a top-level key (continuation line we didn't consume, or
            # nested structure) — skip, we only care about top-level scalars.
            i += 1
            continue
        m = FRONTMATTER_KEY_RE.match(line)
        if not m:
            i += 1
            continue
        key, rest = m.group(1), m.group(2).strip()
        if rest in BLOCK_SCALAR_INDICATORS:
            block: list[str] = []
            j = i + 1
            while j < n:
                nxt = fm_lines[j]
                if nxt.strip() == "":
                    j += 1
                    continue
                if nxt[:1] in (" ", "\t"):
                    block.append(nxt.strip())
                    j += 1
                else:
                    break
            data[key] = " ".join(block)
            i = j
            continue
        val = rest
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
            val = val[1:-1]
        data[key] = val
        i += 1
    return data, None


def check_skills(report: Report) -> None:
    report.section("skills/*/SKILL.md")
    skills_dir = REPO_ROOT / "skills"
    if not skills_dir.is_dir():
        report.warn("no skills/ directory found")
        return
    for skill_dir in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
        skill_name = skill_dir.name
        md_path = skill_dir / "SKILL.md"
        if not md_path.is_file():
            report.fail(f"skills/{skill_name}/: missing SKILL.md")
            continue
        text = read_text(md_path)
        if text is None:
            report.fail(f"{md_path.relative_to(REPO_ROOT)}: not readable as UTF-8 text")
            continue
        data, err = parse_frontmatter(text)
        if err:
            report.fail(f"{md_path.relative_to(REPO_ROOT)}: {err}")
            continue
        rel = md_path.relative_to(REPO_ROOT)
        name = (data.get("name") or "").strip()
        desc = (data.get("description") or "").strip()
        problem = False
        if not name:
            report.fail(f"{rel}: frontmatter `name:` is empty or missing")
            problem = True
        elif name != skill_name:
            report.fail(f"{rel}: frontmatter name `{name}` != directory name `{skill_name}`")
            problem = True
        if not desc:
            report.fail(f"{rel}: frontmatter `description:` is empty or missing")
            problem = True
        elif len(desc) > 500:
            report.warn(f"{rel}: description is {len(desc)} chars (budget ~500 for the skill catalog)")
        if not problem:
            report.ok(f"{rel} (name={name}, description={len(desc)} chars)")


def check_agents(report: Report) -> None:
    report.section("agents/*.md")
    agents_dir = REPO_ROOT / "agents"
    if not agents_dir.is_dir():
        report.warn("no agents/ directory found")
        return
    for md_path in sorted(agents_dir.glob("*.md")):
        stem = md_path.stem
        text = read_text(md_path)
        if text is None:
            report.fail(f"{md_path.relative_to(REPO_ROOT)}: not readable as UTF-8 text")
            continue
        data, err = parse_frontmatter(text)
        if err:
            report.fail(f"{md_path.relative_to(REPO_ROOT)}: {err}")
            continue
        rel = md_path.relative_to(REPO_ROOT)
        name = (data.get("name") or "").strip()
        desc = (data.get("description") or "").strip()
        problem = False
        if not name:
            report.fail(f"{rel}: frontmatter `name:` is empty or missing")
            problem = True
        elif name != stem:
            report.fail(f"{rel}: frontmatter name `{name}` != filename stem `{stem}`")
            problem = True
        if not desc:
            report.fail(f"{rel}: frontmatter `description:` is empty or missing")
            problem = True
        if not problem:
            report.ok(f"{rel} (name={name})")


def check_hooks(report: Report) -> None:
    report.section("hooks/*.py")
    hooks_dir = REPO_ROOT / "hooks"
    if not hooks_dir.is_dir():
        report.warn("no hooks/ directory found")
        return
    for py_path in sorted(hooks_dir.glob("*.py")):
        rel = py_path.relative_to(REPO_ROOT)

        with tempfile.NamedTemporaryFile(suffix=".pyc") as tmp_cfile:
            try:
                py_compile.compile(str(py_path), cfile=tmp_cfile.name, doraise=True)
            except py_compile.PyCompileError as exc:
                report.fail(f"{rel}: does not compile — {exc}")
                continue
            except OSError as exc:
                report.fail(f"{rel}: could not compile — {exc}")
                continue

        try:
            proc = subprocess.run(
                [sys.executable, str(py_path)],
                input=b"{}",
                capture_output=True,
                timeout=HOOK_STDIN_TIMEOUT_S,
            )
        except subprocess.TimeoutExpired:
            report.fail(f"{rel}: hung on `{{}}` stdin past {HOOK_STDIN_TIMEOUT_S}s timeout — would wedge a session")
            continue

        if proc.returncode != 0:
            stderr_tail = proc.stderr.decode("utf-8", "replace").strip().splitlines()
            tail = stderr_tail[-1] if stderr_tail else "(no stderr)"
            report.fail(f"{rel}: exited {proc.returncode} on `{{}}` stdin — {tail}")
            continue

        report.ok(f"{rel} (compiles, exits 0 on empty payload)")


def iter_scan_files():
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        if path.resolve() in SELF_EXEMPT:
            continue
        yield path


def check_no_leaked_paths(report: Report) -> None:
    report.section("repo-wide: no absolute local paths, no wikilinks")
    hits = 0
    for path in iter_scan_files():
        text = read_text(path)
        if text is None:
            continue
        rel = path.relative_to(REPO_ROOT)
        for lineno, line in enumerate(text.split("\n"), start=1):
            m = ABS_USERS_RE.search(line)
            if m:
                report.fail(f"{rel}:{lineno}: absolute /Users/ path found — `{m.group(0)}`")
                hits += 1
            m = ABS_HOME_RE.search(line)
            if m:
                report.fail(f"{rel}:{lineno}: absolute /home/<user>/ path found — `{m.group(0)}`")
                hits += 1
            for m in WIKILINK_RE.finditer(line):
                if _is_wikilink_false_positive(m.group(1)):
                    continue  # POSIX bracket class or bash `[[ ... ]]` test, not a wikilink
                report.fail(f"{rel}:{lineno}: [[wikilink]] syntax found — `{m.group(0)}`")
                hits += 1
    if hits == 0:
        report.ok("no /Users/, /home/<user>/, or [[wikilink]] hits in the tree")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--quiet", action="store_true", help="suppress per-check OK lines; failures/warnings/summary still print")
    args = parser.parse_args()

    report = Report(quiet=args.quiet)
    check_skills(report)
    check_agents(report)
    check_hooks(report)
    check_no_leaked_paths(report)

    print()
    if report.failures:
        print(f"validate.py: FAIL — {len(report.failures)} failure(s), {len(report.warnings)} warning(s) across {report.checked} checks")
        return 1
    print(f"validate.py: OK — {report.checked} checks passed, {len(report.warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
