#!/usr/bin/env python3
"""Read-only integrity preflight for the installed Fleetcraft package."""
import hashlib, json, re, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
expected_files = set([".claude-plugin/plugin.json", "LICENSE", "THIRD_PARTY_NOTICES.md", "agents/executor.md", "agents/researcher.md", "agents/strategist.md", "agents/verifier.md", "hooks/README.md", "hooks/agent-telemetry.py", "hooks/autoload-judgment.py", "hooks/completion-gate.py", "hooks/evidence-batch.py", "hooks/fleet-delegation-guard.py", "hooks/fleet_hook_utils.py", "hooks/hooks.json", "hooks/judgment-kernel.md", "hooks/retrieval-honesty-guard.py", "hooks/skill-routing-guard.py", "hooks/tool-routing-guard.py", "scripts/fleetcraft-doctor.py", "skills/change-plan/SKILL.md", "skills/debugging-and-error-recovery/SKILL.md", "skills/design-judge/SKILL.md", "skills/design-judge/references/ai-slop-checklist.md", "skills/doctor/SKILL.md", "skills/fleet-orchestrator/SKILL.md", "skills/fleet-orchestrator/references/review-rubrics.md", "skills/growth-web-architect/SKILL.md", "skills/image-to-code/SKILL.md", "skills/incident-miner/SKILL.md", "skills/performance-diagnosis/SKILL.md", "skills/product-interface-craft/SKILL.md", "skills/project-handoff/SKILL.md"])
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
    if path.is_symlink(): fail("symlink " + path.relative_to(root).as_posix())
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
