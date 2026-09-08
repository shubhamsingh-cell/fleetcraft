#!/usr/bin/env python3
"""Build the sparse Fleetcraft plugin from canonical repository sources.

The generated ``plugins/fleetcraft`` tree is disposable.  Skills, agents and
hooks are authored only at the repository root; this script copies those
surfaces and writes the small plugin-only runtime files deterministically.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_DEST = ROOT / "plugins" / "fleetcraft"
DEST = Path(os.environ.get("FLEETCRAFT_PLUGIN_DEST", CANONICAL_DEST))
VERSION = "0.3.0"

KERNEL = """# Fleetcraft judgment kernel

Use observed artifacts for claims. Keep user authority, do not assume an
integration is installed, and treat failed verification as open evidence.
Before an external or irreversible action, identify the exact target and
approval. A push is not a deployment.

Before specialized work, check available skill descriptions and load the
narrowest genuinely relevant skill. Skip that step for simple requests that
do not benefit. This reminder does not itself invoke a skill or grant action
authority.
"""


def copy_tree(source: Path, destination: Path) -> None:
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


TRUSTED_SYSTEM_SYMLINKS = {
    Path("/var"): Path("/private/var"),
    Path("/tmp"): Path("/private/tmp"),
    Path("/etc"): Path("/private/etc"),
}


def has_untrusted_symlink_ancestor(path: Path) -> bool:
    """Reject lexical symlinks while permitting documented macOS system aliases."""
    absolute = path.absolute()
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        if not current.is_symlink():
            continue
        if TRUSTED_SYSTEM_SYMLINKS.get(current) == current.resolve():
            continue
        return True
    return False


def resolve_destination(destination: Path) -> Path:
    """Allow only the canonical generated tree or an external path that is new."""
    if has_untrusted_symlink_ancestor(CANONICAL_DEST):
        raise ValueError("refusing canonical plugin destination beneath a symlink")
    if has_untrusted_symlink_ancestor(destination):
        raise ValueError("refusing plugin destination beneath a symlink")
    resolved = destination.resolve(strict=False)
    canonical = CANONICAL_DEST.resolve(strict=False)
    repository = ROOT.resolve()
    if resolved == canonical:
        if destination.is_symlink():
            raise ValueError("refusing symlinked canonical plugin destination")
        return resolved
    if resolved == repository or resolved in repository.parents or repository in resolved.parents:
        raise ValueError("refusing repository root, ancestor, or descendant as plugin destination")
    if resolved in canonical.parents:
        raise ValueError("refusing an ancestor of the canonical plugin destination")
    if destination.exists():
        raise ValueError("external plugin destination must be fresh and non-existent")
    return resolved


def main() -> int:
    try:
        destination = resolve_destination(DEST)
    except ValueError as exc:
        print(f"fleetcraft build: {exc}", file=sys.stderr)
        return 2
    if destination == CANONICAL_DEST.resolve(strict=False) and destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    for name in ("skills", "agents", "hooks"):
        copy_tree(ROOT / name, destination / name)
    for agent in (destination / "agents").glob("*.md"):
        # Only transform a declared skill dependency; prose and paths remain
        # portable source text rather than receiving a blanket namespace edit.
        agent.write_text(agent.read_text(encoding="utf-8").replace("  - fleet-orchestrator\n", "  - fleetcraft:fleet-orchestrator\n"), encoding="utf-8")
    shutil.copy2(ROOT / "LICENSE", destination / "LICENSE")
    notices = ROOT / "THIRD_PARTY_NOTICES.md"
    if notices.is_file():
        shutil.copy2(notices, destination / notices.name)

    write_json(destination / ".claude-plugin" / "plugin.json", {
        "$schema": "https://json.schemastore.org/claude-code-plugin-manifest.json",
        "name": "fleetcraft",
        "displayName": "Fleetcraft",
        "version": VERSION,
        "description": "Evidence-first skills, agents, and optional safety reminders.",
        "author": {"name": "Shubham Singh Chandel"},
        "license": "MIT AND Apache-2.0",
        "userConfig": {
            "autoload_judgment": {"type": "boolean", "title": "Autoload judgment kernel", "default": True, "description": "Load the bundled compact judgment kernel."},
            "delegation_mode": {"type": "string", "title": "Delegation guard mode", "default": "audit", "description": "Use audit reminders or explicit strict-mode confirmation for guarded commands."},
            "completion_gate": {"type": "boolean", "title": "Completion evidence gate", "default": False, "description": "Require evidence fields for explicitly verified tasks."},
            "evidence_batch": {"type": "boolean", "title": "Batch evidence reminders", "default": False, "description": "Summarize observed completed tool batches without treating them as proof."},
            "routing_enforce": {"type": "boolean", "title": "Routing enforcement", "default": False, "description": "Opt in to bounded documentation-routing enforcement."},
        },
    })
    marketplace_path = ROOT / ".claude-plugin" / "marketplace.json"
    if destination == CANONICAL_DEST.resolve(strict=False):
        write_json(marketplace_path, {
        "name": "fleetcraft", "owner": {"name": "Shubham Singh Chandel"}, "metadata": {"version": VERSION, "description": "Evidence-first skills, agents, and optional safety reminders."},
        "plugins": [{"name": "fleetcraft", "source": "./plugins/fleetcraft", "strict": True}],
        })
    write_json(destination / "hooks" / "hooks.json", {
        "description": "Fleetcraft optional reminders.",
        "hooks": {
            "SessionStart": [{"hooks": [{"type": "command", "command": "python3", "args": ["-B", "${CLAUDE_PLUGIN_ROOT}/hooks/autoload-judgment.py"]}]}],
            "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "python3", "args": ["-B", "${CLAUDE_PLUGIN_ROOT}/hooks/skill-routing-guard.py"]}]}],
            "PreToolUse": [
                {"matcher": "Bash|PowerShell", "hooks": [{"type": "command", "command": "python3", "args": ["-B", "${CLAUDE_PLUGIN_ROOT}/hooks/fleet-delegation-guard.py"]}]},
                {"matcher": "WebFetch|WebSearch", "hooks": [{"type": "command", "command": "python3", "args": ["-B", "${CLAUDE_PLUGIN_ROOT}/hooks/tool-routing-guard.py"]}]},
            ],
            "PostToolUse": [{"matcher": "Agent", "hooks": [{"type": "command", "command": "python3", "args": ["-B", "${CLAUDE_PLUGIN_ROOT}/hooks/agent-telemetry.py"]}]}],
            "TaskCompleted": [{"hooks": [{"type": "command", "command": "python3", "args": ["-B", "${CLAUDE_PLUGIN_ROOT}/hooks/completion-gate.py"]}]}],
            "PostToolBatch": [{"hooks": [{"type": "command", "command": "python3", "args": ["-B", "${CLAUDE_PLUGIN_ROOT}/hooks/evidence-batch.py"]}]}],
            "Stop": [{"hooks": [{"type": "command", "command": "python3", "args": ["-B", "${CLAUDE_PLUGIN_ROOT}/hooks/retrieval-honesty-guard.py"]}]}],
        },
    })
    (destination / "hooks" / "judgment-kernel.md").write_text(KERNEL, encoding="utf-8")
    # Plugin autoload must be self-contained, unlike the manual installer hook.
    plugin_autoload = '''#!/usr/bin/env python3\nimport json, os\nfrom pathlib import Path\n\ndef main():\n    raw = os.environ.get("CLAUDE_PLUGIN_OPTION_AUTOLOAD_JUDGMENT", "true").lower()\n    if raw in {"0", "false", "no", "off"}: return\n    warning = "Fleetcraft autoload_judgment is invalid; using enabled default." if raw not in {"", "1", "true", "yes", "on"} else None\n    try: text = Path(__file__).with_name("judgment-kernel.md").read_text(encoding="utf-8-sig").replace("\\r\\n", "\\n").strip()\n    except OSError: text = ""\n    context = "Fleetcraft judgment kernel:\\n\\n" + text\n    if not text or len(context) > 9000:\n        print(json.dumps({"systemMessage": "Fleetcraft judgment kernel is missing or too large; kernel not loaded."}))\n        return\n    output = {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}}\n    if warning: output["systemMessage"] = warning\n    print(json.dumps(output))\nif __name__ == "__main__": main()\n'''
    (destination / "hooks" / "autoload-judgment.py").write_text(plugin_autoload, encoding="utf-8")
    doctor = '''#!/usr/bin/env python3
"""Read-only integrity preflight for the installed Fleetcraft package."""
import hashlib, json, re, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
expected_files = set(__EXPECTED_FILES__)
errors = []
def fail(message): errors.append(message); print("Fleetcraft doctor: FAIL " + message)
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
try:
    inventory = json.loads((root / "scripts" / "distribution-inventory.json").read_text(encoding="utf-8"))["files"]
except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
    fail("readable distribution inventory (" + str(exc) + ")"); inventory = {}
actual_files = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file() and path.relative_to(root).as_posix() != "scripts/distribution-inventory.json"}
actual_dirs = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_dir()}
loader_dir = root / ".in_use"
if loader_dir.is_dir() and not loader_dir.is_symlink() and not any(loader_dir.iterdir()): actual_dirs.discard(".in_use")
expected_dirs = set()
for rel in expected_files:
    parent = Path(rel).parent
    while str(parent) != ".":
        expected_dirs.add(parent.as_posix())
        parent = parent.parent
for path in root.rglob("*"):
    rel = path.relative_to(root).as_posix()
    if path.is_symlink(): fail("symlink " + rel)
    elif not path.is_file() and not path.is_dir(): fail("unsupported filesystem entry " + rel)
if set(inventory) != expected_files: fail("inventory path set")
if actual_files != expected_files: fail("unexpected or missing files")
if actual_dirs != expected_dirs: fail("unexpected or missing directories")
for rel, expected in inventory.items():
    path = root / rel
    if not path.is_file(): fail("missing " + rel)
    elif digest(path) != expected: fail("modified " + rel)
for rel in ("LICENSE", "THIRD_PARTY_NOTICES.md", ".claude-plugin/plugin.json", "hooks/hooks.json", "skills/doctor/SKILL.md"):
    if not (root / rel).is_file(): fail("missing required " + rel)
try:
    hooks = json.loads((root / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]
    for groups in hooks.values():
        for group in groups:
            for handler in group["hooks"]:
                args = handler.get("args", [])
                if handler.get("command") != "python3" or not args or args[0] != "-B": fail("invalid hook command")
                elif not (root / args[-1].replace("${CLAUDE_PLUGIN_ROOT}/", "")).is_file(): fail("missing registered hook " + str(args[-1]))
except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc: fail("valid hook registration (" + str(exc) + ")")
for agent in (root / "agents").glob("*.md"):
    for skill in re.findall(r"- fleetcraft:([a-z0-9-]+)", agent.read_text(encoding="utf-8")):
        if not (root / "skills" / skill / "SKILL.md").is_file(): fail("agent dependency " + skill)
for hook in (root / "hooks").glob("*.py"):
    try: compile(hook.read_text(encoding="utf-8"), str(hook), "exec")
    except (OSError, SyntaxError) as exc: fail("hook syntax " + hook.name + " (" + str(exc) + ")")
if errors: print("Fleetcraft doctor: " + str(len(errors)) + " issue(s)"); sys.exit(1)
print("Fleetcraft doctor: PASS")
'''
    (destination / "scripts").mkdir(exist_ok=True)
    doctor_path = destination / "scripts" / "fleetcraft-doctor.py"
    doctor_path.write_text(doctor, encoding="utf-8")
    expected_files = sorted(
        path.relative_to(destination).as_posix()
        for path in destination.rglob("*")
        if path.is_file() and path.relative_to(destination).as_posix() != "scripts/distribution-inventory.json"
    )
    doctor_path.write_text(doctor.replace("__EXPECTED_FILES__", json.dumps(expected_files)), encoding="utf-8")
    inventory = {
        path.relative_to(destination).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in destination.rglob("*")
        if path.is_file() and path.relative_to(destination).as_posix() != "scripts/distribution-inventory.json"
    }
    write_json(destination / "scripts" / "distribution-inventory.json", {"files": inventory})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
