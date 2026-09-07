"""Behavioural + robustness suite for the five hooks in hooks/.

RUNS TWO WAYS (both must pass):
    python3 -m unittest discover -s tests -v
    python3 -m pytest tests/ -q

STDLIB ONLY. No pytest-specific fixtures/imports are used anywhere in this
file (pytest is only used, when present, as an alternate *runner* for the
same unittest.TestCase classes -- see tests/README.md).

Every hook is invoked as a real subprocess (`python3 hooks/<name>.py` with
JSON piped to stdin), never imported -- see tests/_hook_runner.py for the
shared plumbing and the filesystem-isolation contract (HOME/TMPDIR pointed
at a fresh tempfile.TemporaryDirectory per test; tool-routing-guard's own
state dir is pointed at a temp dir explicitly via CLAUDE_TOOL_ROUTING_STATE_DIR).

=============================================================================
THE NON-NEGOTIABLE DESIGN RULE -- NEGATIVE CONTROLS
=============================================================================
A test suite that only ever feeds a hook the payload it's SUPPOSED to react
to proves nothing: a hook that unconditionally prints nothing (or
unconditionally prints the reminder) would pass every one of those checks
just as well as a correctly-discriminating hook. The two look identical from
a happy-path-only suite.

So every behavioural assertion in this file ships in a PAIR:
  - a "fires" test: a realistic payload that SHOULD trigger the hook,
    asserting the specific decision/injection the source code says it
    should produce, AND
  - a "silent" / "allows" test: a realistic payload that should NOT trigger
    it, asserting no injection happened -- this is the negative control.
A hook that always stays silent passes the "silent" half and fails the
"fires" half. A hook that always fires (a stuck/gutted "helpfully" prints
everything) passes the "fires" half and fails the "silent" half. Only a
hook that actually discriminates passes both. This is checked for real in
the neutered-hook demonstration described in tests/README.md: a copy of a
hook made to unconditionally exit 0 printing nothing is run against a
one-off subset of this suite and DOES fail it, which is the whole point.

Trigger strings and regex-derived substrings below are copied from each
hook's own source (SHAPES / LONG_RUN / INSTALL in fleet-delegation-guard.py,
CATEGORIES in skill-routing-guard.py, DOCS_URL / MSG_* in tool-routing-guard.py,
TELLS in retrieval-honesty-guard.py) specifically so these tests track the
real matchers rather than a paraphrase of them that could silently drift.
"""
import json
import os
import unittest
from pathlib import Path

from _hook_runner import IsolatedHookTestCase, TIMEOUT


# =============================================================================
# 1. autoload-judgment.py -- SessionStart
# =============================================================================
class TestAutoloadJudgment(IsolatedHookTestCase):
    """This hook never reads stdin at all -- it unconditionally reads
    ~/.claude/skills/fable-judgment/SKILL.md (Path.home(), which respects
    $HOME) and injects its body, stripped of YAML frontmatter and the
    changelog blockquote between the H1 and the first '## ' section.

    The natural positive/negative CONTROL PAIR here is "skill file present
    under the (fake, temp) HOME" vs. "skill file absent" -- present must
    inject, absent must stay silent. Both cases are exercised with a fully
    isolated HOME so the real ~/.claude/skills/fable-judgment/SKILL.md
    (which exists on this machine and contains this user's private
    judgment notes) is never touched or leaked into test output.
    """

    SAMPLE_SKILL = """---
description: test skill, not the real fable-judgment content
---
# Test Judgment Skill

> changelog v1 -- should be stripped
> changelog v2 -- should be stripped

## 1. First section
alpha content marker AAA111

## 2. Second section
beta content marker BBB222

## 3. Third section
gamma content marker CCC333

## 4. Fourth section
delta content marker DDD444
"""

    def _write_fake_skill(self):
        skill_dir = self.home / ".claude" / "skills" / "fable-judgment"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(self.SAMPLE_SKILL, encoding="utf-8")

    # -- fires: skill present -------------------------------------------
    def test_fires_when_skill_present(self):
        self._write_fake_skill()
        proc = self.run_hook("autoload_judgment", "")
        data = self.assert_fires(proc, contains="fable-judgment skill (auto-loaded by SessionStart hook")
        ctx = data["hookSpecificOutput"]["additionalContext"]
        self.assertEqual(data["hookSpecificOutput"]["hookEventName"], "SessionStart")
        # All four judgment sections made it through.
        for marker in ("AAA111", "BBB222", "CCC333", "DDD444"):
            self.assertIn(marker, ctx)
        # Frontmatter and changelog were stripped, not injected verbatim.
        self.assertNotIn("description: test skill", ctx)
        self.assertNotIn("changelog v1", ctx)
        self.assertNotIn("changelog v2", ctx)
        self.assertIn("version history omitted from context", ctx)

    # -- silent (negative control): skill absent -------------------------
    def test_silent_when_skill_absent(self):
        # self.home has no .claude/ dir at all -- fresh temp HOME.
        proc = self.run_hook("autoload_judgment", "")
        self.assert_silent(proc, "skill file does not exist under this temp HOME")

    # -- fail-open / robustness ------------------------------------------
    def test_robust_to_garbage_stdin_regardless_of_skill_presence(self):
        """This hook ignores stdin entirely, so garbage stdin must never
        change its behaviour or crash it -- verified for both the present
        and absent skill-file cases."""
        garbage_inputs = ["", "{}", "{not valid json", "null", "42", "[1,2,3]", "\x00\x01binary"]
        with self.subTest(skill="absent"):
            for text in garbage_inputs:
                with self.subTest(stdin=text):
                    proc = self.run_hook("autoload_judgment", text)
                    self.assert_silent(proc)
        self._write_fake_skill()
        with self.subTest(skill="present"):
            for text in garbage_inputs:
                with self.subTest(stdin=text):
                    proc = self.run_hook("autoload_judgment", text)
                    self.assert_fires(proc, contains="fable-judgment skill (auto-loaded by SessionStart hook")

    def test_falls_back_to_untouched_body_on_unexpected_skill_shape(self):
        """If the skill file's shape doesn't match what the stripper
        expects (no '# ' H1, or no '## ' section), _strip_version_header
        must fail toward MORE context, not less -- inject the whole body
        rather than risk mangling it. Exercised here because it's the
        hook's own documented fail-toward-more-context contract, not
        just an implementation detail."""
        skill_dir = self.home / ".claude" / "skills" / "fable-judgment"
        skill_dir.mkdir(parents=True)
        odd_body = "no heading structure here at all, just prose ZZZ999\n"
        (skill_dir / "SKILL.md").write_text(odd_body, encoding="utf-8")
        proc = self.run_hook("autoload_judgment", "")
        data = self.assert_fires(proc)
        self.assertIn("ZZZ999", data["hookSpecificOutput"]["additionalContext"])


