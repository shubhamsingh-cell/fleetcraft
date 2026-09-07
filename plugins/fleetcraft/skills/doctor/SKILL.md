---
name: doctor
description: Run Fleetcraft's read-only source or plugin preflight and report the observed result. Use after installation, hook changes, or an apparent plugin-load failure.
---

# Fleetcraft doctor

Run the applicable read-only check and report its exact output. In a source checkout:

```bash
python3 scripts/validate.py
python3 scripts/check_plugin_parity.py
```

In an installed plugin, use its bundled doctor when present. Do not install packages, change
settings, or treat a missing CLI/runtime as a passing result; report that prerequisite as OPEN.
