#!/usr/bin/env python3
"""SessionStart hook that injects Fleetcraft's bundled compact judgment kernel."""

from __future__ import annotations

import os
from pathlib import Path

from fleet_hook_utils import hook_output, read_json, system_message


KERNEL = Path(__file__).with_name("judgment-kernel.md")
# Claude Code caps hook output strings at 10,000 characters. Leave room for
# the prefix and JSON escaping; never rely on truncation-to-a-file behavior.
MAX_CONTEXT_CHARS = 9_000


def autoload_enabled() -> tuple[bool, bool]:
    """Return (enabled, invalid-option); invalid values retain the safe default."""
    raw = os.environ.get("CLAUDE_PLUGIN_OPTION_AUTOLOAD_JUDGMENT", "true").strip().lower()
    if raw in {"", "1", "true", "yes", "on"}:
        return True, raw not in {"", "1", "true", "yes", "on"}
    if raw in {"0", "false", "no", "off"}:
        return False, False
    return True, True


def kernel_context(kernel: Path) -> str:
    # utf-8-sig strips an accidental BOM; text-mode reads normalize CRLF so
    # the exact hook-output budget is evaluated on the emitted characters.
    text = kernel.read_text(encoding="utf-8-sig").strip()
    context = "Fleetcraft judgment kernel (SessionStart runtime):\n\n" + text
    if len(context) > MAX_CONTEXT_CHARS:
        raise ValueError("bundled judgment kernel exceeds the safe hook-context budget")
    return context


def emit_kernel(kernel: Path = KERNEL, warning: str | None = None) -> None:
    try:
        hook_output("SessionStart", kernel_context(kernel), system_message_text=warning)
    except (OSError, UnicodeError, ValueError) as exc:
        # A corrupt package must not prevent a session from starting, but it
        # must be visible: otherwise users may assume the kernel was loaded.
        system_message(f"Fleetcraft did not load its judgment kernel ({type(exc).__name__}). Run the Fleetcraft doctor before relying on hook guidance.")


def main() -> None:
    # Consume stdin so direct invocation matches hook invocation. SessionStart
    # payload fields are deliberately not required for this deterministic hook.
    read_json()
    enabled, invalid = autoload_enabled()
    if not enabled:
        return
    warning = None
    if invalid:
        warning = "Fleetcraft autoload_judgment is invalid; using the safe default (enabled). Set it to true or false."
    emit_kernel(warning=warning)


if __name__ == "__main__":
    main()

