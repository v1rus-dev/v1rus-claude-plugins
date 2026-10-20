#!/usr/bin/env python3
"""Generate OpenCode and Codex artifacts from the Claude Code plugins (stdlib only).

Source of truth stays in plugins/ (Claude Code format). This script only READS plugins/ and
.claude-plugin/marketplace.json and writes into an output directory (default: dist/, git-ignored).

Usage:
  build-targets.py [--out DIR] [--opencode-root PATH] [--codex-root PATH]
  build-targets.py --check            build into a temp dir, validate, verify determinism; writes nothing

Layout produced (see README, section "Codex и OpenCode"):
  <out>/opencode/   skills/ agents/ commands/ plugins/v1rus.js v1rus/<plugin>/{rules,references,hooks} v1rus/charter.md
  <out>/codex/      .agents/plugins/marketplace.json  plugins/<plugin>/{plugin.json,skills,rules,references,commands,hooks}
                    agents/<name>.toml  v1rus/<plugin>/{skills,rules,references,commands}
"""
import argparse
import hashlib
import json
import posixpath
import re
import shutil
import sys
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGINS = ROOT / "plugins"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
ADAPTERS = ROOT / "scripts" / "adapters"
SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
TOKEN = "${CLAUDE_PLUGIN_ROOT}"
# ${CLAUDE_PLUGIN_ROOT} optionally followed by a path; stops at whitespace/quotes/brackets/backtick.
REF = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}((?:/[^\s`'\"()\[\]<>{}*,;|]*)?)")
FM = re.compile(r"\A---\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.S)
SKILL_NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
CHARTER_WARN_CHARS = 9000  # Codex caps hook additionalContext near 2500 tokens; ~3.6 chars/token heuristic


class BuildError(Exception):
    pass


# ---------------------------------------------------------------- plugin model

def load_plugins():
    market = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    entries = {p["name"]: p for p in market["plugins"]}
    plugins = {}
    for name in sorted(entries):
        pdir = PLUGINS / name
        meta = json.loads((pdir / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        plugins[name] = {
            "name": name, "dir": pdir, "meta": meta, "entry": entries[name],
            "deps": list(meta.get("dependencies") or []),
        }
    for p in plugins.values():
        for d in p["deps"]:
            if d not in plugins:
                raise BuildError("plugin %s depends on unknown plugin %s" % (p["name"], d))
    return plugins


def chain(plugins, name, seen=None):
    """Dependencies first (topological, deterministic), then the plugin itself."""
    seen = seen if seen is not None else []
    for d in sorted(plugins[name]["deps"]):
        chain(plugins, d, seen)
    if name not in seen:
        seen.append(name)
    return seen


def files_under(base):
    return sorted(p for p in base.rglob("*") if p.is_file() and "__pycache__" not in p.parts)


# ---------------------------------------------------------------- frontmatter

def split_fm(text):
    m = FM.match(text)
    return (m.group(1), text[m.end():]) if m else (None, text)


def parse_fm(fm):
    """Top-level keys only: scalar, quoted, block scalar (|, |-, >, >-). Enough for our agents."""
    out, lines, i = {}, fm.splitlines(), 0
    while i < len(lines):
        m = re.match(r"^([A-Za-z_][\w-]*):[ \t]*(.*)$", lines[i])
        i += 1
        if not m:
            continue
        key, val = m.group(1), m.group(2).rstrip()
        cont = []
        while i < len(lines) and (lines[i].startswith((" ", "\t")) or not lines[i].strip()):
            cont.append(lines[i])
            i += 1
        while cont and not cont[-1].strip():
            cont.pop()
        if re.match(r"^[|>][+-]?$", val):
            ind = min((len(c) - len(c.lstrip()) for c in cont if c.strip()), default=0)
            body = [c[ind:] for c in cont]
            out[key] = "\n".join(body) if val.startswith("|") else " ".join(b.strip() for b in body if b.strip())
        elif val.startswith('"'):
            full = " ".join([val] + [c.strip() for c in cont])
            try:
                out[key] = json.loads(full)
            except ValueError:
                out[key] = full.strip('"')
        elif val.startswith("'"):
            out[key] = " ".join([val] + [c.strip() for c in cont]).strip("'").replace("''", "'")
        else:
            out[key] = " ".join([val] + [c.strip() for c in cont]).strip()
    return out


def yaml_block(key, text, indent=""):
    body = "\n".join((indent + "  " + ln) if ln else "" for ln in text.strip("\n").split("\n"))
    return "%s%s: |-\n%s\n" % (indent, key, body)


# ---------------------------------------------------------------- reference rewriting

class Rewriter:
    """Replace ${CLAUDE_PLUGIN_ROOT}[/rel] in a text.

    mapper(owner, rel) -> posix path (relative to the output tree root) where that plugin-relative path lives.
    relative_to: dest-relative path of the file being written -> emit a path relative to it
                 (works wherever the tree is installed, relies on "paths in a skill resolve from its folder").
    absolute_prefix: emit prefix + mapped path (agents/commands have no base folder).
    """

    def __init__(self, mapper, owner, relative_to=None, absolute_prefix=None, refs=None, ref_base=""):
        self.mapper, self.owner = mapper, owner
        self.relative_to, self.absolute_prefix, self.refs = relative_to, absolute_prefix, refs
        self.ref_base = ref_base  # tree prefix of the output root the mapped path is relative to

    def __call__(self, text):
        def sub(m):
            rel = m.group(1).lstrip("/")
            trail = ""
            while rel and rel[-1] in ".:!?":
                trail = rel[-1] + trail
                rel = rel[:-1]
            target = self.mapper(self.owner, rel)
            if self.refs is not None and rel and not re.search(r"[<>*{}$]", rel):
                self.refs.append((self.owner, rel, self.ref_base + target))
            if self.relative_to is not None:
                out = posixpath.relpath(target, posixpath.dirname(self.relative_to)) if target else "."
            else:
                out = (self.absolute_prefix.rstrip("/") + "/" + target) if target else self.absolute_prefix.rstrip("/")
            return out + trail
        return REF.sub(sub, text)


def is_text(path):
    try:
        path.read_text(encoding="utf-8")
        return True
    except (UnicodeDecodeError, OSError):
        return False


class Tree:
    """In-memory output tree: {posix path: bytes}. Written once at the end -> deterministic."""

    def __init__(self):
        self.files = {}

    def put(self, path, data):
        if isinstance(data, str):
            data = data.encode("utf-8")
        if path in self.files and self.files[path] != data:
            raise BuildError("output collision at %s" % path)
        self.files[path] = data

    def copy(self, src, dest, rewriter=None):
        if rewriter is not None and is_text(src):
            self.put(dest, rewriter(src.read_text(encoding="utf-8")))
        else:
            self.put(dest, src.read_bytes())

    def write(self, out):
        if out.exists():
            shutil.rmtree(out)
        for path in sorted(self.files):
            target = out / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(self.files[path])


def tree_hash(tree_or_dir):
    h = hashlib.sha256()
    if isinstance(tree_or_dir, Tree):
        items = sorted(tree_or_dir.files.items())
    else:
        base = Path(tree_or_dir)
        items = [(p.relative_to(base).as_posix(), p.read_bytes()) for p in files_under(base)]
    for path, data in items:
        h.update(path.encode() + b"\0" + hashlib.sha256(data).digest())
    return h.hexdigest()


# ---------------------------------------------------------------- collisions / naming

def collect_names(plugins):
    """Skills must be unique (error). Agents with equal names get a `-<stack>` suffix (recorded)."""
    skills, agents = {}, {}
    for p in plugins.values():
        for f in sorted((p["dir"] / "skills").glob("*/SKILL.md")) if (p["dir"] / "skills").is_dir() else []:
            name = f.parent.name
            if name in skills:
                raise BuildError("skill name collision: '%s' exists in %s and %s; rename one (plugins/ is the "
                                 "source of truth, the generator will not guess)" % (name, skills[name], p["name"]))
            skills[name] = p["name"]
        for f in sorted((p["dir"] / "agents").glob("*.md")) if (p["dir"] / "agents").is_dir() else []:
            agents.setdefault(f.stem, []).append(p["name"])
    agent_names = {}
    for base, owners in agents.items():
        for owner in owners:
            final = base if len(owners) == 1 else "%s-%s" % (base, owner.replace("v1rus-", "", 1))
            if final in agent_names.values():
                raise BuildError("agent name collision after renaming: %s" % final)
            agent_names[(owner, base)] = final
    return agent_names


# ---------------------------------------------------------------- agents

TOOL_MAP = {
    "Read": ["read"], "Glob": ["glob", "list"], "Grep": ["grep"], "Bash": ["bash"],
    "Write": ["edit"], "Edit": ["edit"], "MultiEdit": ["edit"], "NotebookEdit": ["edit"],
    "WebFetch": ["webfetch"], "WebSearch": ["websearch"], "Skill": ["skill"], "Agent": ["task"],
}


def split_list(value):
    return [t.strip() for t in (value or "").split(",") if t.strip()]


def opencode_permission(fm):
    """Claude `tools` allow-list -> OpenCode `permission` (deny-all, then allow). None = inherit everything."""
    if not fm.get("tools"):
        return None
    allowed = []
    for tool in split_list(fm["tools"]):
        if tool.startswith("mcp__"):
            parts = tool.split("__", 2)  # mcp__server__tool -> OpenCode tool name server_tool
            allowed.append("%s_%s" % (parts[1], parts[2]) if len(parts) == 3 else tool)
        else:
            allowed.extend(TOOL_MAP.get(tool, []))  # TaskCreate & co have no OpenCode permission key
    denied = {k for t in split_list(fm.get("disallowedTools")) for k in TOOL_MAP.get(t, [])}
    keys = sorted({k for k in allowed if k not in denied})
    return keys


def build_opencode_agent(fm, body, mapper_rewriter):
    desc = fm.get("description") or ""
    if not desc.strip():
        raise BuildError("agent without description")
    out = "---\n" + yaml_block("description", desc) + "mode: subagent\n"
    # model: intentionally omitted. Claude aliases (sonnet/opus) have no reliable provider/model-id
    # mapping; OpenCode then uses the model of the invoking agent.
    keys = opencode_permission(fm)
    if keys is not None:
        out += "permission:\n  \"*\": deny\n" + "".join("  %s: allow\n" % k for k in keys)
    # dropped on purpose: name (file name is the id), color (Claude names are not valid), memory,
    # maxTurns, effort, skills, disallowedTools (folded into permission). OpenCode passes unknown
    # keys through to the provider as model options, so leaving them in would be harmful.
    return out + "---\n" + mapper_rewriter(body)


def toml_str(s):
    return json.dumps(s, ensure_ascii=False)


def toml_multiline(s):
    s = s.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
    s = "".join(c if (c in "\n\t" or ord(c) >= 32 and ord(c) != 127) else "\\u%04x" % ord(c) for c in s)
    return '"""\n' + s.strip("\n") + '\n"""'


def build_codex_agent(name, fm, body, rewriter):
    desc = fm.get("description") or ""
    if not desc.strip():
        raise BuildError("agent %s without description" % name)
    # model / sandbox_mode intentionally omitted: no verified mapping from Claude aliases/tool lists.
    return "name = %s\ndescription = %s\ndeveloper_instructions = %s\n" % (
        toml_str(name), toml_str(desc.strip()), toml_multiline(rewriter(body)))


# ---------------------------------------------------------------- OpenCode

def opencode_mapper(agent_names):
    def mapper(owner, rel):
        head = rel.split("/", 1)[0]
        if head == "skills" or head == "commands":
            return rel
        if head == "agents":
            parts = rel.split("/", 1)
            if len(parts) == 2 and parts[1].endswith(".md"):
                return "agents/" + agent_names.get((owner, parts[1][:-3]), parts[1][:-3]) + ".md"
            return rel
        return posixpath.join("v1rus", owner, rel) if rel else posixpath.join("v1rus", owner)
    return mapper


def build_opencode(plugins, agent_names, root_prefix, refs):
    t = Tree()
    mapper = opencode_mapper(agent_names)
    for p in plugins.values():
        pdir, name = p["dir"], p["name"]
        for f in files_under(pdir / "skills") if (pdir / "skills").is_dir() else []:
            rel = f.relative_to(pdir).as_posix()
            t.copy(f, rel, Rewriter(mapper, name, relative_to=rel, refs=refs))
        for sub in ("rules", "references"):
            for f in files_under(pdir / sub) if (pdir / sub).is_dir() else []:
                rel = f.relative_to(pdir).as_posix()
                dest = "v1rus/%s/%s" % (name, rel)
                t.copy(f, dest, Rewriter(mapper, name, relative_to=dest, refs=refs) if sub == "references" else None)
        hooks = pdir / "hooks"
        keep = {"path-rules.py"} | ({"git-guard.py", "secrets-guard.py", "inject-charter.py", "charter.md"} if name == "v1rus-core" else set())
        for f in files_under(hooks) if hooks.is_dir() else []:
            if f.name in keep:
                t.copy(f, "v1rus/%s/hooks/%s" % (name, f.name))
        for f in sorted((pdir / "commands").glob("*.md")) if (pdir / "commands").is_dir() else []:
            fm_text, body = split_fm(f.read_text(encoding="utf-8"))
            fm = parse_fm(fm_text or "")
            rw = Rewriter(mapper, name, absolute_prefix=root_prefix, refs=refs)
            head = "---\n" + ("description: %s\n" % json.dumps(fm["description"], ensure_ascii=False) if fm.get("description") else "") + "---\n"
            t.put("commands/%s" % f.name, head + rw(body))
        for f in sorted((pdir / "agents").glob("*.md")) if (pdir / "agents").is_dir() else []:
            fm_text, body = split_fm(f.read_text(encoding="utf-8"))
            if fm_text is None:
                raise BuildError("%s: no frontmatter" % f)
            rw = Rewriter(mapper, name, absolute_prefix=root_prefix, refs=refs)
            t.put("agents/%s.md" % agent_names[(name, f.stem)], build_opencode_agent(parse_fm(fm_text), body, rw))
    t.copy(PLUGINS / "v1rus-core" / "hooks" / "charter.md", "v1rus/charter.md")
    t.copy(ADAPTERS / "opencode-plugin.js", "plugins/v1rus.js")
    t.put("README.md", OPENCODE_README % {"root": root_prefix})
    return t


OPENCODE_README = """# v1rus for OpenCode (generated, do not edit)

Generated by scripts/build-targets.py from the Claude Code plugins. Layout equals an OpenCode config directory.

Install (global):   cp -R <this dir>/. ~/.config/opencode/        (or into <project>/.opencode/)
Charter:            add to opencode.json:  "instructions": ["%(root)s/v1rus/charter.md"]
Agent/command texts reference files under %(root)s (set with --opencode-root when building).
Requires python3 on PATH (the hooks are the original Python scripts).
"""


# ---------------------------------------------------------------- Codex

def codex_hooks(charter_cmd=True):
    def cmd(script, adapter=True):
        if adapter:
            return 'python3 "${PLUGIN_ROOT}/hooks/codex-adapter.py" %s' % script
        return 'python3 "${PLUGIN_ROOT}/hooks/%s"' % script
    return {"hooks": {
        "SessionStart": [{"hooks": [{"type": "command", "command": cmd("inject-charter.py", False), "timeout": 10}]}],
        "PreToolUse": [
            {"matcher": "Read|Write|Edit|MultiEdit|NotebookEdit|apply_patch|Bash",
             "hooks": [{"type": "command", "command": cmd("secrets-guard.py"), "timeout": 10}]},
            {"matcher": "Bash", "hooks": [{"type": "command", "command": cmd("git-guard.py"), "timeout": 15}]},
            {"matcher": "apply_patch|Write|Edit|MultiEdit",
             "hooks": [{"type": "command", "command": cmd("path-rules.py"), "timeout": 10}]},
        ],
        "PreCompact": [{"hooks": [{"type": "command", "command": cmd("path-rules.py"), "timeout": 10}]}],
    }}


def codex_mirror_mapper(owner, rel):
    return posixpath.join("v1rus", owner, rel) if rel else posixpath.join("v1rus", owner)


def build_codex(plugins, agent_names, root_prefix, refs):
    t = Tree()
    ident = lambda owner, rel: rel  # noqa: E731 - bundle root == plugin-relative layout
    warnings = []
    for name, p in plugins.items():
        base = "plugins/%s" % name
        layers = chain(plugins, name)
        # Bundle = this plugin + all its dependencies, merged into one flat plugin root.
        for layer in layers:
            ldir = plugins[layer]["dir"]
            for sub in ("skills", "rules", "references", "commands"):
                for f in files_under(ldir / sub) if (ldir / sub).is_dir() else []:
                    rel = f.relative_to(ldir).as_posix()
                    dest = "%s/%s" % (base, rel)
                    rewrite = None if sub == "rules" else Rewriter(ident, layer, relative_to=rel, refs=refs, ref_base=base + "/")
                    try:
                        t.copy(f, dest, rewrite)
                    except BuildError:
                        raise BuildError("bundle %s: %s from %s collides with another layer" % (name, rel, layer))
        # hooks: adapter + unmodified scripts; path-rules.py comes from the bundle's own plugin.
        core = plugins["v1rus-core"]["dir"] / "hooks"
        for fname in ("inject-charter.py", "git-guard.py", "secrets-guard.py", "charter.md"):
            t.copy(core / fname, "%s/hooks/%s" % (base, fname))
        t.copy(p["dir"] / "hooks" / "path-rules.py", "%s/hooks/path-rules.py" % base)
        t.copy(ADAPTERS / "codex_hook_adapter.py", "%s/hooks/codex-adapter.py" % base)
        t.put("%s/hooks/hooks.json" % base, json.dumps(codex_hooks(), indent=2) + "\n")
        meta = p["meta"]
        manifest = {
            "$schema": SCHEMA, "name": name, "version": meta["version"],
            "description": meta.get("description", ""),
            "author": meta.get("author", {}), "license": meta.get("license", "UNLICENSED"),
            "keywords": meta.get("keywords", []),
            "extensions": {"com.openai": {
                "hooks": "./hooks/hooks.json",
                "interface": {"displayName": meta.get("displayName", name),
                              "shortDescription": p["entry"].get("description", "")[:200],
                              "category": p["entry"].get("category", "conventions")},
            }},
        }
        t.put("%s/plugin.json" % base, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
        # mirror (per single plugin, no merging) for agents, which Codex does not load from plugins
        for sub in ("skills", "rules", "references", "commands"):
            for f in files_under(p["dir"] / sub) if (p["dir"] / sub).is_dir() else []:
                rel = f.relative_to(p["dir"]).as_posix()
                dest = "v1rus/%s/%s" % (name, rel)
                t.copy(f, dest, None if sub == "rules" else Rewriter(ident, name, relative_to=rel, refs=refs, ref_base="v1rus/%s/" % name))
        for f in sorted((p["dir"] / "agents").glob("*.md")) if (p["dir"] / "agents").is_dir() else []:
            fm_text, body = split_fm(f.read_text(encoding="utf-8"))
            if fm_text is None:
                raise BuildError("%s: no frontmatter" % f)
            rw = Rewriter(codex_mirror_mapper, name, absolute_prefix=root_prefix, refs=refs)
            aname = agent_names[(name, f.stem)]
            t.put("agents/%s.toml" % aname, build_codex_agent(aname, parse_fm(fm_text), body, rw))
    charter_len = len((PLUGINS / "v1rus-core" / "hooks" / "charter.md").read_text(encoding="utf-8"))
    if charter_len > CHARTER_WARN_CHARS:
        warnings.append("charter.md is %d chars: Codex truncates hook additionalContext near 2500 tokens" % charter_len)
    market = {
        "name": "v1rus-dev",
        "interface": {"displayName": "v1rus-dev"},
        "plugins": [{
            "name": n, "source": {"source": "local", "path": "./plugins/%s" % n},
            "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
            "category": plugins[n]["entry"].get("category", "conventions"),
        } for n in plugins],
    }
    t.put(".agents/plugins/marketplace.json", json.dumps(market, indent=2) + "\n")
    t.put("README.md", CODEX_README % {"root": root_prefix})
    return t, warnings


CODEX_README = """# v1rus for Codex (generated, do not edit)

Generated by scripts/build-targets.py. NOT run against a real Codex binary: format follows the Codex docs.

Marketplace:  codex plugin marketplace add <path to this dir>
Each plugin under plugins/ is a self-contained bundle (dependencies merged in): install ONE layer, not several.
Hooks of plugins need a manual trust review in Codex (/hooks).
Agents are not a plugin component: cp agents/*.toml ~/.codex/agents/ and cp -R v1rus %(root)s/v1rus
"""


# ---------------------------------------------------------------- validation

def check_refs(tree, refs, label):
    bad = []
    for owner, rel, target in refs:
        if target not in tree.files and not any(k.startswith(target.rstrip("/") + "/") for k in tree.files):
            bad.append("%s: %s -> %s (not produced)" % (owner, rel, target))
    return ["%s dangling reference %s" % (label, b) for b in sorted(set(bad))]


def validate(tree, label, kind):
    errs = []
    for path, data in sorted(tree.files.items()):
        if path.endswith(".json"):
            try:
                json.loads(data)
            except ValueError as e:
                errs.append("%s/%s invalid JSON: %s" % (label, path, e))
        elif path.endswith(".toml"):
            try:
                tomllib.loads(data.decode("utf-8"))
            except (tomllib.TOMLDecodeError, UnicodeDecodeError) as e:
                errs.append("%s/%s invalid TOML: %s" % (label, path, e))
        # copied hook scripts are byte-for-byte originals and legitimately mention the variable
        if not path.endswith(".py") and TOKEN.encode() in data:
            errs.append("%s/%s still contains %s" % (label, path, TOKEN))
        if re.search(r"(^|/)SKILL\.md$", path):
            fm = parse_fm(split_fm(data.decode("utf-8"))[0] or "")
            sname = path.split("/")[-2]
            if fm.get("name") != sname or not SKILL_NAME.match(sname):
                errs.append("%s/%s: skill name must equal directory and be kebab-case" % (label, path))
            if not fm.get("description"):
                errs.append("%s/%s: empty description" % (label, path))
        if kind == "opencode" and path.startswith("agents/"):
            fm = parse_fm(split_fm(data.decode("utf-8"))[0] or "")
            if not fm.get("description") or fm.get("mode") != "subagent":
                errs.append("%s/%s: agent needs description and mode: subagent" % (label, path))
        if kind == "codex" and path.startswith("agents/"):
            doc = tomllib.loads(data.decode("utf-8"))
            for k in ("name", "description", "developer_instructions"):
                if not doc.get(k):
                    errs.append("%s/%s: missing %s" % (label, path, k))
    return errs


def build_all(plugins, opencode_root, codex_root):
    agent_names = collect_names(plugins)
    refs_oc, refs_cx = [], []
    oc = build_opencode(plugins, agent_names, opencode_root, refs_oc)
    cx, warnings = build_codex(plugins, agent_names, codex_root, refs_cx)
    errs = check_refs(oc, refs_oc, "opencode") + check_refs(cx, refs_cx, "codex")
    errs += validate(oc, "opencode", "opencode") + validate(cx, "codex", "codex")
    renamed = {"%s:%s" % k: v for k, v in agent_names.items() if k[1] != v}
    long_desc = sorted(
        path.split("/")[-2] for path, data in oc.files.items() if path.startswith("skills/") and path.endswith("/SKILL.md")
        and len(parse_fm(split_fm(data.decode("utf-8"))[0] or "").get("description", "")) > 1024)
    if long_desc:
        # Verified accepted by OpenCode 2.x; the OpenCode 1.x docs state a 1024-char limit (not verified there).
        warnings.append("%d OpenCode skills have descriptions over 1024 chars (accepted by OpenCode 2.x, "
                        "documented limit of 1.x): %s" % (len(long_desc), ", ".join(long_desc[:3]) + ", ..."))
    return oc, cx, errs, warnings, renamed


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(ROOT / "dist"))
    ap.add_argument("--opencode-root", default="~/.config/opencode",
                    help="where dist/opencode is installed; used for paths inside agent/command texts")
    ap.add_argument("--codex-root", default="~/.codex", help="where dist/codex/v1rus is installed (agent texts)")
    ap.add_argument("--check", action="store_true", help="build twice into temp dirs, validate, compare; write nothing")
    args = ap.parse_args(argv)
    try:
        plugins = load_plugins()
        oc, cx, errs, warnings, renamed = build_all(plugins, args.opencode_root, args.codex_root)
        if args.check:
            oc2, cx2, _, _, _ = build_all(plugins, args.opencode_root, args.codex_root)
            if tree_hash(oc) != tree_hash(oc2) or tree_hash(cx) != tree_hash(cx2):
                errs.append("non-deterministic output")
            with tempfile.TemporaryDirectory() as tmp:  # also exercise real file writing
                oc.write(Path(tmp) / "opencode")
                if tree_hash(Path(tmp) / "opencode") != tree_hash(oc):
                    errs.append("written opencode tree differs from in-memory tree")
    except BuildError as e:
        print("build-targets: ERROR: %s" % e, file=sys.stderr)
        return 1
    for w in warnings:
        print("build-targets: warning: %s" % w, file=sys.stderr)
    if errs:
        for e in errs:
            print("build-targets: ERROR: %s" % e, file=sys.stderr)
        return 1
    if renamed:
        print("build-targets: agents renamed to avoid collisions: %s" % ", ".join("%s -> %s" % kv for kv in sorted(renamed.items())))
    if args.check:
        print("build-targets: check OK (opencode %d files, codex %d files, deterministic)" % (len(oc.files), len(cx.files)))
        return 0
    out = Path(args.out)
    oc.write(out / "opencode")
    cx.write(out / "codex")
    print("build-targets: wrote %s (opencode %d files, codex %d files)" % (out, len(oc.files), len(cx.files)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
