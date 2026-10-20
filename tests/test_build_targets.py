"""Tests for scripts/build-targets.py and scripts/adapters. Run: python3 -m unittest discover -s tests"""
import importlib.util
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts/build-targets.py"
ADAPTER = ROOT / "scripts/adapters/codex_hook_adapter.py"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def source_hash(bt):
    return bt.tree_hash(ROOT / "plugins") + bt.tree_hash(ROOT / ".claude-plugin")


class BuildTargetsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bt = load(SCRIPT, "build_targets")
        cls.tmp = pathlib.Path(tempfile.mkdtemp())
        cls.before = source_hash(cls.bt)
        cls.out = cls.tmp / "out"
        cls.second = cls.tmp / "out2"
        for out in (cls.out, cls.second):
            rc = cls.bt.main(["--out", str(out)])
            assert rc == 0, "build failed"
        cls.oc, cls.cx = cls.out / "opencode", cls.out / "codex"

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_sources_untouched(self):
        self.assertEqual(self.before, source_hash(self.bt))

    def test_deterministic(self):
        self.assertEqual(self.bt.tree_hash(self.out), self.bt.tree_hash(self.second))

    def test_check_mode_passes(self):
        self.assertEqual(self.bt.main(["--check"]), 0)

    def test_no_plugin_root_token_left(self):
        for f in self.out.rglob("*"):
            if f.is_file() and f.suffix != ".py":
                self.assertNotIn(b"${CLAUDE_PLUGIN_ROOT}", f.read_bytes(), str(f))

    def test_json_and_toml_valid(self):
        n = 0
        for f in self.out.rglob("*.json"):
            json.loads(f.read_text(encoding="utf-8"))
            n += 1
        for f in self.out.rglob("*.toml"):
            tomllib.loads(f.read_text(encoding="utf-8"))
            n += 1
        self.assertGreater(n, 40)

    def test_skill_collision_is_an_error(self):
        plugins = self.bt.load_plugins()
        first = next(iter(plugins.values()))
        victim = next(p for p in plugins.values() if p is not first and (p["dir"] / "skills").is_dir())
        skill = next((first["dir"] / "skills").iterdir()).name
        tmp = pathlib.Path(tempfile.mkdtemp())
        try:
            shutil.copytree(victim["dir"], tmp / victim["name"])
            (tmp / victim["name"] / "skills" / skill).mkdir(parents=True)
            (tmp / victim["name"] / "skills" / skill / "SKILL.md").write_text("---\nname: %s\ndescription: d\n---\n" % skill)
            old = self.bt.PLUGINS
            self.bt.PLUGINS = tmp
            try:
                plugins[victim["name"]]["dir"] = tmp / victim["name"]
                with self.assertRaises(self.bt.BuildError) as ctx:
                    self.bt.collect_names(plugins)
                self.assertIn(skill, str(ctx.exception))
            finally:
                self.bt.PLUGINS = old
        finally:
            shutil.rmtree(tmp)

    def test_opencode_agent_translation(self):
        text = (self.oc / "agents/code-reviewer.md").read_text(encoding="utf-8")
        fm = self.bt.parse_fm(self.bt.split_fm(text)[0])
        self.assertEqual(fm["mode"], "subagent")
        self.assertTrue(fm["description"])
        for dropped in ("model:", "color:", "memory:", "maxTurns:", "tools:", "skills:"):
            self.assertNotIn("\n" + dropped, text.split("\n---\n", 1)[0])
        self.assertIn('"*": deny', text)
        self.assertIn("  read: allow", text)
        self.assertNotIn("  edit: allow", text)

    def test_colliding_agents_are_renamed(self):
        self.assertTrue((self.oc / "agents/test-runner-kmp.md").exists())
        self.assertFalse((self.oc / "agents/test-runner.md").exists())
        self.assertTrue((self.cx / "agents/test-runner-kmp.toml").exists())

    def test_codex_agent_toml(self):
        doc = tomllib.loads((self.cx / "agents/go-engineer.toml").read_text(encoding="utf-8"))
        self.assertEqual(doc["name"], "go-engineer")
        self.assertTrue(doc["description"] and doc["developer_instructions"])
        self.assertNotIn("model", doc)

    def test_codex_marketplace_and_manifests(self):
        market = json.loads((self.cx / ".agents/plugins/marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual(len(market["plugins"]), 12)
        for entry in market["plugins"]:
            self.assertEqual(entry["policy"]["installation"], "AVAILABLE")
            self.assertTrue(entry["category"])
            pdir = self.cx / entry["source"]["path"]
            manifest = json.loads((pdir / "plugin.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["name"], entry["name"])
            self.assertTrue(manifest["$schema"].startswith("https://agent-plugins.org/schemas/1.0.0/"))
            self.assertTrue((pdir / "skills").is_dir())

    def test_codex_bundle_contains_dependencies(self):
        kmp = self.cx / "plugins/v1rus-kmp"
        self.assertTrue((kmp / "skills/v1rus-workflow/SKILL.md").exists())      # core
        self.assertTrue((kmp / "rules/kotlin-style.md").exists())               # kotlin
        self.assertTrue((kmp / "references/compose-rules.md").exists())         # compose
        self.assertTrue((kmp / "rules/commonmain.md").exists())                 # kmp itself

    def test_codex_hooks_point_to_existing_files(self):
        hooks = json.loads((self.cx / "plugins/v1rus-kotlin/hooks/hooks.json").read_text(encoding="utf-8"))
        cmds = [h["command"] for groups in hooks["hooks"].values() for g in groups for h in g["hooks"]]
        self.assertTrue(cmds)
        for cmd in cmds:
            for name in re.findall(r"[\w-]+\.py", cmd):
                self.assertTrue((self.cx / "plugins/v1rus-kotlin/hooks" / name).exists(), cmd)

    def test_opencode_layout(self):
        for p in ("plugins/v1rus.js", "v1rus/charter.md", "v1rus/v1rus-core/hooks/git-guard.py",
                  "v1rus/v1rus-kotlin/hooks/path-rules.py", "v1rus/v1rus-kotlin/rules/kotlin-style.md"):
            self.assertTrue((self.oc / p).exists(), p)

    def test_hook_scripts_are_byte_identical_copies(self):
        src = (ROOT / "plugins/v1rus-core/hooks/git-guard.py").read_bytes()
        self.assertEqual(src, (self.oc / "v1rus/v1rus-core/hooks/git-guard.py").read_bytes())
        self.assertEqual(src, (self.cx / "plugins/v1rus-core/hooks/git-guard.py").read_bytes())


class CodexAdapterTest(unittest.TestCase):
    def setUp(self):
        self.mod = load(ADAPTER, "codex_adapter")
        self.build = pathlib.Path(tempfile.mkdtemp())
        bt = load(SCRIPT, "build_targets2")
        self.assertEqual(bt.main(["--out", str(self.build)]), 0)
        self.hooks = self.build / "codex/plugins/v1rus-kotlin/hooks"

    def tearDown(self):
        shutil.rmtree(self.build)

    def run_adapter(self, script, event):
        return subprocess.run([sys.executable, str(self.hooks / "codex-adapter.py"), script],
                              input=json.dumps(event), capture_output=True, text=True)

    def test_patch_paths(self):
        patch = "*** Begin Patch\n*** Update File: src/A.kt\n@@\n-a\n+b\n*** Add File: src/B.kt\n+x\n*** End Patch"
        self.assertEqual(self.mod.extract_paths({"command": patch}), ["src/A.kt", "src/B.kt"])
        self.assertEqual(self.mod.extract_paths({"file_path": "x.kt"}), ["x.kt"])
        self.assertEqual(self.mod.extract_paths({"path": "y.kt"}), ["y.kt"])

    def test_normalize_apply_patch(self):
        out = self.mod.normalize({"tool_name": "apply_patch", "tool_input": {"command": "*** Update File: a.kt\n"}})
        self.assertEqual(out["tool_name"], "Edit")
        self.assertEqual(out["tool_input"]["file_path"], "a.kt")

    def test_secrets_guard_blocks_env_patch(self):
        r = self.run_adapter("secrets-guard.py", {"tool_name": "apply_patch", "session_id": "s",
                             "tool_input": {"command": "*** Add File: app/.env\n+K=V\n"}})
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("denied", r.stderr)

    def test_git_guard_blocks_sudo(self):
        r = self.run_adapter("git-guard.py", {"tool_name": "Bash", "tool_input": {"command": "sudo ls"}})
        self.assertEqual(r.returncode, 2, r.stderr)

    def test_path_rules_inject_for_patch_once_and_reset(self):
        env_data = self.build / "data"
        event = {"tool_name": "apply_patch", "session_id": "adapter-test", "hook_event_name": "PreToolUse",
                 "tool_input": {"command": "*** Update File: src/Foo.kt\n"}}
        import os
        env = dict(os.environ, CLAUDE_PLUGIN_DATA=str(env_data))

        def call(ev):
            return subprocess.run([sys.executable, str(self.hooks / "codex-adapter.py"), "path-rules.py"],
                                  input=json.dumps(ev), capture_output=True, text=True, env=env)
        first = call(event)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertIn("additionalContext", first.stdout)
        self.assertEqual(call(event).stdout.strip(), "")  # already injected this session
        call({"hook_event_name": "PreCompact", "session_id": "adapter-test"})
        self.assertIn("additionalContext", call(event).stdout)  # back after compaction


@unittest.skipUnless(shutil.which("node"), "node not installed")
class OpenCodePluginTest(unittest.TestCase):
    def test_plugin_blocks_and_injects(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        try:
            bt = load(SCRIPT, "build_targets3")
            self.assertEqual(bt.main(["--out", str(tmp)]), 0)
            harness = r"""
import plugin from %s
const hooks = {}, sys = []
await plugin.setup({ location: { directory: %s }, tool: { hook: async (n, f) => { hooks['tool.' + n] = f } },
  session: { hook: async (n, f) => { hooks['session.' + n] = f } } })
const res = {}
const tryCall = (k, ev) => { try { hooks['tool.execute.before'](ev); res[k] = 'ok' } catch (e) { res[k] = 'blocked: ' + e.message.slice(0, 40) } }
tryCall('sudo', { tool: 'shell', sessionID: 's1', input: { command: 'sudo ls' } })
tryCall('env', { tool: 'read', sessionID: 's1', input: { path: '/p/.env' } })
tryCall('ls', { tool: 'shell', sessionID: 's1', input: { command: 'ls' } })
tryCall('kt', { tool: 'write', sessionID: 's1', input: { path: '/p/src/A.kt' } })
const ev = { sessionID: 's1', system: [] }
hooks['session.context'](ev)
res.injected = ev.system.length
await hooks['session.compaction']({ sessionID: 's1' })
const ev2 = { sessionID: 's1', system: [] }
hooks['session.context'](ev2)
res.afterCompaction = ev2.system.length
const v1 = await plugin.server({ directory: %s })
res.v1hooks = Object.keys(v1)
console.log(JSON.stringify(res))
""" % (json.dumps((tmp / "opencode/plugins/v1rus.js").as_uri()), json.dumps(str(tmp)), json.dumps(str(tmp)))
            env = dict(__import__("os").environ, XDG_STATE_HOME=str(tmp / "state"))
            r = subprocess.run(["node", "--input-type=module", "-e", harness], capture_output=True, text=True, env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            res = json.loads(r.stdout)
            self.assertTrue(res["sudo"].startswith("blocked"), res)
            self.assertTrue(res["env"].startswith("blocked"), res)
            self.assertEqual(res["ls"], "ok")
            self.assertEqual(res["kt"], "ok")
            self.assertGreater(res["injected"], 0)
            self.assertEqual(res["afterCompaction"], 0)
            self.assertIn("tool.execute.before", res["v1hooks"])
        finally:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
