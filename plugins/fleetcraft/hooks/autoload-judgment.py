#!/usr/bin/env python3
import json, os
from pathlib import Path

def main():
    raw = os.environ.get("CLAUDE_PLUGIN_OPTION_AUTOLOAD_JUDGMENT", "true").lower()
    if raw in {"0", "false", "no", "off"}: return
    warning = "Fleetcraft autoload_judgment is invalid; using enabled default." if raw not in {"", "1", "true", "yes", "on"} else None
    try: text = Path(__file__).with_name("judgment-kernel.md").read_text(encoding="utf-8-sig").replace("\r\n", "\n").strip()
    except OSError: text = ""
    context = "Fleetcraft judgment kernel:\n\n" + text
    if not text or len(context) > 9000:
        print(json.dumps({"systemMessage": "Fleetcraft judgment kernel is missing or too large; kernel not loaded."}))
        return
    output = {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}}
    if warning: output["systemMessage"] = warning
    print(json.dumps(output))
if __name__ == "__main__": main()
