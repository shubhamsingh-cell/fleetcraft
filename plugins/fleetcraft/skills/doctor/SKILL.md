---
name: doctor
description: Run Fleetcraft's read-only package preflight and report the exact result. Use after installation, after plugin or hook changes, or when a Fleetcraft hook appears not to load.
---

# Fleetcraft doctor

Run this bundled, read-only command and return its exact PASS/FAIL summary:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/fleetcraft-doctor.py"
```

Do not install packages, alter Claude settings, or hide a failed check. If the command
cannot resolve `python3` or the plugin root, report that prerequisite as OPEN. In a source
checkout, the maintainer may additionally run `python3 scripts/validate-plugin.py` to
validate both the marketplace and plugin schemas with the installed Claude Code CLI.
