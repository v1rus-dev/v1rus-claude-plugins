"""Stdin-driven tests for the rules engine. Run: python3 -m unittest discover -s tests"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ENGINE = pathlib.Path(__file__).resolve().parent.parent / "plugins/v1rus-core/hooks/v1rus_rules.py"


class EngineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.root = self.tmp / "plug"
        (self.root / ".claude-plugin").mkdir(parents=True)
        (self.root / "rules").mkdir()
        (self.root / ".claude-plugin/plugin.json").write_text('{"name":"v1rus-x"}')
        (self.root / "charter.md").write_text("---\nx: y\n---\nBe terse.\n")
        (self.root / "rules/kt.md").write_text('---\npaths:\n  - "**/*.{kt,kts}"\n  - "src/api/*.java"\n---\nKotlin rule\n')
        (self.root / "rules/inline.md").write_text('---\npaths: "*.md", docs/**\n---\nDocs rule\n')
        (self.root / "rules/always.md").write_text("no frontmatter, never injected by path engine\n")
        self.env = dict(os.environ, CLAUDE_PLUGIN_ROOT=str(self.root), CLAUDE_PLUGIN_DATA=str(self.tmp / "data"))
        self.env.pop("CLAUDE_PROJECT_DIR", None)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_engine(self, mode, event, raw=None):
        p = subprocess.run([sys.executable, str(ENGINE), mode], input=raw if raw is not None else json.dumps(event),
                           capture_output=True, text=True, env=self.env)
        self.assertEqual(p.returncode, 0)
        return json.loads(p.stdout)["hookSpecificOutput"] if p.stdout else None

    def edit(self, path, sid="s1", tool="Edit"):
        return self.run_engine("path-rules", {"session_id": sid, "cwd": "/proj", "tool_name": tool,
                                              "tool_input": {"file_path": path}})

    def test_charter(self):
        out = self.run_engine("session-start", {"session_id": "s1", "source": "startup"})
        self.assertEqual(out["hookEventName"], "SessionStart")
        self.assertIn("Be terse.", out["additionalContext"])
        self.assertNotIn("x: y", out["additionalContext"])

    def test_match_once_per_session(self):
        out = self.edit("/proj/app/src/Main.kt")
        self.assertEqual(out["hookEventName"], "PreToolUse")
        self.assertIn("Kotlin rule", out["additionalContext"])
        self.assertIsNone(self.edit("/proj/app/Other.kt"))
        self.assertIn("Kotlin rule", self.edit("/proj/Other.kt", sid="s2")["additionalContext"])

    def test_reset_on_startup_not_on_resume(self):
        self.edit("/proj/A.kt")
        self.run_engine("session-start", {"session_id": "s1", "source": "resume"})
        self.assertIsNone(self.edit("/proj/B.kt"))
        self.run_engine("session-start", {"session_id": "s1", "source": "compact"})
        self.assertIsNotNone(self.edit("/proj/B.kt"))

    def test_globs(self):
        self.assertIsNotNone(self.edit("/proj/src/api/A.java", sid="a"))
        self.assertIsNone(self.edit("/proj/src/api/sub/A.java", sid="b"))
        self.assertIsNone(self.edit("/proj/main.go", sid="c"))
        self.assertIn("Docs rule", self.edit("/proj/README.md", sid="d")["additionalContext"])
        self.assertIsNone(self.edit("/proj/sub/README.md", sid="e"))
        self.assertIsNotNone(self.edit("/proj/docs/a/b.txt", sid="f"))

    def test_ignored_tools_and_garbage(self):
        self.assertIsNone(self.edit("/proj/A.kt", tool="Read"))
        self.assertIsNone(self.run_engine("path-rules", None, raw="not json"))
        self.assertIsNone(self.run_engine("bogus", {}))

    def test_fail_open_without_root_files(self):
        shutil.rmtree(self.root / "rules")
        os.remove(self.root / "charter.md")
        self.assertIsNone(self.edit("/proj/A.kt"))
        self.assertIsNone(self.run_engine("session-start", {"session_id": "s1", "source": "startup"}))

    def test_subagent_has_own_dedup_state(self):
        def ev(agent, sid="s1"):
            e = {"session_id": sid, "cwd": "/proj", "tool_name": "Edit", "tool_input": {"file_path": "/proj/A.kt"}}
            if agent:
                e["agent_id"] = agent
            return self.run_engine("path-rules", e)
        self.assertIsNotNone(ev(None))
        self.assertIsNone(ev(None))
        self.assertIsNotNone(ev("a1"))  # subagent gets the rule again
        self.assertIsNone(ev("a1"))
        self.assertIsNotNone(ev("a2"))
        self.run_engine("session-start", {"session_id": "s1", "source": "startup"})
        self.assertIsNotNone(ev("a1"))  # startup resets subagent state too

    def test_empty_session_id_no_dedup(self):
        self.assertIsNotNone(self.edit("/proj/A.kt", sid=""))
        self.assertIsNotNone(self.edit("/proj/A.kt", sid=""))

    def test_outside_project_root_no_match(self):
        self.assertIsNone(self.edit("/other/place/A.kt"))
        self.assertIsNotNone(self.edit("/proj/A.kt"))

    def test_unreadable_rule_does_not_abort_others(self):
        (self.root / "rules/aaa.md").write_bytes(b"---\npaths: '*.kt'\n---\n\xff\xfe bad\n")
        out = self.edit("/proj/A.kt")
        self.assertIn("Kotlin rule", out["additionalContext"])

    def test_expand_braces(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("eng", ENGINE)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        self.assertEqual(m.expand_braces("{a,b}/x.{c,d}"), ["a/x.c", "a/x.d", "b/x.c", "b/x.d"])
        self.assertEqual(m.expand_braces("{lit}/x.{c,d}"), ["{lit}/x.c", "{lit}/x.d"])
        self.assertEqual(m.expand_braces("{a,b}/{lit}"), ["a/{lit}", "b/{lit}"])
        self.assertEqual(m.expand_braces("{a,{b,c}}"), ["a", "b", "c"])


if __name__ == "__main__":
    unittest.main()