# =============================================================================
# 2. fleet-delegation-guard.py -- PreToolUse / Bash
# =============================================================================
class TestFleetDelegationGuard(IsolatedHookTestCase):
    HOOK = "fleet_delegation_guard"

    # -- silent (negative control) ---------------------------------------
    def test_silent_on_ordinary_command(self):
        proc = self.run_hook_json(self.HOOK, {"tool_input": {"command": "ls -la"}})
        self.assert_silent(proc)

    # -- fires: deploy-shaped ---------------------------------------------
    def test_fires_on_deploy_shape_git_commit(self):
        proc = self.run_hook_json(self.HOOK, {"tool_input": {"command": "git commit -m 'x'"}})
        data = self.assert_fires(proc, contains="deploy/publish-shaped")
        ctx = data["hookSpecificOutput"]["additionalContext"]
        self.assertIn("MAIN-LOOP ORCHESTRATOR", ctx)  # main-loop branch, not subagent-short branch

    def test_fires_on_deploy_shape_gh_pr_create(self):
        proc = self.run_hook_json(self.HOOK, {"tool_input": {"command": "gh pr create --title x"}})
        self.assert_fires(proc, contains="deploy/publish-shaped")

    def test_fires_on_deploy_shape_worktree_git_push(self):
        # 2026-07-15 extension: `git -C <worktree> push` must still match.
        proc = self.run_hook_json(
            self.HOOK, {"tool_input": {"command": "git -C /tmp/wt push origin main"}}
        )
        self.assert_fires(proc, contains="deploy/publish-shaped")

    # -- fires: long-run-shaped (opposite-direction warning) --------------
    def test_fires_on_long_run_shape_pytest(self):
        proc = self.run_hook_json(self.HOOK, {"tool_input": {"command": "pytest tests/ -q"}})
        self.assert_fires(proc, contains="LONG-LIVED RUN")

    def test_fires_on_long_run_shape_npm_build(self):
        proc = self.run_hook_json(self.HOOK, {"tool_input": {"command": "npm run build"}})
        self.assert_fires(proc, contains="LONG-LIVED RUN")

    # -- fires: install-shaped ---------------------------------------------
    def test_fires_on_install_shape_npm_add_package(self):
        proc = self.run_hook_json(self.HOOK, {"tool_input": {"command": "npm install lodash"}})
        self.assert_fires(proc, contains="INSTALLS a third-party package")

    def test_silent_on_bare_lockfile_restore_npm(self):
        """Negative control for the install shape: a bare `npm install`
        (no package name -- a lockfile restore) must NOT nag, per the
        module docstring's explicit design note."""
        proc = self.run_hook_json(self.HOOK, {"tool_input": {"command": "npm install"}})
        self.assert_silent(proc)

    def test_silent_on_bare_lockfile_restore_pip(self):
        proc = self.run_hook_json(
            self.HOOK, {"tool_input": {"command": "pip install -r requirements.txt"}}
        )
        self.assert_silent(proc)

    # -- subagent asymmetry -------------------------------------------------
    def test_subagent_deploy_shape_gets_short_gitleaks_only_message(self):
        """Deploy-shaped + subagent (agent_id present) is the DESIRED end
        state -- no delegation nag, only the gitleaks preflight line."""
        proc = self.run_hook_json(
            self.HOOK,
            {"tool_input": {"command": "git push origin main"}, "agent_id": "agent-123"},
        )
        data = self.assert_fires(proc, contains="gitleaks skill offers a redacted local secret preflight")
        ctx = data["hookSpecificOutput"]["additionalContext"]
        self.assertNotIn("MAIN-LOOP ORCHESTRATOR", ctx)

    def test_subagent_detected_via_transcript_path_fallback(self):
        """agent_id absent but transcript_path contains '/subagents/' must
        also count as a subagent (the documented fallback discriminator)."""
        proc = self.run_hook_json(
            self.HOOK,
            {
                "tool_input": {"command": "git commit -m x"},
                "transcript_path": "/tmp/session/subagents/abc/transcript.jsonl",
            },
        )
        data = self.assert_fires(proc, contains="gitleaks skill offers a redacted local secret preflight")
        ctx = data["hookSpecificOutput"]["additionalContext"]
        self.assertNotIn("MAIN-LOOP ORCHESTRATOR", ctx)

    def test_long_run_still_nags_subagent(self):
        """The asymmetry: unlike the deploy shape, a subagent running a
        long-lived command IS the bug, so it gets the full loud warning
        regardless of agent_id -- this is the one branch that can catch
        the delegated-long-run failure mode in the act."""
        proc = self.run_hook_json(
            self.HOOK, {"tool_input": {"command": "pytest -q"}, "agent_id": "agent-123"}
        )
        self.assert_fires(proc, contains="LONG-LIVED RUN")

    # -- fail-open / robustness (fail-LOUD-but-never-crash contract) ------
    def test_fail_open_on_true_parse_failures(self):
        """Per the module's own stated contract, a JSON parse failure is
        NOT silenced -- it prints a visible 'shape detection did not run'
        notice, but must still exit 0 (never wedge the session)."""
        for label, stdin_text in [
            ("empty stdin", ""),
            ("truncated json", "{not valid json"),
        ]:
            with self.subTest(case=label):
                proc = self.run_hook(self.HOOK, stdin_text)
                self.assert_fires(proc, contains="could not parse this tool call's payload")

    def test_silent_on_valid_but_keyless_payloads(self):
        """A syntactically valid JSON *dict* with missing/falsy expected
        keys must stay silent -- this is NOT a parse failure, so it takes
        the normal no-match path, not the loud parse-failure path."""
        safe_payloads = [
            {},  # no tool_input key at all
            {"tool_name": "Bash"},  # missing tool_input
            {"tool_input": None},
            {"tool_input": []},
            {"tool_input": {}},
            {"tool_input": 0},
            {"tool_input": False},
            {"tool_input": ""},
            {"tool_input": {"command": None}},
            {"tool_input": {"command": ""}},
        ]
        for payload in safe_payloads:
            with self.subTest(payload=payload):
                proc = self.run_hook_json(self.HOOK, payload)
                self.assert_silent(proc, f"payload={payload!r}")

    def test_nondict_top_level_payload_fails_open(self):
        """FIXED CONTRACT: fleet-delegation-guard.py now guards with
        `isinstance(payload, dict)` before touching `payload.get(...)`. A
        syntactically valid JSON payload whose TOP LEVEL is not a dict --
        e.g. the bare JSON array below -- routes into the same "shape
        detection did NOT run" unchecked-call reminder that a JSON-parse
        failure already uses, and exits 0.

        HISTORY: this test was DISCOVERED WHILE BUILDING THIS SUITE, not
        injected by it, and originally caught a real crash: with no
        `isinstance(payload, dict)` guard (unlike skill-routing-guard.py and
        tool-routing-guard.py, which both checked this), `payload.get(...)`
        raised an uncaught AttributeError -- exit 1 with a traceback on
        stderr instead of exit 0. It was marked `@unittest.expectedFailure`
        so the bug stayed visible in `-v` output without breaking the suite.
        fleet-delegation-guard.py has since been hardened to close this, so
        the decorator is gone and the assertion now pins the fixed contract.
        """
        proc = self.run_hook(self.HOOK, "[]")
        data = self.assert_fires(
            proc,
            contains="shape detection did NOT run",
            msg="non-dict top-level payload should fail open with the unchecked-call reminder",
        )
        ctx = data["hookSpecificOutput"]["additionalContext"]
        self.assertIn("treat this as an unchecked call, not a cleared one", ctx)

    def test_truthy_nondict_tool_input_fails_open(self):
        """FIXED CONTRACT: the hook now also guards `isinstance(tool_input,
        dict)` and `isinstance(cmd, str)` before using either value. A dict
        payload whose `tool_input` is present, TRUTHY, and not itself a
        dict -- which used to defeat the `payload.get("tool_input") or {}`
        falsy-fallback trick -- and a payload whose `command` is a
        non-string, non-falsy value both now route into the same
        unchecked-call reminder instead of crashing, and both exit 0.

        HISTORY: same root cause as test_nondict_top_level_payload_fails_open,
        different entry point -- also discovered while building this suite
        and originally marked `@unittest.expectedFailure` for the same
        reason. Reproduced pre-fix:
            printf '{"tool_input": "oops"}' | python3 hooks/fleet-delegation-guard.py           # exit 1
            printf '{"tool_input": {"command": 123}}' | python3 hooks/fleet-delegation-guard.py # exit 1
        """
        cases = [
            ("truthy non-dict tool_input", {"tool_input": "oops, not a dict"}),
            ("non-string command", {"tool_input": {"command": 123}}),
        ]
        for label, payload in cases:
            with self.subTest(case=label):
                proc = self.run_hook_json(self.HOOK, payload)
                data = self.assert_fires(
                    proc,
                    contains="shape detection did NOT run",
                    msg=f"{label} should fail open with the unchecked-call reminder",
                )
                ctx = data["hookSpecificOutput"]["additionalContext"]
                self.assertIn("treat this as an unchecked call, not a cleared one", ctx)


