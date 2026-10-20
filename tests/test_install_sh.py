"""Tests for install.sh and scripts/package-release.py. No network: a file:// release layout is served from a temp dir.
Run: python3 -m unittest discover -s tests
"""
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
INSTALL = ROOT / "install.sh"
PACKAGE = ROOT / "scripts" / "package-release.py"
TAG = "v0.0.0-test"
PLACEHOLDER = b"@@V1RUS_OPENCODE_ROOT@@"


def snapshot(base):
    """{relative path: 'dir' | 'link->target' | sha256} of a tree (empty dirs included)."""
    out = {}
    base = pathlib.Path(base)
    for p in sorted(base.rglob("*")):
        rel = p.relative_to(base).as_posix()
        if p.is_symlink():
            out[rel] = "link->" + os.readlink(p)
        elif p.is_dir():
            out[rel] = "dir"
        else:
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


class InstallShTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = pathlib.Path(tempfile.mkdtemp(prefix="v1rus-install-test-"))
        rel = cls.tmp / "release"
        cp = subprocess.run([sys.executable, str(PACKAGE), "--version", TAG, "--out", str(rel)],
                            capture_output=True, text=True)
        assert cp.returncode == 0, cp.stderr
        cls.archive = rel / ("v1rus-opencode-%s.tar.gz" % TAG)
        cls.sha = rel / (cls.archive.name + ".sha256")
        cls.base = cls.tmp / "base"  # GitHub-like layout
        (cls.base / "download" / TAG).mkdir(parents=True)
        (cls.base / "latest" / "download").mkdir(parents=True)
        for f in (cls.archive, cls.sha):
            shutil.copy(f, cls.base / "download" / TAG / f.name)
        shutil.copy(cls.archive, cls.base / "latest" / "download" / "v1rus-opencode.tar.gz")
        (cls.base / "latest" / "download" / "v1rus-opencode.tar.gz.sha256").write_text(
            "%s  v1rus-opencode.tar.gz\n" % hashlib.sha256(cls.archive.read_bytes()).hexdigest())

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def setUp(self):
        self.home = pathlib.Path(tempfile.mkdtemp(dir=self.tmp, prefix="home-"))
        self.root = self.home / ".config" / "opencode"

    def run_install(self, *args, base=None, stdin=subprocess.DEVNULL, shell=False, extra_env=None):
        env = {k: v for k, v in os.environ.items() if not k.startswith(("XDG_", "V1RUS_"))}
        env.update(HOME=str(self.home), V1RUS_RELEASE_BASE_URL=(base or self.base).as_uri())
        env.update(extra_env or {})
        cmd = ["sh", str(INSTALL), "opencode", *args]
        return subprocess.run(cmd, env=env, stdin=stdin, capture_output=True, text=True, cwd=str(self.home))

    def installed(self, root=None):
        return (root or self.root) / "v1rus" / ".install-manifest"

    # ------------------------------------------------------------ happy path

    def test_install_lays_out_files_and_config(self):
        cp = self.run_install("--version", TAG)
        self.assertEqual(cp.returncode, 0, cp.stderr + cp.stdout)
        for sub in ("skills", "agents", "commands", "plugins/v1rus.js", "v1rus/charter.md"):
            self.assertTrue((self.root / sub).exists(), sub)
        self.assertTrue(self.installed().is_file())
        cfg = json.loads((self.root / "opencode.json").read_text())
        self.assertEqual(cfg["instructions"], [str(self.root / "v1rus" / "charter.md")])
        self.assertIn(TAG, self.installed().read_text())
        self.assertFalse((self.root / "README.md").exists())
        self.assertEqual(list(self.root.rglob("*.bak")), [])

    def test_latest_alias(self):
        cp = self.run_install()
        self.assertEqual(cp.returncode, 0, cp.stderr + cp.stdout)
        self.assertIn(TAG, self.installed().read_text())

    def test_idempotent(self):
        self.assertEqual(self.run_install("--version", TAG).returncode, 0)
        first = snapshot(self.home)
        cp = self.run_install("--version", TAG, stdin=subprocess.DEVNULL)
        self.assertEqual(cp.returncode, 0, cp.stderr + cp.stdout)
        self.assertEqual(first, snapshot(self.home))
        cfg = json.loads((self.root / "opencode.json").read_text())
        self.assertEqual(len(cfg["instructions"]), 1)

    def test_print_writes_nothing(self):
        before = snapshot(self.home)
        cp = self.run_install("--version", TAG, "--print")
        self.assertEqual(cp.returncode, 0, cp.stderr + cp.stdout)
        self.assertEqual(before, snapshot(self.home))
        self.assertIn("Dry run", cp.stdout)
        self.assertIn(str(self.root), cp.stdout)

    # ------------------------------------------------------------ integrity

    def test_sha_mismatch_aborts_and_writes_nothing(self):
        bad = self.tmp / ("badbase-%d" % id(self))
        shutil.copytree(self.base, bad)
        (bad / "download" / TAG / (self.archive.name + ".sha256")).write_text("0" * 64 + "  x\n")
        before = snapshot(self.home)
        cp = self.run_install("--version", TAG, "--yes", base=bad)
        self.assertNotEqual(cp.returncode, 0)
        self.assertIn("sha256 mismatch", cp.stderr)
        self.assertEqual(before, snapshot(self.home))

    def test_tampered_archive_aborts(self):
        bad = self.tmp / ("tampbase-%d" % id(self))
        shutil.copytree(self.base, bad)
        arc = bad / "download" / TAG / self.archive.name
        arc.write_bytes(arc.read_bytes() + b"x")
        before = snapshot(self.home)
        cp = self.run_install("--version", TAG, "--yes", base=bad)
        self.assertNotEqual(cp.returncode, 0)
        self.assertEqual(before, snapshot(self.home))

    def test_invalid_version_rejected(self):
        cp = self.run_install("--version", "../x")
        self.assertNotEqual(cp.returncode, 0)
        self.assertEqual(snapshot(self.home), {})

    # ------------------------------------------------------------ conflicts

    def conflict_setup(self):
        skill = self.root / "skills" / "api-contract" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("my own skill\n")
        mine = self.root / "skills" / "mine" / "SKILL.md"
        mine.parent.mkdir(parents=True)
        mine.write_text("untouched\n")
        return skill, mine

    def test_conflict_without_yes_refuses(self):
        skill, mine = self.conflict_setup()
        before = snapshot(self.home)
        cp = self.run_install("--version", TAG)  # stdin is not a tty
        self.assertNotEqual(cp.returncode, 0)
        self.assertIn("--yes", cp.stderr)
        self.assertIn("skills/api-contract/SKILL.md", cp.stdout)
        self.assertEqual(before, snapshot(self.home))

    def test_conflict_with_yes_makes_bak(self):
        skill, mine = self.conflict_setup()
        cp = self.run_install("--version", TAG, "--yes")
        self.assertEqual(cp.returncode, 0, cp.stderr + cp.stdout)
        bak = skill.with_name("SKILL.md.bak")
        self.assertEqual(bak.read_text(), "my own skill\n")
        self.assertNotEqual(skill.read_text(), "my own skill\n")
        self.assertEqual(mine.read_text(), "untouched\n")

    def test_edited_managed_file_is_a_conflict_on_update(self):
        self.assertEqual(self.run_install("--version", TAG).returncode, 0)
        target = self.root / "v1rus" / "charter.md"
        target.write_text("edited by user\n")
        cp = self.run_install("--version", TAG)
        self.assertNotEqual(cp.returncode, 0)
        self.assertEqual(target.read_text(), "edited by user\n")
        cp = self.run_install("--version", TAG, "--yes")
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertEqual(target.with_name("charter.md.bak").read_text(), "edited by user\n")

    def test_pipe_mode_refuses_conflicts_and_installs_clean(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith(("XDG_", "V1RUS_"))}
        env.update(HOME=str(self.home), V1RUS_RELEASE_BASE_URL=self.base.as_uri())
        self.conflict_setup()
        before = snapshot(self.home)
        cp = subprocess.run("cat '%s' | sh -s opencode --version %s" % (INSTALL, TAG), shell=True, env=env,
                            capture_output=True, text=True, cwd=str(self.home))
        self.assertNotEqual(cp.returncode, 0)
        self.assertEqual(before, snapshot(self.home))
        cp = subprocess.run("cat '%s' | sh -s opencode --version %s --yes" % (INSTALL, TAG), shell=True, env=env,
                            capture_output=True, text=True, cwd=str(self.home))
        self.assertEqual(cp.returncode, 0, cp.stderr + cp.stdout)
        self.assertTrue(self.installed().is_file())

    # ------------------------------------------------------------ uninstall

    def test_uninstall_restores_pristine_state_with_user_data(self):
        skill, mine = self.conflict_setup()
        user_cfg = {"theme": "x", "instructions": ["AGENTS.md"], "nested": {"a": [1, 2]}}
        cfg_path = self.root / "opencode.json"
        cfg_path.write_text(json.dumps(user_cfg, indent=2) + "\n")
        (self.home / "unrelated").mkdir()
        before = snapshot(self.home)
        self.assertEqual(self.run_install("--version", TAG, "--yes").returncode, 0)
        merged = json.loads(cfg_path.read_text())
        self.assertEqual(merged["theme"], "x")
        self.assertEqual(merged["nested"], {"a": [1, 2]})
        self.assertEqual(merged["instructions"][0], "AGENTS.md")
        self.assertEqual(len(merged["instructions"]), 2)
        self.assertTrue((self.root / "opencode.json.bak").is_file())
        cp = self.run_install("--uninstall")
        self.assertEqual(cp.returncode, 0, cp.stderr + cp.stdout)
        self.assertEqual(before, snapshot(self.home))

    def test_uninstall_on_fresh_home_removes_everything(self):
        before = snapshot(self.home)
        self.assertEqual(self.run_install("--version", TAG).returncode, 0)
        self.assertEqual(self.run_install("--uninstall", "--print").returncode, 0)
        self.assertTrue(self.installed().is_file())  # dry run
        self.assertEqual(self.run_install("--uninstall").returncode, 0)
        self.assertEqual(before, snapshot(self.home))

    def test_uninstall_keeps_user_edits_and_foreign_config_entries(self):
        self.assertEqual(self.run_install("--version", TAG).returncode, 0)
        cfg_path = self.root / "opencode.json"
        cfg = json.loads(cfg_path.read_text())
        cfg["instructions"].append("mine.md")
        cfg["model"] = "keep"
        cfg_path.write_text(json.dumps(cfg))  # edited after install: surgical removal path
        edited = self.root / "v1rus" / "charter.md"
        edited.write_text("my edit\n")
        self.assertEqual(self.run_install("--uninstall").returncode, 0)
        after = json.loads(cfg_path.read_text())
        self.assertEqual(after, {"instructions": ["mine.md"], "model": "keep"})
        self.assertEqual(edited.with_name("charter.md.bak").read_text(), "my edit\n")
        self.assertFalse(self.installed().exists())
        self.assertFalse((self.root / "skills").exists())

    def test_uninstall_without_manifest_does_nothing(self):
        (self.root).mkdir(parents=True)
        (self.root / "keep.txt").write_text("x")
        before = snapshot(self.home)
        cp = self.run_install("--uninstall")
        self.assertNotEqual(cp.returncode, 0)
        self.assertEqual(before, snapshot(self.home))

    # ------------------------------------------------------------ opencode.json safety

    def test_jsonc_config_is_left_untouched(self):
        self.root.mkdir(parents=True)
        cfg = self.root / "opencode.json"
        content = '{\n  // my comment\n  "theme": "x",\n}\n'
        cfg.write_text(content)
        cp = self.run_install("--version", TAG)
        self.assertEqual(cp.returncode, 0, cp.stderr + cp.stdout)
        self.assertEqual(cfg.read_text(), content)
        self.assertFalse((self.root / "opencode.json.bak").exists())
        self.assertIn(str(self.root / "v1rus" / "charter.md"), cp.stderr + cp.stdout)
        self.assertIn("unparseable", cp.stderr)
        self.assertEqual(self.run_install("--uninstall").returncode, 0)
        self.assertEqual(cfg.read_text(), content)

    def test_opencode_jsonc_file_is_not_shadowed(self):
        self.root.mkdir(parents=True)
        (self.root / "opencode.jsonc").write_text("{ // c\n}\n")
        cp = self.run_install("--version", TAG)
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertFalse((self.root / "opencode.json").exists())

    def test_existing_instruction_entry_is_not_removed_by_uninstall(self):
        self.root.mkdir(parents=True)
        entry = str(self.root / "v1rus" / "charter.md")
        cfg = self.root / "opencode.json"
        cfg.write_text(json.dumps({"instructions": [entry]}, indent=2) + "\n")
        before = cfg.read_text()
        self.assertEqual(self.run_install("--version", TAG).returncode, 0)
        self.assertEqual(cfg.read_text(), before)
        self.assertEqual(self.run_install("--uninstall").returncode, 0)
        self.assertEqual(cfg.read_text(), before)

    # ------------------------------------------------------------ location independence

    def test_project_install_in_custom_dir_has_no_placeholders(self):
        proj = self.home / "my proj & co"
        proj.mkdir()
        cp = self.run_install("--version", TAG, "--project", str(proj))
        self.assertEqual(cp.returncode, 0, cp.stderr + cp.stdout)
        root = proj / ".opencode"
        self.assertFalse(self.root.exists())
        self.assertTrue(self.installed(root).is_file())
        hits, with_root = [], 0
        real_home = str(pathlib.Path.home()).encode()
        for f in root.rglob("*"):
            if f.is_file():
                data = f.read_bytes()
                if PLACEHOLDER in data:
                    hits.append(str(f))
                if str(root).encode() in data:
                    with_root += 1
                if f.name.endswith((".md", ".js")) and real_home in data and real_home not in str(self.home).encode():
                    hits.append("foreign home in %s" % f)
        self.assertEqual(hits, [])
        self.assertGreater(with_root, 0, "agent/command texts should reference the real root")
        cfg = json.loads((root / "opencode.json").read_text())
        self.assertEqual(cfg["instructions"], [str(root / "v1rus" / "charter.md")])
        self.assertEqual(self.run_install("--uninstall", "--project", str(proj)).returncode, 0)
        self.assertEqual(snapshot(proj), {})

    def test_xdg_config_home_is_honoured(self):
        xdg = self.home / "xdg"
        xdg.mkdir()
        cp = self.run_install("--version", TAG, extra_env={"XDG_CONFIG_HOME": str(xdg)})
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertTrue(self.installed(xdg / "opencode").is_file())
        self.assertFalse(self.root.exists())


class PackageReleaseTest(unittest.TestCase):
    def test_archive_is_deterministic_and_checksummed(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            for out in (a, b):
                cp = subprocess.run([sys.executable, str(PACKAGE), "--version", "v9.9.9", "--out", out],
                                    capture_output=True, text=True)
                self.assertEqual(cp.returncode, 0, cp.stderr)
            name = "v1rus-opencode-v9.9.9.tar.gz"
            blob = pathlib.Path(a, name).read_bytes()
            self.assertEqual(blob, pathlib.Path(b, name).read_bytes())
            digest = hashlib.sha256(blob).hexdigest()
            self.assertEqual(pathlib.Path(a, name + ".sha256").read_text(), "%s  %s\n" % (digest, name))

    def test_bad_version_rejected(self):
        cp = subprocess.run([sys.executable, str(PACKAGE), "--version", "1.0; rm", "--out", tempfile.gettempdir() + "/x-never"],
                            capture_output=True, text=True)
        self.assertEqual(cp.returncode, 2)


if __name__ == "__main__":
    unittest.main()
