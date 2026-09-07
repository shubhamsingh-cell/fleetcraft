import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


PATH = Path(__file__).parents[1] / "scripts" / "evaluate_skills.py"
spec = importlib.util.spec_from_file_location("evaluate_skills", PATH)
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)


def stream(skill="fleetcraft:change-plan", *, result="unknown deployment is unapproved", model="claude-sonnet-5", plugins=None, cwd="/tmp/cwd", tool_result=None):
    tool_result = tool_result if tool_result is not None else "Launching skill: " + skill
    return "\n".join(json.dumps(event) for event in [
        {"type": "system", "subtype": "init", "session_id": "session", "model": model, "plugins": plugins or [], "cwd": cwd, "claude_code_version": "2.1.263", "tools": ["Glob", "Grep", "Read", "Skill"], "mcp_servers": []},
        {"type": "assistant", "session_id": "session", "message": {"content": [
            {"type": "tool_use", "id": "call", "name": "Skill", "input": {"skill": skill}}]}},
        {"type": "user", "session_id": "session", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "call", "content": tool_result}]}},
        {"type": "result", "subtype": "success", "session_id": "session", "result": result,
         "num_tokens": 7, "cost_usd": 0.01},
    ])


def case():
    return {"id": "plan", "prompt": "Read fixture.", "fixtures": [], "expected_skill": "change-plan",
            "quality": {"required": ["unknown", "unapproved"], "max_words": 220}}


def record(directory, mode="candidate", *, model="claude-sonnet-5", prompt="Read fixture."):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    candidate_case = case()
    candidate_case["prompt"] = prompt
    run_cwd = directory / "cwd"
    live_plugin = run_cwd / "fleetcraft"
    plugins = [{"name": "fleetcraft", "path": str(live_plugin.resolve()), "version": "0.3.0"}] if mode == "candidate" else []
    observed_skill = "fleetcraft:change-plan" if mode == "candidate" else "builtin:math"
    (directory / "stream.jsonl").write_text(stream(skill=observed_skill, model=model, plugins=plugins, cwd=str(run_cwd.resolve())), encoding="utf-8")
    (directory / "stderr.txt").write_text("", encoding="utf-8")
    (directory / "mcp.json").write_text('{"mcpServers":{}}\n', encoding="utf-8")
    ev.write_json(directory / "case.json", candidate_case)
    (directory / "prompt.txt").write_text(prompt, encoding="utf-8")
    plugin = directory / "plugin"
    inventory = []
    if mode == "candidate":
        skill = plugin / "skills" / "change-plan"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("---\nname: change-plan\n---\n", encoding="utf-8")
        manifest = plugin / ".claude-plugin"
        manifest.mkdir()
        (manifest / "plugin.json").write_text('{"version":"0.3.0"}\n', encoding="utf-8")
        inventory = ev.plugin_inventory(plugin)
    ev.write_json(directory / "plugin-inventory.json", inventory)
    _, init, terminal, _ = ev.trace((directory / "stream.jsonl").read_text())
    verdicts = ev.assess((directory / "stream.jsonl").read_text(), "change-plan" if mode == "candidate" else None, live_plugin if mode == "candidate" else None, candidate_case)
    value = {
        "schema": 2, "run_id": "id-" + mode, "mode": mode, "case": "plan", "expected_skill": "change-plan",
        "request_settings": {"model_alias": "sonnet", "budget": 0.25, "timeout": 90, "tools": ev.TOOLS,
                             "restricted": True, "strict_mcp_config": True, "no_session_persistence": True},
        "returncode": 0, "timed_out": False, "stream_sha256": ev.sha(directory / "stream.jsonl"),
        "stderr_sha256": ev.sha(directory / "stderr.txt"), "mcp_sha256": ev.sha(directory / "mcp.json"), "case_sha256": ev.sha(directory / "case.json"),
        "prompt_sha256": ev.sha(directory / "prompt.txt"), "fixtures": {},
        "plugin_inventory_sha256": ev.sha(directory / "plugin-inventory.json"),
        "trace_integrity": verdicts[0], "activation": verdicts[1], "output_quality": verdicts[2],
        "telemetry": ev.telemetry(init, terminal), "init_plugins": plugins, "init_cwd": str(run_cwd.resolve()),
        "plugin_root": str(live_plugin.resolve()) if mode == "candidate" else None,
        "command": ev.command(prompt, mode, live_plugin if mode == "candidate" else Path("/no-plugin"), directory / "mcp.json", "sonnet", 0.25),
        "cli_version": "2.1.263",
    }
    ev.write_json(directory / "record.json", value)
    return directory / "record.json"