# =============================================================================
# 3. skill-routing-guard.py -- UserPromptSubmit
# =============================================================================
class TestSkillRoutingGuard(IsolatedHookTestCase):
    HOOK = "skill_routing_guard"
    HEADER = "skill-routing-guard (UserPromptSubmit hook, non-blocking reminder-only"

    # -- silent (negative control): ordinary code discussion ---------------
    def test_silent_on_ordinary_code_discussion(self):
        proc = self.run_hook_json(
            self.HOOK, {"prompt": "fix the csv parser in ingest.py, it throws on blank lines"}
        )
        self.assert_silent(proc)

    def test_silent_on_totally_unrelated_prompt(self):
        proc = self.run_hook_json(self.HOOK, {"prompt": "what time zone is Bangalore in?"})
        self.assert_silent(proc)

    # -- category: tabular-analysis -----------------------------------------
    def test_fires_tabular_analysis(self):
        proc = self.run_hook_json(
            self.HOOK, {"prompt": "analyze sales_data.csv and summarize the totals"}
        )
        data = self.assert_fires(proc, contains=self.HEADER)
        self.assertIn("duckdb skill", data["hookSpecificOutput"]["additionalContext"])

    def test_silent_tabular_analysis_missing_file_object(self):
        """Negative control: intent verb present, no .csv/.tsv/.parquet
        object -- gate 2 fails, must stay silent."""
        proc = self.run_hook_json(
            self.HOOK, {"prompt": "please analyze this quarter's numbers for me"}
        )
        self.assert_silent(proc)

    def test_silent_tabular_analysis_suppressed_by_code_adjacency(self):
        """Negative control: both gates satisfied, but the CODE_ADJACENT
        suppressor (a src/ path here) vetoes it -- this is really a prompt
        about existing code, not a request to analyze a data file."""
        proc = self.run_hook_json(
            self.HOOK,
            {"prompt": "analyze sales_data.csv parsing, see src/ingest.py def load_csv"},
        )
        self.assert_silent(proc)

    # -- category: doc-extract -----------------------------------------------
    def test_fires_doc_extract(self):
        proc = self.run_hook_json(
            self.HOOK, {"prompt": "extract the text from report.docx please"}
        )
        data = self.assert_fires(proc, contains=self.HEADER)
        self.assertIn("markitdown skill", data["hookSpecificOutput"]["additionalContext"])

    def test_silent_doc_extract_missing_file_object(self):
        proc = self.run_hook_json(
            self.HOOK, {"prompt": "please extract the key insight from this discussion"}
        )
        self.assert_silent(proc)

    def test_silent_doc_extract_excludes_pdf(self):
        """.pdf is deliberately excluded (owned by a dedicated pdf skill)
        -- this category must never fire for it even with the right verb."""
        proc = self.run_hook_json(self.HOOK, {"prompt": "extract the text from report.pdf"})
        self.assert_silent(proc)

    # -- category: share-preflight --------------------------------------------
    def test_fires_share_preflight(self):
        proc = self.run_hook_json(
            self.HOOK, {"prompt": "can you export this deck and share it with the client"}
        )
        data = self.assert_fires(proc, contains=self.HEADER)
        self.assertIn("presidio skill", data["hookSpecificOutput"]["additionalContext"])

    def test_silent_share_preflight_missing_audience_or_pii_token(self):
        proc = self.run_hook_json(self.HOOK, {"prompt": "can you export this deck to a new folder"})
        self.assert_silent(proc)

    # -- category: design-ship-check -------------------------------------------
    def test_fires_design_ship_check(self):
        proc = self.run_hook_json(self.HOOK, {"prompt": "is this landing page ready to ship?"})
        data = self.assert_fires(proc, contains=self.HEADER)
        self.assertIn("design-judge skill", data["hookSpecificOutput"]["additionalContext"])

    def test_silent_design_ship_check_missing_design_noun(self):
        proc = self.run_hook_json(self.HOOK, {"prompt": "is this plan ready to ship?"})
        self.assert_silent(proc)

    # -- category: register-exec -------------------------------------------------
    def test_fires_register_exec(self):
        proc = self.run_hook_json(self.HOOK, {"prompt": "draft an update for the CEO on this"})
        data = self.assert_fires(proc, contains=self.HEADER)
        self.assertIn(
            "fable-judgment section 3 register rule",
            data["hookSpecificOutput"]["additionalContext"],
        )

    def test_silent_register_exec_missing_distant_reader(self):
        proc = self.run_hook_json(self.HOOK, {"prompt": "draft an update for the team on this"})
        self.assert_silent(proc)

    # -- category: library-docs -------------------------------------------------
    def test_fires_library_docs(self):
        proc = self.run_hook_json(
            self.HOOK, {"prompt": "check the react docs for the new useEffect syntax"}
        )
        data = self.assert_fires(proc, contains=self.HEADER)
        self.assertIn("context7 MCP", data["hookSpecificOutput"]["additionalContext"])

    def test_silent_library_docs_missing_library_object(self):
        proc = self.run_hook_json(self.HOOK, {"prompt": "check the docs for this"})
        self.assert_silent(proc)

    # -- category: graphify-first (cwd-gated) -------------------------------------
    def test_fires_graphify_first_when_index_present(self):
        repo = self.tmp_root / "indexed_repo"
        (repo / "graphify-out").mkdir(parents=True)
        proc = self.run_hook_json(
            self.HOOK,
            {"prompt": "where is the auth handled in this codebase?", "cwd": str(repo)},
        )
        data = self.assert_fires(proc, contains=self.HEADER)
        self.assertIn(
            "graphify-out/ index", data["hookSpecificOutput"]["additionalContext"]
        )

    def test_silent_graphify_first_when_index_absent(self):
        """Negative control: identical prompt, cwd has no graphify-out/ --
        structurally silent per the cwd_test gate."""
        repo = self.tmp_root / "unindexed_repo"
        repo.mkdir()
        proc = self.run_hook_json(
            self.HOOK,
            {"prompt": "where is the auth handled in this codebase?", "cwd": str(repo)},
        )
        self.assert_silent(proc)

    # -- category: incident-capture (intent-only, no object gate) --------------
    def test_fires_incident_capture(self):
        proc = self.run_hook_json(
            self.HOOK, {"prompt": "this is worth remembering, turn this into a lesson"}
        )
        data = self.assert_fires(proc, contains=self.HEADER)
        self.assertIn("incident-miner skill", data["hookSpecificOutput"]["additionalContext"])
        # negative control for this category is test_silent_on_ordinary_code_discussion /
        # test_silent_on_totally_unrelated_prompt above -- incident-capture has no
        # separate object gate to violate, only the intent phrase itself.

    # -- multiple categories can co-fire -------------------------------------------
    def test_multiple_categories_fire_together(self):
        proc = self.run_hook_json(
            self.HOOK,
            {"prompt": "analyze sales_data.csv and draft an update for the CEO about it"},
        )
        data = self.assert_fires(proc)
        ctx = data["hookSpecificOutput"]["additionalContext"]
        self.assertIn("duckdb skill", ctx)
        self.assertIn("fable-judgment section 3 register rule", ctx)

    # -- fail-open / robustness --------------------------------------------------
    def test_fail_open_robustness(self):
        malformed_and_unexpected = [
            "",  # empty stdin
            "{}",  # valid but empty
            "{not valid json",  # malformed
            "[]",  # unexpected type: top-level list
            "null",  # unexpected type: top-level null
            "true",  # unexpected type: top-level bool
            "42",  # unexpected type: top-level number
            '"just a string"',  # unexpected type: top-level string
            '{"prompt": 12345}',  # unexpected type: prompt is not a string
            '{"prompt": null}',  # prompt explicitly null
            '{"prompt": "csv analysis", "cwd": 12345}',  # cwd not a string
            '{"foo": "bar"}',  # valid dict, missing every expected key
        ]
        for stdin_text in malformed_and_unexpected:
            with self.subTest(stdin=stdin_text):
                proc = self.run_hook(self.HOOK, stdin_text)
                self.assert_silent(proc, f"stdin={stdin_text!r}")


