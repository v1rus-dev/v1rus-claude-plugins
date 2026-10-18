"""Tests for scripts/check-plugins.py checks (description, agent refs). Run: python3 -m unittest discover -s tests"""
import importlib.util
import json
import pathlib
import shutil
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "scripts/check-plugins.py"


def load():
    spec = importlib.util.spec_from_file_location("check_plugins", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class CheckPluginsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.m = load()
        self.m.ROOT = self.tmp
        self.m.PLUGINS = self.tmp / "plugins"
        self.plugins = {}

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def plugin(self, name, deps=(), agents=(), md=None):
        p = self.tmp / "plugins" / name
        (p / "agents").mkdir(parents=True)
        for a in agents:
            (p / "agents" / (a + ".md")).write_text("---\nname: %s\ndescription: x\n---\nbody\n" % a)
        if md:
            (p / "README.md").write_text(md)
        (p / ".claude-plugin").mkdir()
        (p / ".claude-plugin/plugin.json").write_text(json.dumps({"name": name, "version": "1.0.0", "dependencies": list(deps)}))
        self.plugins[name] = {"name": name, "dependencies": list(deps)}

    def test_empty_description_detected(self):
        e = self.m.description_empty
        self.assertTrue(e("name: a\ndescription:"))
        self.assertTrue(e('name: a\ndescription: ""'))
        self.assertTrue(e("name: a\ndescription: |-\nmodel: x"))
        self.assertFalse(e("name: a\ndescription: Does things"))
        self.assertFalse(e("name: a\ndescription: |-\n  Does things\nmodel: x"))

    def test_empty_agent_description_is_error(self):
        self.plugin("v1rus-a")
        (self.tmp / "plugins/v1rus-a/agents/bad.md").write_text("---\nname: bad\ndescription:\n---\nbody\n")
        self.m.check_plugin(self.tmp / "plugins/v1rus-a", {})
        self.assertTrue(any("description is empty" in e for e in self.m.errors), self.m.errors)

    def test_undefined_agent_warns_unless_optional(self):
        self.plugin("v1rus-core", agents=["code-reviewer"], md="Use `code-reviewer`.\n")
        self.plugin("v1rus-x", deps=["v1rus-core"], md="Use `code-reviewer` and `perf-expert`.\nAlso `ghost-expert` if installed.\n")
        self.m.check_agent_refs(self.plugins)
        self.assertEqual(len(self.m.warnings), 1, self.m.warnings)
        self.assertIn("perf-expert", self.m.warnings[0])

    def test_dependency_chain_is_transitive(self):
        self.plugin("c")
        self.plugin("b", deps=["c"])
        self.plugin("a", deps=["b"])
        self.assertEqual(self.m.dependency_chain("a", self.plugins), {"a", "b", "c"})


if __name__ == "__main__":
    unittest.main()