class EvalTraceTests(unittest.TestCase):
    def test_valid_exact_skill_and_quality(self):
        answer = "Stage one maps fullName to name. Stage two updates clients. The unknown consumer remains open. Deployment is unapproved. Rollback restores fullName during monitored release validation and approval review."
        trace, activation, output, _ = ev.assess(stream(result=answer), "change-plan", case=case())
        self.assertEqual((trace, activation, output), ("PASS", "PASS", "PASS"))

    def test_skill_needs_exact_launch_result(self):
        self.assertEqual(ev.assess(stream(tool_result="ok"), "change-plan")[1], "FAIL")
        self.assertEqual(ev.assess(stream(tool_result="Error: Unknown skill"), "change-plan")[1], "FAIL")

    def test_rejects_missing_terminal_error_and_non_object_event(self):
        self.assertEqual(ev.assess(stream().rsplit("\n", 1)[0], "change-plan")[0], "FAIL")
        self.assertEqual(ev.assess(stream().replace('"success"', '"error"'), "change-plan")[0], "FAIL")
        self.assertEqual(ev.assess('[]', "change-plan")[0], "FAIL")

    def test_rejects_terminal_session_post_terminal_and_bad_blocks(self):
        self.assertEqual(ev.assess(stream().replace('"session_id": "session", "result"', '"session_id": "other", "result"'), "change-plan")[0], "FAIL")
        self.assertEqual(ev.assess(stream() + '\n' + json.dumps({"type": "user", "session_id": "session"}), "change-plan")[0], "FAIL")
        malformed = stream().replace('[{"type": "tool_use"', '["not-a-block", {"type": "tool_use"')
        self.assertEqual(ev.assess(malformed, "change-plan")[0], "FAIL")

    def test_rejects_unknown_and_error_events(self):
        events = ev.parse_stream(stream())
        for injected in ({"type": "system", "subtype": "error", "session_id": "session"},
                         {"type": "mystery", "session_id": "session"}):
            raw = "\n".join(json.dumps(event) for event in events[:-1] + [injected, events[-1]])
            self.assertEqual(ev.assess(raw, "change-plan")[0], "FAIL")

    def test_accepts_only_completed_sessionstart_hook_prelude(self):
        events = ev.parse_stream(stream())
        hook_id = "redacted-hook"
        prelude = [
            {"type": "system", "subtype": "hook_started", "hook_id": hook_id,
             "hook_name": "SessionStart:startup", "hook_event": "SessionStart", "session_id": "session"},
            {"type": "system", "subtype": "hook_response", "hook_id": hook_id,
             "hook_name": "SessionStart:startup", "hook_event": "SessionStart", "session_id": "session",
             "exit_code": 0, "outcome": "success"},
        ]
        raw = "\n".join(json.dumps(event) for event in prelude + events)
        self.assertEqual(ev.assess(raw, "change-plan")[0:2], ("PASS", "PASS"))
        pending = "\n".join(json.dumps(event) for event in prelude[:1] + events)
        self.assertEqual(ev.assess(pending, "change-plan")[0], "FAIL")
        failed = "\n".join(json.dumps(event) for event in [{**prelude[0]}, {**prelude[1], "exit_code": 1}] + events)
        self.assertEqual(ev.assess(failed, "change-plan")[0], "FAIL")
        foreign = "\n".join(json.dumps(event) for event in [{"type": "assistant", "session_id": "session"}] + events)
        self.assertEqual(ev.assess(foreign, "change-plan")[0], "FAIL")

    def test_rejects_duplicate_orphan_and_partial_results(self):
        duplicate = stream().replace(']}}\n{"type": "result"', ']}}\n{"type": "user", "session_id": "session", "message": {"content": [{"type": "tool_result", "tool_use_id": "call"}]}}\n{"type": "result"')
        self.assertEqual(ev.assess(duplicate, "change-plan")[0], "FAIL")
        orphan = stream().replace('"tool_use_id": "call"', '"tool_use_id": "other"')
        self.assertEqual(ev.assess(orphan, "change-plan")[0], "FAIL")

    def test_exact_read_binding_rejects_suffix_spoof(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "plugin"
            target = root / "skills" / "change-plan" / "SKILL.md"
            target.parent.mkdir(parents=True)
            target.write_text("x")
            raw = stream(skill="builtin").replace('"name": "Skill", "input": {"skill": "builtin"}', '"name": "Read", "input": {"file_path": "' + str(target) + '.bak"}')
            self.assertEqual(ev.assess(raw, "change-plan", root)[1], "FAIL")

    def test_read_replay_uses_snapshot_after_runtime_directory_is_gone(self):
        with tempfile.TemporaryDirectory() as directory:
            snapshot = Path(directory) / "snapshot"
            skill = snapshot / "skills" / "change-plan"
            skill.mkdir(parents=True)
            content = "---\nname: change-plan\n---\nbody\n"
            (skill / "SKILL.md").write_text(content, encoding="utf-8")
            runtime_root = Path(directory) / "deleted-runtime"
            events = ev.parse_stream(stream())
            events[1]["message"]["content"][0] = {"type": "tool_use", "id": "call", "name": "Read",
                                                       "input": {"file_path": str(runtime_root / "skills" / "change-plan" / "SKILL.md")}}
            events[2]["message"]["content"][0]["content"] = "1\t---\n2\tname: change-plan\n3\t---\n4\tbody"
            raw = "\n".join(json.dumps(event) for event in events)
            self.assertEqual(ev.assess(raw, "change-plan", runtime_root, snapshot_root=snapshot)[1], "PASS")
            events[2]["message"]["content"][0]["content"] = "1\tpartial"
            self.assertEqual(ev.assess("\n".join(json.dumps(event) for event in events), "change-plan", runtime_root, snapshot_root=snapshot)[1], "OPEN")

    def test_negative_allows_builtin_but_rejects_fleetcraft(self):
        self.assertEqual(ev.assess(stream(skill="builtin:math"), None)[1], "PASS")
        self.assertEqual(ev.assess(stream(), None)[1], "FAIL")

    def test_quality_requires_facts_and_handles_negated_forbidden_phrase(self):
        quality_case = {"quality": {"required": ["120", "400", "approval"],
                                    "forbidden_regex": [r"(?<!not )\bdeployed\b"], "max_words": 8}}
        self.assertEqual(ev.quality("120 400 approval not deployed", quality_case)[0], "PASS")
        self.assertEqual(ev.quality("120 400 approval deployed", quality_case)[0], "FAIL")
        self.assertEqual(ev.quality("120 400", quality_case)[0], "FAIL")

    def test_replay_recomputes_and_rejects_tampered_raw_prompt_and_verdict(self):
        with tempfile.TemporaryDirectory() as directory:
            path = record(Path(directory) / "candidate")
            self.assertTrue(ev.validate_record(path)[0])
            (path.parent / "stream.jsonl").write_text("tampered")
            self.assertFalse(ev.validate_record(path)[0])
            path = record(Path(directory) / "candidate2")
            (path.parent / "prompt.txt").write_text("changed")
            self.assertFalse(ev.validate_record(path)[0])
            path = record(Path(directory) / "candidate3")
            value = ev.load_record(path)
            value["activation"] = "FAIL"
            ev.write_json(path, value)
            self.assertFalse(ev.validate_record(path)[0])

    def test_replay_requires_actual_init_model_and_successful_return(self):
        with tempfile.TemporaryDirectory() as directory:
            path = record(Path(directory) / "candidate")
            value = ev.load_record(path)
            value["telemetry"]["actual_init_model"] = None
            ev.write_json(path, value)
            self.assertFalse(ev.validate_record(path)[0])

    def test_replay_rejects_settings_plugin_and_session_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            path = record(Path(directory) / "settings")
            value = ev.load_record(path)
            value["request_settings"]["budget"] = 1.0
            ev.write_json(path, value)
            self.assertFalse(ev.validate_record(path)[0])

            path = record(Path(directory) / "empty-dir")
            (path.parent / "plugin" / "unexpected-empty").mkdir()
            self.assertFalse(ev.validate_record(path)[0])

            path = record(Path(directory) / "mcp-path")
            value = ev.load_record(path)
            value["command"][value["command"].index("--mcp-config") + 1] = "/tmp/evil.json"
            ev.write_json(path, value)
            self.assertFalse(ev.validate_record(path)[0])

            path = record(Path(directory) / "plugin")
            skill = path.parent / "plugin" / "skills" / "change-plan" / "SKILL.md"
            skill.write_text("tampered", encoding="utf-8")
            self.assertFalse(ev.validate_record(path)[0])

    def test_replay_rejects_extra_plugin_missing_isolation_and_wrong_skill(self):
        with tempfile.TemporaryDirectory() as directory:
            path = record(Path(directory) / "plugins")
            value = ev.load_record(path)
            value["init_plugins"].append({"name": "other", "path": "/tmp/other", "version": "1"})
            ev.write_json(path, value)
            self.assertFalse(ev.validate_record(path)[0])

            path = record(Path(directory) / "skill")
            value = ev.load_record(path)
            value["expected_skill"] = "doctor"
            ev.write_json(path, value)
            self.assertFalse(ev.validate_record(path)[0])

            path = record(Path(directory) / "session")
            raw = (path.parent / "stream.jsonl").read_text().replace('"session_id": "session", "result"', '"session_id": "other", "result"')
            (path.parent / "stream.jsonl").write_text(raw, encoding="utf-8")
            value = ev.load_record(path)
            value["stream_sha256"] = ev.sha(path.parent / "stream.jsonl")
            ev.write_json(path, value)
            self.assertFalse(ev.validate_record(path)[0])
            path = record(Path(directory) / "candidate2")
            value = ev.load_record(path)
            value["returncode"] = 1
            ev.write_json(path, value)
            self.assertFalse(ev.validate_record(path)[0])

    def test_compare_requires_complete_unique_matching_pair(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            candidate = record(directory / "candidate", "candidate")
            baseline = record(directory / "baseline", "baseline")
            self.assertEqual(ev.compare([candidate, baseline], {"plan"})["plan"]["pair_integrity"], "COMPARABLE")
            self.assertEqual(ev.compare([candidate], {"plan"})["plan"]["pair_integrity"], "OPEN")
            self.assertEqual(ev.compare([candidate, baseline, baseline], {"plan"})["plan"]["pair_integrity"], "OPEN")
            changed = record(directory / "changed", "baseline", model="other-model")
            self.assertEqual(ev.compare([candidate, changed], {"plan"})["plan"]["pair_integrity"], "OPEN")

    def test_compare_rejects_different_case_rubric_with_same_prompt_and_fixtures(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            candidate = record(directory / "candidate", "candidate")
            baseline = record(directory / "baseline", "baseline")
            case_file = baseline.parent / "case.json"
            changed_case = json.loads(case_file.read_text())
            changed_case["quality"]["min_words"] = 9
            ev.write_json(case_file, changed_case)
            value = ev.load_record(baseline)
            value["case_sha256"] = ev.sha(case_file)
            value["output_quality"] = ev.assess((baseline.parent / "stream.jsonl").read_text(), None, None, changed_case)[2]
            ev.write_json(baseline, value)
            self.assertTrue(ev.validate_record(candidate)[0])
            self.assertTrue(ev.validate_record(baseline)[0])
            self.assertEqual(ev.compare([candidate, baseline], {"plan"})["plan"]["pair_integrity"], "OPEN")

    def test_mocked_run_snapshots_and_replays_without_live_provider(self):
        with tempfile.TemporaryDirectory() as directory:
            original = ev.subprocess.run

            def fake_run(command, **kwargs):
                if command[1:] == ["--version"]:
                    return SimpleNamespace(returncode=0, stdout="2.1.263\n", stderr="")
                plugin = command[command.index("--plugin-dir") + 1]
                raw = stream(plugins=[{"name": "fleetcraft", "path": str(Path(plugin).resolve()), "version": "0.3.0"}], cwd=str(kwargs["cwd"].resolve()))
                return SimpleNamespace(returncode=0, stdout=raw, stderr="")

            ev.subprocess.run = fake_run
            try:
                args = SimpleNamespace(output_dir=Path(directory), mode="candidate", model="sonnet", budget=.25, timeout=90)
                produced = ev.run(case(), args)
            finally:
                ev.subprocess.run = original
            record_path = next(Path(directory).rglob("record.json"))
            self.assertEqual(produced["telemetry"]["actual_init_model"], "claude-sonnet-5")
            self.assertTrue(ev.validate_record(record_path)[0])


if __name__ == "__main__":
    unittest.main()