# =============================================================================
# 4. tool-routing-guard.py -- PreToolUse / WebFetch|WebSearch
# =============================================================================
class TestToolRoutingGuard(IsolatedHookTestCase):
    HOOK = "tool_routing_guard"
    DOCS_URL = "https://docs.python.org/3/library/os.html"
    NON_DOCS_URL = "https://example.com/blog/post"

    def _state_dir(self, name):
        d = self.tmp_root / "trg-state" / name
        d.mkdir(parents=True)
        return str(d)

    # -- silent (negative control): a single non-docs WebFetch -------------
    def test_silent_on_single_non_docs_fetch(self):
        state = self._state_dir("silent")
        proc = self.run_hook_json(
            self.HOOK,
            {"tool_name": "WebFetch", "tool_input": {"url": self.NON_DOCS_URL}, "session_id": "s-silent"},
            env_overrides={"CLAUDE_TOOL_ROUTING_STATE_DIR": state},
        )
        self.assert_silent(proc)

    # -- deny-then-allow contract, end to end -------------------------------
    def test_docs_url_deny_then_retry_allowed(self):
        state = self._state_dir("deny-allow")
        env = {"CLAUDE_TOOL_ROUTING_STATE_DIR": state}
        payload = {
            "tool_name": "WebFetch",
            "tool_input": {"url": self.DOCS_URL},
            "session_id": "s-deny-allow",
        }

        first = self.run_hook_json(self.HOOK, payload, env_overrides=env)
        data = self.assert_fires(first)
        hso = data["hookSpecificOutput"]
        self.assertEqual(hso.get("permissionDecision"), "deny")
        self.assertIn("DENIED this WebFetch", hso.get("permissionDecisionReason", ""))

        # Immediate identical retry, same session, same state dir -> passes.
        second = self.run_hook_json(self.HOOK, payload, env_overrides=env)
        self.assert_silent(second, "retry of the same docs URL in the same session must be allowed")

    def test_docs_url_deny_is_per_session(self):
        """A DIFFERENT session_id must get its own fresh deny -- the marker
        is keyed on session, not globally."""
        state = self._state_dir("per-session")
        env = {"CLAUDE_TOOL_ROUTING_STATE_DIR": state}
        payload_a = {
            "tool_name": "WebFetch",
            "tool_input": {"url": self.DOCS_URL},
            "session_id": "session-A",
        }
        payload_b = {**payload_a, "session_id": "session-B"}

        self.run_hook_json(self.HOOK, payload_a, env_overrides=env)  # burn session A's deny
        second_session_first_call = self.run_hook_json(self.HOOK, payload_b, env_overrides=env)
        data = self.assert_fires(second_session_first_call)
        self.assertEqual(data["hookSpecificOutput"].get("permissionDecision"), "deny")

    # -- kill switch ------------------------------------------------------------
    def test_kill_switch_downgrades_deny_to_reminder(self):
        state = self._state_dir("kill-switch")
        env = {"CLAUDE_TOOL_ROUTING_STATE_DIR": state, "CLAUDE_TOOL_ROUTING_ENFORCE": "0"}
        payload = {
            "tool_name": "WebFetch",
            "tool_input": {"url": self.DOCS_URL},
            "session_id": "s-killswitch",
        }
        proc = self.run_hook_json(self.HOOK, payload, env_overrides=env)
        data = self.assert_fires(proc, contains="this WebFetch targets a documentation URL")
        hso = data["hookSpecificOutput"]
        self.assertNotIn("permissionDecision", hso)
        self.assertIsNone(hso.get("permissionDecision"))

    # -- websearch-alternatives, once per session ----------------------------
    def test_websearch_reminder_fires_once_then_silent(self):
        state = self._state_dir("websearch")
        env = {"CLAUDE_TOOL_ROUTING_STATE_DIR": state}
        payload = {"tool_name": "WebSearch", "tool_input": {"query": "foo"}, "session_id": "s-ws"}

        first = self.run_hook_json(self.HOOK, payload, env_overrides=env)
        self.assert_fires(first, contains="WebSearch call detected")

        second = self.run_hook_json(self.HOOK, payload, env_overrides=env)
        self.assert_silent(second, "websearch-alternatives fires at most once per session")

    # -- page-by-page-firecrawl on the 3rd+ WebFetch --------------------------
    def test_page_by_page_fires_on_third_fetch(self):
        state = self._state_dir("page-by-page")
        env = {"CLAUDE_TOOL_ROUTING_STATE_DIR": state}
        session_id = "s-pbp"

        def fetch(n):
            return self.run_hook_json(
                self.HOOK,
                {
                    "tool_name": "WebFetch",
                    "tool_input": {"url": f"https://example.com/page-{n}"},
                    "session_id": session_id,
                },
                env_overrides=env,
            )

        self.assert_silent(fetch(1), "1st non-docs fetch: no nudge yet")
        self.assert_silent(fetch(2), "2nd non-docs fetch: still no nudge")
        third = fetch(3)
        self.assert_fires(third, contains="already made 2+ WebFetch calls")

    # -- fail-open / robustness -----------------------------------------------
    def test_fail_open_robustness(self):
        malformed_and_unexpected = [
            "",
            "{}",
            "{not valid json",
            "[]",
            "null",
            "42",
            '"a string"',
            '{"tool_name": "WebFetch"}',  # missing tool_input entirely
            '{"tool_name": "WebFetch", "tool_input": 123}',  # tool_input not a dict
            '{"tool_name": "WebFetch", "tool_input": {"url": 123}}',  # url not a string
            '{"tool_name": "SomethingElse", "tool_input": {}}',  # unrecognized tool_name
            '{"tool_name": null}',
        ]
        # Each case gets its OWN fresh state dir: several of these payloads
        # are shaped enough to count as a real "WebFetch" call to the
        # per-session webcalls counter, and this hook's page-by-page-firecrawl
        # nudge is deliberately supposed to fire on the 3rd+ one seen in a
        # session (see test_page_by_page_fires_on_third_fetch) -- sharing one
        # state dir across this whole list would make cases 9-12 trip that
        # real nudge and this would stop being a fail-open test of each case
        # in isolation.
        for i, stdin_text in enumerate(malformed_and_unexpected):
            with self.subTest(stdin=stdin_text):
                env = {"CLAUDE_TOOL_ROUTING_STATE_DIR": self._state_dir(f"robustness-{i}")}
                proc = self.run_hook(self.HOOK, stdin_text, env_overrides=env)
                self.assert_silent(proc, f"stdin={stdin_text!r}")

    def test_never_writes_outside_state_dir(self):
        """Assert-by-construction: after a handful of calls, only files
        under our own temp state dir exist -- nothing touched the
        hardcoded default (/tmp/claude-tool-routing-guard)."""
        state = self._state_dir("write-scope")
        env = {"CLAUDE_TOOL_ROUTING_STATE_DIR": state}
        self.run_hook_json(
            self.HOOK,
            {"tool_name": "WebSearch", "tool_input": {}, "session_id": "s-scope"},
            env_overrides=env,
        )
        produced = list(Path(state).iterdir())
        self.assertTrue(produced, "expected at least one marker file in our own state dir")
        self.assertFalse(
            os.path.isdir("/tmp/claude-tool-routing-guard") and
            any(Path("/tmp/claude-tool-routing-guard").glob("s-scope.*")),
            "hook must not have written into the real default state dir",
        )


