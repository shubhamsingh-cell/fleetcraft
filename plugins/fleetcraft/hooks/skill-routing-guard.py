#!/usr/bin/env python3
"""UserPromptSubmit routing reminders with narrow, inspectable classifiers."""

from __future__ import annotations

import re

from fleet_hook_utils import hook_output, prompt_from_payload, read_json


FILE = r"(?:[\w.-]+[/\\])*[\w.-]+"
TABULAR_FILE = re.compile(rf"(?<!\w){FILE}\.(?:csv|tsv|parquet)(?!\w)", re.I)
DOC_FILE = re.compile(rf"(?<!\w){FILE}\.(?:docx|doc|pptx|epub|eml|msg|odt|rtf)(?!\w)", re.I)
TABULAR_INTENT = re.compile(r"\b(?:analy[sz]e|profile|summari[sz]e|query|aggregate|join|dedup(?:e|licate)|explore|count\s+rows?)\b", re.I)
DOC_INTENT = re.compile(r"\b(?:read|extract|convert|summari[sz]e|pull\s+(?:out\s+)?text)\b", re.I)
SHARE_INTENT = re.compile(r"\b(?:share|send|email|export|upload|publish|post|attach|hand\s+over)\b", re.I)
EXTERNAL_AUDIENCE = re.compile(r"\b(?:external(?:ly)?|client|customer|public(?:ly)?|outside|vendor|partner|email|slack|teams|drive|dropbox)\b", re.I)
SENSITIVE = re.compile(r"\b(?:pii|personal data|secret|credential|token|api[ _-]?key|redact|saniti[sz]e|anonymi[sz]e)\b", re.I)
VISUAL_INTENT = re.compile(r"\b(?:ship|ready|review|does\s+(?:this|it)\s+look|is\s+(?:this|it)\s+(?:good|ready))\b", re.I)
VISUAL_OBJECT = re.compile(r"\b(?:design|page|homepage|landing page|hero|ui|mockup|layout|screen|site|deck|slide|carousel|figma|visual)\b", re.I)
EXEC_INTENT = re.compile(r"\b(?:draft|write|reply|update|message|send|tell|note|ping)\b", re.I)
EXEC_AUDIENCE = re.compile(r"\b(?:ceo|executives?|leadership|board|investors?|client|founder|chief)\b", re.I)


def match_categories(prompt: str) -> list[str]:
    """Return stable category ids. Multiple reminders may be relevant."""
    matches: list[str] = []
    if TABULAR_INTENT.search(prompt) and TABULAR_FILE.search(prompt):
        matches.append("tabular-analysis")
    if DOC_INTENT.search(prompt) and DOC_FILE.search(prompt):
        matches.append("document-extraction")
    if SHARE_INTENT.search(prompt) and (EXTERNAL_AUDIENCE.search(prompt) or SENSITIVE.search(prompt)):
        matches.append("share-preflight")
    if VISUAL_INTENT.search(prompt) and VISUAL_OBJECT.search(prompt):
        matches.append("design-ship-check")
    if EXEC_INTENT.search(prompt) and EXEC_AUDIENCE.search(prompt):
        matches.append("executive-register")
    return matches


MESSAGES = {
    "tabular-analysis": "Local tabular analysis detected. Prefer a read-only query/profile workflow; use DuckDB or qsv only when those tools are installed and available in this environment.",
    "document-extraction": "Office or mail document extraction detected. Prefer a local document-to-Markdown capability when it is installed; do not assume a private runtime path exists.",
    "share-preflight": "External sharing or sensitive-data handling detected. Before anything leaves this machine, run an available local PII/secret preflight. Redacted findings are not a clearance decision.",
    "design-ship-check": "A user-facing visual surface may be heading toward ship. Render it, inspect the real result, and run the design review; an errored lens remains OPEN.",
    "executive-register": "An out-of-session executive/client audience was detected. Lead with the outcome and name the evidence; do not call something verified without its observed artifact.",
}


def main() -> None:
    payload = read_json()
    if payload is None:
        return
    prompt = prompt_from_payload(payload)
    if not prompt:
        return
    matches = match_categories(prompt)
    if matches:
        context = "Fleetcraft routing reminder (non-blocking):\n\n" + "\n\n".join(
            f"[{item}] {MESSAGES[item]}" for item in matches
        )
        hook_output("UserPromptSubmit", context)


if __name__ == "__main__":
    main()
