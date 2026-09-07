#!/usr/bin/env python3
"""Offline-safe Fleetcraft evaluation runner and canonical trace validator."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "evals" / "skill-routing.json"
TOOLS = "Read,Glob,Grep,Skill"
SUCCESS_SUBTYPES = {"success", "result_success"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def json_sha(value: Any) -> str:
    return text_sha(json.dumps(value, sort_keys=True, separators=(",", ":")))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load() -> list[dict[str, Any]]:
    data = json.loads(CORPUS.read_text(encoding="utf-8"))
    cases = data.get("cases")
    if not isinstance(cases, list) or len(cases) < 12:
        raise ValueError("corpus needs at least 12 cases")
    valid_skills = {path.parent.name for path in (ROOT / "plugins" / "fleetcraft" / "skills").glob("*/SKILL.md")}
    ids: set[str] = set()
    for case in cases:
        if not isinstance(case, dict) or set(case) != {"id", "prompt", "fixtures", "expected_skill", "quality"} or not isinstance(case.get("id"), str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", case["id"]):
            raise ValueError("every case needs an id")
        if case["id"] in ids:
            raise ValueError("duplicate case: " + case["id"])
        ids.add(case["id"])
        if not isinstance(case.get("prompt"), str) or not case["prompt"]:
            raise ValueError("invalid prompt: " + case["id"])
        if case.get("expected_skill") is not None and (not isinstance(case.get("expected_skill"), str) or case["expected_skill"] not in valid_skills):
            raise ValueError("unknown expected skill: " + case["id"])
        if not isinstance(case.get("fixtures"), list) or not isinstance(case.get("quality"), dict):
            raise ValueError("fixtures and quality required: " + case["id"])
        quality = case["quality"]
        unsupported = set(quality) - {"mode", "required", "forbidden_regex", "max_words", "min_words"}
        if unsupported or quality.get("mode", "deterministic") not in {"deterministic", "not_evaluated"}:
            raise ValueError("unsupported quality metadata: " + case["id"])
        if not isinstance(quality.get("required", []), list) or any(not isinstance(value, str) or not value for value in quality.get("required", [])):
            raise ValueError("invalid required facts: " + case["id"])
        if not isinstance(quality.get("forbidden_regex", []), list) or any(not isinstance(value, str) for value in quality.get("forbidden_regex", [])):
            raise ValueError("invalid forbidden regex: " + case["id"])
        try:
            for expression in quality.get("forbidden_regex", []):
                re.compile(expression)
        except re.error as exc:
            raise ValueError("invalid forbidden regex: " + case["id"]) from exc
        max_words, min_words = quality.get("max_words", 220), quality.get("min_words", 1)
        if (type(max_words) is not int or not 1 <= max_words <= 220 or type(min_words) is not int or not 1 <= min_words <= max_words):
            raise ValueError("invalid word bounds: " + case["id"])
        if quality.get("mode", "deterministic") == "deterministic" and not quality.get("required") and case["id"] not in {"plan", "debug"}:
            raise ValueError("deterministic quality needs required facts: " + case["id"])
        if len(case["fixtures"]) != len(set(case["fixtures"])):
            raise ValueError("duplicate fixture: " + case["id"])
        for fixture in case["fixtures"]:
            if not isinstance(fixture, str) or "/" in fixture or "\\" in fixture or ".." in fixture:
                raise ValueError("invalid fixture name: " + repr(fixture))
            if not (ROOT / "evals" / "fixtures" / fixture).is_file():
                raise ValueError("missing fixture: " + fixture)
    return cases


def parse_stream(raw: str) -> list[dict[str, Any]]:
    if not raw.strip():
        raise ValueError("empty stream")
    events: list[dict[str, Any]] = []
    for number, line in enumerate(raw.splitlines(), 1):
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"malformed json line {number}") from exc
        if not isinstance(event, dict):
            raise ValueError(f"non-object event at line {number}")
        events.append(event)
    return events


def content_blocks(event: dict[str, Any]) -> list[dict[str, Any]]:
    message = event.get("message")
    if message is None:
        return []
    if not isinstance(message, dict):
        raise ValueError("non-object message")
    content = message.get("content", [])
    if not isinstance(content, list) or any(not isinstance(block, dict) for block in content):
        raise ValueError("non-object content block")
    return content


def validate_sessionstart_prelude(events: list[dict[str, Any]], init_index: int, session: str) -> None:
    """Accept only completed SessionStart hook pairs before the canonical init event."""
    prelude = events[:init_index]
    if not prelude:
        return
    if len(prelude) % 2:
        raise ValueError("pending SessionStart hook prelude")
    for position in range(0, len(prelude), 2):
        started, response = prelude[position:position + 2]
        if started.get("type") != "system" or started.get("subtype") != "hook_started":
            raise ValueError("non-hook event before init")
        if response.get("type") != "system" or response.get("subtype") != "hook_response":
            raise ValueError("SessionStart hook response missing")
        fields = ("hook_id", "hook_name", "hook_event")
        if (any(started.get(field) != response.get(field) for field in fields)
                or started.get("hook_event") != "SessionStart"
                or not isinstance(started.get("hook_id"), str)
                or not isinstance(started.get("hook_name"), str)
                or started.get("session_id") != session
                or response.get("session_id") != session
                or response.get("exit_code") != 0
                or response.get("outcome") != "success"):
            raise ValueError("invalid SessionStart hook lifecycle")


def trace(raw: str) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any], dict[str, tuple[str, dict[str, Any], str]]]:
    """Parse canonical events, preserving order and binding every tool result."""
    events = parse_stream(raw)
    init_events = [event for event in events if event.get("type") == "system" and event.get("subtype") == "init"]
    terminal_events = [event for event in events if event.get("type") == "result"]
    if len(init_events) != 1 or len(terminal_events) != 1:
        raise ValueError("need exactly one init and terminal")
    init, terminal = init_events[0], terminal_events[0]
    init_index = events.index(init)
    session = init.get("session_id")
    if not isinstance(session, str) or not session:
        raise ValueError("init needs nonempty session")
    validate_sessionstart_prelude(events, init_index, session)
    if events[-1] is not terminal:
        raise ValueError("event after terminal")
    if terminal.get("session_id") != session:
        raise ValueError("terminal session mismatch")
    if terminal.get("is_error") is True or terminal.get("subtype") not in SUCCESS_SUBTYPES:
        raise ValueError("terminal not successful")

    calls: dict[str, tuple[str, dict[str, Any]]] = {}
    results: dict[str, str] = {}
    for index, event in enumerate(events):
        if event.get("session_id") != session:
            raise ValueError("session mismatch")
        if index < init_index:
            continue
        event_type = event.get("type")
        if event_type == "system" and event.get("subtype") not in {"init", "thinking_tokens"}:
            raise ValueError("unknown or error system event")
        if event_type not in {"system", "assistant", "user", "rate_limit_event", "result"}:
            raise ValueError("unknown event type")
        if event_type == "assistant":
            for block in content_blocks(event):
                if block.get("type") != "tool_use":
                    continue
                tool_id, name, tool_input = block.get("id"), block.get("name"), block.get("input")
                if not isinstance(tool_id, str) or not tool_id or tool_id in calls:
                    raise ValueError("duplicate or invalid tool id")
                if not isinstance(name, str) or not isinstance(tool_input, dict):
                    raise ValueError("invalid tool use")
                calls[tool_id] = (name, tool_input)
        elif event_type == "user":
            for block in content_blocks(event):
                if block.get("type") != "tool_result":
                    continue
                tool_id = block.get("tool_use_id")
                if not isinstance(tool_id, str) or tool_id not in calls or tool_id in results:
                    raise ValueError("orphan or duplicate tool result")
                if block.get("is_error") is True:
                    raise ValueError("error tool result")
                content = block.get("content")
                if not isinstance(content, str) or not content:
                    raise ValueError("empty or non-text tool result")
                results[tool_id] = content
    if set(calls) != set(results):
        raise ValueError("partial tool results")
    bound = {tool_id: (name, tool_input, results[tool_id]) for tool_id, (name, tool_input) in calls.items()}
    return events, init, terminal, bound


def extract_answer(terminal: dict[str, Any]) -> str | None:
    for field in ("result", "text"):
        value = terminal.get(field)
        if isinstance(value, str):
            return value
    return None


def strip_cli_line_prefixes(content: str) -> str:
    return "\n".join(re.sub(r"^\d+\t", "", line) for line in content.splitlines()).strip()


def activation(calls: dict[str, tuple[str, dict[str, Any], str]], expected: str | None, plugin_root: Path | None,
               snapshot_root: Path | None = None) -> tuple[str, str]:
    plugin_root = plugin_root.resolve() if plugin_root else None
    if expected is None:
        for name, tool_input, _ in calls.values():
            if name == "Skill" and isinstance(tool_input.get("skill"), str) and tool_input["skill"].startswith("fleetcraft:"):
                return "FAIL", "Fleetcraft Skill activated for negative case"
            if name == "Read" and plugin_root and isinstance(tool_input.get("file_path"), str):
                try:
                    target = Path(tool_input["file_path"]).resolve()
                except OSError:
                    continue
                if plugin_root in (target, *target.parents):
                    return "FAIL", "Fleetcraft Read activated for negative case"
        return "PASS", "no Fleetcraft activation"

    expected_path = (plugin_root / "skills" / expected / "SKILL.md").resolve() if plugin_root else None
    for name, tool_input, result_content in calls.values():
        expected_skill = f"fleetcraft:{expected}"
        if name == "Skill" and tool_input.get("skill") == expected_skill:
            if result_content == f"Launching skill: {expected_skill}":
                return "PASS", "exact namespaced Skill with launch result"
            return "FAIL", "Skill result did not prove launch"
        if name == "Read" and expected_path and isinstance(tool_input.get("file_path"), str):
            try:
                if Path(tool_input["file_path"]).resolve() == expected_path:
                    snapshot_path = ((snapshot_root / "skills" / expected / "SKILL.md") if snapshot_root else expected_path)
                    if not snapshot_path.is_file():
                        return "OPEN", "expected generated SKILL.md unavailable for Read verification"
                    if strip_cli_line_prefixes(result_content) == snapshot_path.read_text(encoding="utf-8").strip():
                        return "PASS", "exact generated SKILL.md Read with complete content"
                    return "OPEN", "SKILL.md Read content is partial or mismatched"
            except OSError:
                continue
    return "FAIL", "expected Fleetcraft activation absent"


def quality(answer: str | None, case: dict[str, Any]) -> tuple[str, str]:
    requirements = case["quality"]
    if requirements.get("mode") == "not_evaluated":
        return "NOT_EVALUATED", "routing-only case"
    if not isinstance(answer, str):
        return "OPEN", "terminal has no text result"
    if len(answer.split()) > requirements.get("max_words", 220):
        return "FAIL", "word limit exceeded"
    lowered = answer.lower()
    if len(answer.split()) < requirements.get("min_words", 1):
        return "FAIL", "response is too short for the registered checks"
    if case.get("id") == "plan":
        required_groups = [("unknown", "unidentified"), ("unapproved", "not approved", "not authorized"),
                           ("fullname", "fullName".lower()), ("name",), ("stage",), ("rollback",)]
        if any(not any(token.lower() in lowered for token in group) for group in required_groups):
            return "FAIL", "plan misses a required field, authorization, stage, or rollback fact"
    for fact in requirements.get("required", []):
        if fact.lower() not in lowered:
            return "FAIL", "missing required fact: " + fact
    for expression in requirements.get("forbidden_regex", []):
        if re.search(expression, answer, flags=re.IGNORECASE):
            return "FAIL", "forbidden invention: " + expression
    return "PASS", "deterministic requirements met"


def assess(raw: str, expected: str | None, plugin_root: Path | None = None, case: dict[str, Any] | None = None,
           snapshot_root: Path | None = None) -> tuple[str, str, str, str]:
    try:
        _, _, terminal, calls = trace(raw)
    except ValueError as exc:
        return "FAIL", "OPEN", "NOT_EVALUATED", str(exc)
    selected, selection_detail = activation(calls, expected, plugin_root, snapshot_root)
    if case is None:
        return "PASS", selected, "NOT_EVALUATED", selection_detail
    output_quality, quality_detail = quality(extract_answer(terminal), case)
    return "PASS", selected, output_quality, selection_detail + "; " + quality_detail


def telemetry(init: dict[str, Any], terminal: dict[str, Any]) -> dict[str, Any]:
    return {
        "actual_init_model": init.get("model") or init.get("model_name"),
        "tokens": terminal.get("usage") if "usage" in terminal else terminal.get("num_tokens"),
        "cache": terminal.get("cache") if "cache" in terminal else terminal.get("cache_read_input_tokens"),
        "cost": terminal.get("total_cost_usd") if "total_cost_usd" in terminal else terminal.get("cost_usd"),
    }


def init_plugins(init: dict[str, Any]) -> Any:
    """Preserve the init declaration verbatim enough to prove plugin presence/absence."""
    plugins = init.get("plugins", init.get("plugin_info", []))
    if not isinstance(plugins, (list, dict)):
        raise ValueError("invalid init plugin declaration")
    return plugins


def mentions_fleetcraft(plugins: Any) -> bool:
    return "fleetcraft" in json.dumps(plugins, sort_keys=True).lower()


def plugin_inventory(root: Path) -> list[dict[str, Any]]:
    if not root.is_dir():
        return []
    inventory = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("plugin snapshot contains symlink: " + str(path))
        if path.is_dir():
            inventory.append({"type": "directory", "path": path.relative_to(root).as_posix(),
                              "mode": path.stat().st_mode & 0o777})
        if path.is_file():
            inventory.append({"type": "file", "path": path.relative_to(root).as_posix(),
                              "sha256": sha(path), "mode": path.stat().st_mode & 0o777})
    return inventory


def decode_partial(value: str | bytes | None) -> str:
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value or ""


def command(prompt: str, mode: str, plugin: Path, mcp: Path, model: str, budget: float) -> list[str]:
    result = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose", "--restricted",
              "--strict-mcp-config", "--mcp-config", str(mcp), "--setting-sources", "", "--permission-mode",
              "dontAsk", "--tools", TOOLS, "--allowedTools", TOOLS, "--no-session-persistence", "--model",
              model, "--max-budget-usd", str(budget)]
    if mode == "candidate":
        result += ["--plugin-dir", str(plugin.resolve())]
    if mode == "disabled-control":
        result += ["--disable-slash-commands"]
    return result


def normalized_settings(args: argparse.Namespace) -> dict[str, Any]:
    return {"model_alias": args.model, "budget": args.budget, "timeout": args.timeout, "tools": TOOLS,
            "restricted": True, "strict_mcp_config": True, "no_session_persistence": True}


def cli_version(env: dict[str, str]) -> str | None:
    try:
        result = subprocess.run(["claude", "--version"], env=env, text=True, capture_output=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def snapshot_case(out: Path, case: dict[str, Any], plugin: Path | None) -> dict[str, Any]:
    write_json(out / "case.json", case)
    prompt = out / "prompt.txt"
    prompt.write_text(case["prompt"], encoding="utf-8")
    fixtures: dict[str, str] = {}
    fixture_dir = out / "fixtures"
    fixture_dir.mkdir()
    for name in case["fixtures"]:
        target = fixture_dir / name
        shutil.copy2(ROOT / "evals" / "fixtures" / name, target)
        fixtures[name] = sha(target)
    inventory: list[dict[str, Any]] = []
    if plugin:
        snapshot = out / "plugin"
        shutil.copytree(plugin, snapshot)
        inventory = plugin_inventory(snapshot)
    write_json(out / "plugin-inventory.json", inventory)
    return {"case_sha256": sha(out / "case.json"), "prompt_sha256": sha(prompt), "fixtures": fixtures,
            "plugin_inventory_sha256": sha(out / "plugin-inventory.json")}


def run(case: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    run_id = str(uuid.uuid4())
    out = args.output_dir / run_id / args.mode / case["id"]
    out.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix="fleetcraft-eval-") as temporary_name:
        temporary = Path(temporary_name)
        cwd = temporary / "cwd"
        cwd.mkdir()
        plugin = cwd / "fleetcraft"
        if args.mode == "candidate":
            shutil.copytree(ROOT / "plugins" / "fleetcraft", plugin)
        for fixture in case["fixtures"]:
            destination = cwd / "fixtures" / fixture
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / "evals" / "fixtures" / fixture, destination)
        mcp = temporary / "mcp.json"
        mcp.write_text('{"mcpServers":{}}\n', encoding="utf-8")
        environment = {**os.environ, "CLAUDE_CONFIG_DIR": str(temporary / "config")}
        invocation = command(case["prompt"], args.mode, plugin, mcp, args.model, args.budget)
        started = time.monotonic()
        timed_out = False
        try:
            result = subprocess.run(invocation, cwd=cwd, env=environment, text=True, capture_output=True, timeout=args.timeout, check=False)
            raw, stderr, returncode = result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired as exc:
            timed_out, raw, stderr, returncode = True, decode_partial(exc.stdout), decode_partial(exc.stderr), None
        duration = time.monotonic() - started
        (out / "stream.jsonl").write_text(raw, encoding="utf-8")
        (out / "stderr.txt").write_text(stderr, encoding="utf-8")
        shutil.copy2(mcp, out / "mcp.json")
        snapshots = snapshot_case(out, case, plugin if args.mode == "candidate" else None)
        try:
            _, init, terminal, _ = trace(raw)
            expected = case.get("expected_skill") if args.mode == "candidate" else None
            trace_verdict, activation_verdict, quality_verdict, proof = assess(raw, expected, plugin if args.mode == "candidate" else None, case)
            observed_telemetry = telemetry(init, terminal)
            observed_plugins = init_plugins(init)
            observed_cwd = init.get("cwd")
        except ValueError as exc:
            trace_verdict, activation_verdict, quality_verdict, proof = "FAIL", "OPEN", "NOT_EVALUATED", str(exc)
            observed_telemetry = {"actual_init_model": None, "tokens": None, "cache": None, "cost": None}
            observed_plugins = []
            observed_cwd = None
        if timed_out or returncode != 0:
            trace_verdict, activation_verdict, quality_verdict, proof = "FAIL", "OPEN", "NOT_EVALUATED", "timeout or nonzero returncode"
        record = {"schema": 2, "run_id": run_id, "mode": args.mode, "case": case["id"], "expected_skill": case.get("expected_skill"),
                  "request_settings": normalized_settings(args), "command": invocation, "returncode": returncode, "timed_out": timed_out,
                  "duration_s": duration, "cli_version": cli_version(environment), "mcp_sha256": sha(out / "mcp.json"), "stream_sha256": sha(out / "stream.jsonl"),
                  "stderr_sha256": sha(out / "stderr.txt"), **snapshots, "trace_integrity": trace_verdict, "activation": activation_verdict,
                  "output_quality": quality_verdict, "proof": proof, "telemetry": observed_telemetry,
                  "init_plugins": observed_plugins, "init_cwd": observed_cwd,
                  "plugin_root": str(plugin.resolve()) if args.mode == "candidate" else None}
        write_json(out / "record.json", record)
        return record


def load_record(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("invalid record json") from exc
    if not isinstance(value, dict):
        raise ValueError("record must be object")
    return value


def validate_record(path: str | Path) -> tuple[bool, str]:
    """Replay self-contained snapshots and reject changed/incomplete evidence."""
    try:
        path = Path(path)
        record = load_record(path)
        required = {"schema", "run_id", "mode", "case", "expected_skill", "request_settings", "returncode", "timed_out",
                    "stream_sha256", "stderr_sha256", "case_sha256", "prompt_sha256", "fixtures", "plugin_inventory_sha256",
                    "trace_integrity", "activation", "output_quality", "telemetry", "init_plugins", "plugin_root",
                    "init_cwd", "command", "cli_version", "mcp_sha256"}
        if record.get("schema") != 2 or not required.issubset(record):
            raise ValueError("missing required record fields")
        directory = path.parent
        stream, stderr, mcp_file = directory / "stream.jsonl", directory / "stderr.txt", directory / "mcp.json"
        case_file, prompt_file, inventory_file = directory / "case.json", directory / "prompt.txt", directory / "plugin-inventory.json"
        for item in (stream, stderr, mcp_file, case_file, prompt_file, inventory_file):
            if not item.is_file():
                raise ValueError("missing snapshot: " + item.name)
        if sha(stream) != record["stream_sha256"] or sha(stderr) != record["stderr_sha256"]:
            raise ValueError("raw artifact hash mismatch")
        if sha(mcp_file) != record["mcp_sha256"] or mcp_file.read_text(encoding="utf-8") != '{"mcpServers":{}}\n':
            raise ValueError("MCP snapshot mismatch")
        if sha(case_file) != record["case_sha256"] or sha(prompt_file) != record["prompt_sha256"]:
            raise ValueError("case or prompt hash mismatch")
        case = json.loads(case_file.read_text(encoding="utf-8"))
        if not isinstance(case, dict) or case.get("id") != record["case"] or case.get("prompt") != prompt_file.read_text(encoding="utf-8"):
            raise ValueError("case snapshot mismatch")
        if case.get("expected_skill") != record["expected_skill"]:
            raise ValueError("expected skill does not match case snapshot")
        if not isinstance(record["fixtures"], dict):
            raise ValueError("invalid fixtures")
        for name, digest in record["fixtures"].items():
            fixture = directory / "fixtures" / name
            if not isinstance(name, str) or "/" in name or ".." in name or not fixture.is_file() or sha(fixture) != digest:
                raise ValueError("fixture hash mismatch")
        if set(record["fixtures"]) != set(case.get("fixtures", [])):
            raise ValueError("fixture set mismatch")
        inventory = json.loads(inventory_file.read_text(encoding="utf-8"))
        if sha(inventory_file) != record["plugin_inventory_sha256"]:
            raise ValueError("plugin inventory hash mismatch")
        plugin = directory / "plugin"
        if record["mode"] == "candidate":
            if not plugin.is_dir() or plugin_inventory(plugin) != inventory:
                raise ValueError("plugin snapshot mismatch")
        elif inventory or plugin.exists():
            raise ValueError("non-candidate includes plugin snapshot")
        raw = stream.read_text(encoding="utf-8")
        _, init, terminal, _ = trace(raw)
        if init_plugins(init) != record["init_plugins"]:
            raise ValueError("init plugin declaration does not recompute")
        if init.get("cwd") != record["init_cwd"] or not isinstance(record["init_cwd"], str) or not record["init_cwd"]:
            raise ValueError("init cwd does not recompute")
        expected_tools = ["Glob", "Grep", "Read"] if record["mode"] == "disabled-control" else ["Glob", "Grep", "Read", "Skill"]
        if init.get("tools") != expected_tools or init.get("mcp_servers") != []:
            raise ValueError("init does not prove requested tools and empty MCP isolation")
        if record["mode"] == "candidate":
            fleet_plugins = [item for item in record["init_plugins"] if isinstance(item, dict) and item.get("name") == "fleetcraft"] if isinstance(record["init_plugins"], list) else []
            if len(record["init_plugins"]) != 1 or len(fleet_plugins) != 1 or fleet_plugins[0].get("path") != record["plugin_root"] or not isinstance(fleet_plugins[0].get("version"), str):
                raise ValueError("candidate init does not identify Fleetcraft path and version")
            if not isinstance(record["plugin_root"], str) or not Path(record["plugin_root"]).is_absolute():
                raise ValueError("invalid candidate plugin root")
            if Path(record["plugin_root"]) != Path(record["init_cwd"]) / "fleetcraft":
                raise ValueError("candidate plugin path is not the isolated cwd fleetcraft copy")
            manifest = plugin / ".claude-plugin" / "plugin.json"
            if not manifest.is_file() or json.loads(manifest.read_text(encoding="utf-8")).get("version") != fleet_plugins[0]["version"]:
                raise ValueError("candidate plugin version differs from snapshot manifest")
        if record["mode"] != "candidate" and record["init_plugins"] != []:
            raise ValueError("non-candidate init contains plugins")
        expected = case.get("expected_skill") if record["mode"] == "candidate" else None
        replay_root = Path(record["plugin_root"]) if record["plugin_root"] else None
        verdicts = assess(raw, expected, replay_root, case, plugin if plugin.is_dir() else None)
        if verdicts[:3] != (record["trace_integrity"], record["activation"], record["output_quality"]):
            raise ValueError("stored verdict does not recompute")
        if record["mode"] != "candidate" and record["activation"] != "PASS":
            raise ValueError("baseline has Fleetcraft activation contamination")
        if telemetry(init, terminal) != record["telemetry"]:
            raise ValueError("telemetry does not recompute")
        if record["returncode"] != 0 or record["timed_out"] is not False:
            raise ValueError("record did not complete successfully")
        if not isinstance(record["request_settings"], dict) or not record["telemetry"].get("actual_init_model"):
            raise ValueError("missing request settings or actual init model")
        if not isinstance(record["command"], list) or "--model" not in record["command"]:
            raise ValueError("invalid command")
        try:
            expected_settings = {"model_alias", "budget", "timeout", "tools", "restricted", "strict_mcp_config", "no_session_persistence"}
            if set(record["request_settings"]) != expected_settings or record["request_settings"]["tools"] != TOOLS or not all(record["request_settings"][key] is True for key in ("restricted", "strict_mcp_config", "no_session_persistence")):
                raise ValueError("invalid request settings")
            recorded_mcp = Path(record["command"][record["command"].index("--mcp-config") + 1])
            runtime_mcp = (Path(record["init_cwd"]).parent / "mcp.json").resolve()
            if recorded_mcp.resolve() != runtime_mcp:
                raise ValueError("command MCP path differs from isolated runtime path")
            expected_command = command(case["prompt"], record["mode"], replay_root or Path("/no-plugin"), recorded_mcp,
                                       record["request_settings"]["model_alias"], record["request_settings"]["budget"])
        except (KeyError, ValueError, IndexError, TypeError) as exc:
            raise ValueError("cannot rebuild command") from exc
        if record["command"] != expected_command or not isinstance(record["cli_version"], str) or not record["cli_version"]:
            raise ValueError("command or CLI version mismatch")
        init_version = init.get("claude_code_version")
        if init_version is not None and not record["cli_version"].startswith(str(init_version)):
            raise ValueError("CLI version differs from init version")
    except (ValueError, TypeError, OSError, json.JSONDecodeError) as exc:
        return False, str(exc)
    return True, "record replays"


def candidate_acceptance(record: dict[str, Any]) -> str:
    verdicts = (record["trace_integrity"], record["activation"], record["output_quality"])
    if verdicts[0] == "PASS" and verdicts[1] == "PASS" and verdicts[2] in {"PASS", "NOT_EVALUATED"}:
        return "PASS"
    return "FAIL" if "FAIL" in verdicts else "OPEN"


def compare(paths: list[str | Path], scope: set[str] | None = None) -> dict[str, dict[str, str]]:
    """Keep provenance comparability separate from candidate acceptance and quality."""
    valid_records: list[dict[str, Any]] = []
    errors = False
    for given in paths:
        valid, _ = validate_record(given)
        if not valid:
            errors = True
            continue
        valid_records.append(load_record(Path(given)))
    corpus_ids = {case["id"] for case in load()}
    target = scope if scope is not None else corpus_ids
    if not target or not target.issubset(corpus_ids):
        return {"_errors": {"pair_integrity": "OPEN", "candidate_acceptance": "OPEN"}}
    output = {case: {"pair_integrity": "OPEN", "candidate_acceptance": "OPEN"} for case in sorted(target)}
    if errors:
        output["_errors"] = {"pair_integrity": "OPEN", "candidate_acceptance": "OPEN"}
        return output
    grouped: dict[str, dict[str, dict[str, Any]]] = {}
    duplicate = False
    for record in valid_records:
        if record["case"] not in target:
            continue
        modes = grouped.setdefault(record["case"], {})
        if record["mode"] in modes:
            duplicate = True
        modes[record["mode"]] = record
    for case in target:
        modes = grouped.get(case, {})
        if duplicate or "candidate" not in modes or "baseline" not in modes:
            continue
        candidate, baseline = modes["candidate"], modes["baseline"]
        signature = lambda record: (record["case_sha256"], record["prompt_sha256"], json.dumps(record["fixtures"], sort_keys=True),
                                    json.dumps(record["request_settings"], sort_keys=True), record["telemetry"]["actual_init_model"],
                                    record["cli_version"])
        if signature(candidate) == signature(baseline):
            output[case] = {"pair_integrity": "COMPARABLE", "candidate_acceptance": candidate_acceptance(candidate)}
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--case")
    parser.add_argument("--mode", choices=["candidate", "baseline", "disabled-control"], default="candidate")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts" / "evals")
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--budget", type=float, default=0.25)
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--validate-record")
    parser.add_argument("--compare", nargs="+")
    parser.add_argument("--scope", nargs="*")
    args = parser.parse_args()
    if args.validate_record:
        valid, detail = validate_record(args.validate_record)
        if not valid:
            print("FAIL " + detail)
            return 1
        record = load_record(Path(args.validate_record))
        print("PASS replay integrity; trace={}; activation={}; quality={}; acceptance={}".format(
            record["trace_integrity"], record["activation"], record["output_quality"], candidate_acceptance(record)))
        return 0
    if args.compare:
        result = compare(args.compare, set(args.scope) if args.scope else None)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if all(value["pair_integrity"] == "COMPARABLE" and value["candidate_acceptance"] == "PASS"
                        for value in result.values()) else 1
    try:
        cases = load()
    except (ValueError, json.JSONDecodeError) as exc:
        print("FAIL corpus: " + str(exc))
        return 1
    if args.case:
        cases = [case for case in cases if case["id"] == args.case]
    if not cases:
        print("FAIL case")
        return 1
    if not args.live:
        print(f"PASS structural: {len(cases)} cases; live requires --live")
        return 0
    records = [run(case, args) for case in cases]
    print(json.dumps(records, indent=2, sort_keys=True))
    acceptable_quality = {"PASS", "NOT_EVALUATED"}
    return 0 if all(record["trace_integrity"] == "PASS" and record["activation"] == "PASS"
                       and record["output_quality"] in acceptable_quality for record in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