# =============================================================================
# 5. retrieval-honesty-guard.py -- Stop
# =============================================================================
class TestRetrievalHonestyGuard(IsolatedHookTestCase):
    HOOK = "retrieval_honesty_guard"

    def _write_transcript(self, name, entries):
        path = self.tmp_root / f"{name}.jsonl"
        with open(path, "w", encoding="utf-8") as fh:
            for entry in entries:
                fh.write(json.dumps(entry) + "\n")
        return str(path)

    @staticmethod
    def _user_turn(text):
        return {"type": "user", "message": {"content": text}}

    @staticmethod
    def _assistant_text(text):
        return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}

    @staticmethod
    def _assistant_tool_use(name, tool_input=None):
        return {
            "type": "assistant",
            "message": {"content": [{"type": "tool_use", "name": name, "input": tool_input or {}}]},
        }

    # -- (a) tell, NO retrieval tool call this turn -> BLOCK -------------------
    def test_tell_without_retrieval_blocks(self):
        tpath = self._write_transcript(
            "a_tell_no_retrieval",
            [
                self._user_turn("Is the new Foo SDK v3 out yet?"),
                self._assistant_text(
                    "I'm past my cutoff on that, so I can't verify whether Foo SDK v3 shipped."
                ),
            ],
        )
        proc = self.run_hook_json(self.HOOK, {"transcript_path": tpath, "session_id": "sess-a"})
        self.assert_exit0(proc)  # blocking is via JSON body, never a nonzero exit
        data = json.loads(proc.stdout.strip())
        self.assertEqual(data.get("decision"), "block")
        self.assertIn("motivated-non-retrieval failure mode", data.get("reason", ""))

    # -- (b) same tell, WITH a retrieval tool call this turn -> ALLOW ------------
    def test_tell_with_retrieval_allows(self):
        tpath = self._write_transcript(
            "b_tell_with_retrieval",
            [
                self._user_turn("Is the new Foo SDK v3 out yet?"),
                self._assistant_tool_use(
                    "mcp__tavily__tavily_search", {"query": "Foo SDK v3 release"}
                ),
                self._assistant_text(
                    "I'm past my cutoff on that, so I can't verify it from memory, "
                    "but tavily confirms v3 shipped."
                ),
            ],
        )
        proc = self.run_hook_json(self.HOOK, {"transcript_path": tpath, "session_id": "sess-b"})
        self.assert_silent(proc)

    def test_tell_with_dispatched_subagent_allows(self):
        """A dispatched research subagent (Agent/Task/SendMessage tool use)
        counts as retrieval too, independent of the direct-MCP-call path
        exercised above."""
        tpath = self._write_transcript(
            "b2_tell_with_subagent",
            [
                self._user_turn("Did Foo Corp ship the v3 SDK?"),
                self._assistant_tool_use("Task", {"description": "research Foo SDK v3"}),
                self._assistant_text("I can't verify this without checking, but the agent found it shipped."),
            ],
        )
        proc = self.run_hook_json(self.HOOK, {"transcript_path": tpath, "session_id": "sess-b2"})
        self.assert_silent(proc)

    # -- (c) stop_hook_active: true -> never block (no loops) -------------------
    def test_stop_hook_active_never_blocks(self):
        tpath = self._write_transcript(
            "c_stop_hook_active",
            [
                self._user_turn("Is the new Foo SDK v3 out yet?"),
                self._assistant_text("I'm past my cutoff on that, so I can't verify it."),
            ],
        )
        proc = self.run_hook_json(
            self.HOOK,
            {"transcript_path": tpath, "session_id": "sess-c", "stop_hook_active": True},
        )
        self.assert_silent(proc)

    # -- (d) missing / nonexistent transcript path -> exit 0 --------------------
    def test_missing_transcript_path_key_exits_silently(self):
        proc = self.run_hook_json(self.HOOK, {"session_id": "sess-d1"})
        self.assert_silent(proc)

    def test_nonexistent_transcript_path_exits_silently(self):
        proc = self.run_hook_json(
            self.HOOK,
            {"transcript_path": str(self.tmp_root / "does-not-exist.jsonl"), "session_id": "sess-d2"},
        )
        self.assert_silent(proc)

    # -- negative control: no tell phrase present at all -------------------------
    def test_no_tell_phrase_present_silent_even_without_retrieval(self):
        tpath = self._write_transcript(
            "no_tell",
            [
                self._user_turn("What's 2 + 2?"),
                self._assistant_text("4."),
            ],
        )
        proc = self.run_hook_json(self.HOOK, {"transcript_path": tpath, "session_id": "sess-e"})
        self.assert_silent(proc)

    def test_alternate_tell_phrasing_without_retrieval_blocks(self):
        """A different TELLS regex branch ('as of my last training') for
        extra confidence the pattern list, not just one phrase, is wired."""
        tpath = self._write_transcript(
            "alt_tell",
            [
                self._user_turn("What's the latest pricing for this API?"),
                self._assistant_text(
                    "As of my last training update, I don't have current pricing for this."
                ),
            ],
        )
        proc = self.run_hook_json(self.HOOK, {"transcript_path": tpath, "session_id": "sess-f"})
        data = json.loads(proc.stdout.strip())
        self.assertEqual(data.get("decision"), "block")

    # -- fail-open / robustness ---------------------------------------------------
    def test_fail_open_robustness(self):
        malformed_and_unexpected = [
            "",  # empty stdin
            "{}",
            "{not valid json",
            "[]",
            "null",
            "true",
            "42",
            '"a string"',
            '{"transcript_path": 123}',  # unexpected type
            '{"transcript_path": []}',  # unexpected type
            '{"transcript_path": true}',  # unexpected type
            '{"session_id": 123, "transcript_path": null}',
        ]
        for stdin_text in malformed_and_unexpected:
            with self.subTest(stdin=stdin_text):
                proc = self.run_hook(self.HOOK, stdin_text)
                self.assert_silent(proc, f"stdin={stdin_text!r}")

    def test_marker_file_written_only_inside_tmpdir(self):
        """Assert-by-construction: the once-per-(session,response) marker
        this hook writes (tempfile.gettempdir() / 'claude-retrieval-guard-*')
        lands inside OUR TMPDIR override, never the real system temp dir."""
        tpath = self._write_transcript(
            "marker_scope",
            [
                self._user_turn("Is the new Foo SDK v3 out yet?"),
                self._assistant_text("I can't verify this without looking it up."),
            ],
        )
        proc = self.run_hook_json(self.HOOK, {"transcript_path": tpath, "session_id": "sess-marker"})
        data = json.loads(proc.stdout.strip())
        self.assertEqual(data.get("decision"), "block")
        markers = list(self.tmp.glob("claude-retrieval-guard-*"))
        self.assertTrue(markers, f"expected a marker file under {self.tmp}, found none")


if __name__ == "__main__":
    unittest.main()
