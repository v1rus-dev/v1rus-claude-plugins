#!/usr/bin/env python3
"""Consistency checks for the v1rus-dev marketplace (stdlib only).

Usage:
  check-plugins.py --all             structure/content checks on the working tree
  check-plugins.py --staged          --all + version-bump check of the staged change vs HEAD
  check-plugins.py --base <ref>      --all + version-bump check of the working tree vs <ref>
Exit 1 on any error; warnings never fail.
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLUGINS = ROOT / "plugins"
errors, warnings = [], []


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def git(*args):
    p = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return p.returncode, p.stdout


def load_json(path, what):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        err("%s: missing" % what)
    except ValueError as e:
        err("%s: invalid JSON (%s)" % (what, e))
    return None


def frontmatter(text):
    m = re.match(r"---\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", text, re.S)
    return m.group(1) if m else None


def fm_scalar(fm, key):
    """Return (found, raw_value_on_key_line, following_lines)."""
    lines = fm.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"%s\s*:\s*(.*)$" % re.escape(key), line)
        if m:
            cont = []
            for nxt in lines[i + 1:]:
                if nxt.startswith((" ", "\t")) and nxt.strip():
                    cont.append(nxt)
                else:
                    break
            return True, m.group(1).strip(), cont
    return False, "", []


def description_empty(fm):
    """True when `description` is present but has no text (empty scalar or empty block scalar)."""
    found, val, cont = fm_scalar(fm, "description")
    if not found:
        return False
    if re.match(r"^[|>][+-]?$", val):
        return not any(c.strip() for c in cont)
    return val.strip("\"' ") == "" and not cont


def check_marketplace():
    mp = load_json(ROOT / ".claude-plugin/marketplace.json", "marketplace.json")
    if mp is None:
        return {}
    listed = {}
    for e in mp.get("plugins", []):
        name, src = e.get("name"), e.get("source")
        if not name or not isinstance(src, str):
            err("marketplace.json: entry needs name and relative-path source: %r" % e)
            continue
        if name in listed:
            err("marketplace.json: duplicate plugin %s" % name)
        listed[name] = e
        pdir = (ROOT / src).resolve()
        if not (pdir / ".claude-plugin/plugin.json").is_file():
            err("marketplace.json: %s -> %s has no .claude-plugin/plugin.json" % (name, src))
        elif pdir.name != name:
            err("marketplace.json: entry %s points to directory %s" % (name, pdir.name))
    on_disk = {p.name for p in PLUGINS.iterdir() if p.is_dir()} if PLUGINS.is_dir() else set()
    for n in sorted(on_disk - set(listed)):
        err("plugins/%s exists but is not listed in marketplace.json" % n)
    return listed


def check_plugin(pdir, listed):
    name = pdir.name
    pj = load_json(pdir / ".claude-plugin/plugin.json", "%s/plugin.json" % name)
    if pj is None:
        return None
    if pj.get("name") != name:
        err("%s: plugin.json name %r != directory name" % (name, pj.get("name")))
    if not re.match(r"^\d+\.\d+\.\d+$", str(pj.get("version", ""))):
        err("%s: plugin.json version must be semver X.Y.Z" % name)
    deps = pj.get("dependencies", [])
    if not isinstance(deps, list):
        err("%s: dependencies must be an array" % name)
        deps = []
    for d in deps:
        dn = d if isinstance(d, str) else d.get("name") if isinstance(d, dict) else None
        if not dn:
            err("%s: bad dependency entry %r" % (name, d))
        elif "@" not in dn and dn not in listed:
            err("%s: dependency %s is not in marketplace.json" % (name, dn))
        if isinstance(d, dict) and d.get("version"):
            warn("%s: dependency %s pins a version range; layering normally tracks latest" % (name, dn))
    ev = listed.get(name, {}).get("version")
    if ev and ev != pj.get("version"):
        err("%s: marketplace entry version %s != plugin.json %s" % (name, ev, pj.get("version")))

    # skills
    for sk in sorted((pdir / "skills").glob("*/SKILL.md")):
        fm = frontmatter(sk.read_text(encoding="utf-8"))
        if fm is None:
            err("%s: no frontmatter" % sk.relative_to(ROOT))
            continue
        found, val, _ = fm_scalar(fm, "name")
        if found and val.strip("\"'") != sk.parent.name:
            err("%s: name %r != directory %r" % (sk.relative_to(ROOT), val, sk.parent.name))
        if not fm_scalar(fm, "description")[0]:
            err("%s: description missing" % sk.relative_to(ROOT))
        elif description_empty(fm):
            err("%s: description is empty" % sk.relative_to(ROOT))

    # agents
    for ag in sorted((pdir / "agents").rglob("*.md")):
        rel = ag.relative_to(ROOT)
        fm = frontmatter(ag.read_text(encoding="utf-8"))
        if fm is None:
            err("%s: no frontmatter" % rel)
            continue
        for key in ("name", "description"):
            if not fm_scalar(fm, key)[0]:
                err("%s: %s missing" % (rel, key))
        if description_empty(fm):
            err("%s: description is empty" % rel)
        found, val, cont = fm_scalar(fm, "description")
        if found and cont and not re.match(r"^[|>][+-]?$", val):
            err("%s: multi-line description must use a block scalar (|-), not a plain/quoted scalar" % rel)
        if found and val and val[0] in "\"'" and (len(val) < 2 or val[-1] != val[0]):
            err("%s: unterminated quoted description (use block scalar |-)" % rel)
        if found and val and val[0] not in "\"'|>" and re.search(r":\s", val):
            err("%s: unquoted description contains ': ' (YAML breaks; use block scalar |-)" % rel)
        for bad in ("permissionMode", "hooks", "mcpServers", "initialPrompt"):
            if fm_scalar(fm, bad)[0]:
                warn("%s: frontmatter field %s is ignored in plugin agents" % (rel, bad))

    # rules / charter
    for rl in sorted((pdir / "rules").glob("*.md")):
        fm = frontmatter(rl.read_text(encoding="utf-8")) or ""
        if not re.search(r"^paths\s*:", fm, re.M):
            warn("%s: rule without `paths:` is never injected by the path engine (put always-on text in core's hooks/charter.md)" % rl.relative_to(ROOT))
    ch = pdir / "hooks" / "charter.md"
    if ch.is_file() and len(ch.read_text(encoding="utf-8").splitlines()) > 200:
        warn("%s: charter over 200 lines (loaded every session)" % ch.relative_to(ROOT))

    check_references(pdir)
    return pj


AGENT_NAME_RE = re.compile(r"`([a-z][a-z0-9]*(?:-[a-z0-9]+)*-(?:expert|engineer|runner|developer|reviewer))`")
OPTIONAL_HINT_RE = re.compile(r"if installed|when installed|if available|if present|when present|when .{0,40}(?:is|are) installed|not installed|optional|ships with|skipped", re.I)


def dependency_chain(name, plugins):
    """name plus all transitive declared dependencies (plugins: name -> plugin.json dict)."""
    seen, stack = set(), [name]
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        for d in (plugins.get(n) or {}).get("dependencies") or []:
            dn = d if isinstance(d, str) else d.get("name") if isinstance(d, dict) else None
            if dn:
                stack.append(dn.split("@")[0])
    return seen


def check_agent_refs(plugins):
    """WARN on backticked agent-like names not defined in the plugin or its dependency chain.
    Lines that mark the reference as optional (`if installed`, ...) are accepted."""
    defined = {n: {a.stem for a in (PLUGINS / n / "agents").rglob("*.md")} for n in plugins}
    for n in plugins:
        visible = set().union(*(defined.get(d, set()) for d in dependency_chain(n, plugins)))
        for f in sorted((PLUGINS / n).rglob("*.md")):
            for ln, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                for m in AGENT_NAME_RE.finditer(line):
                    if m.group(1) not in visible and not OPTIONAL_HINT_RE.search(line):
                        warn("%s:%d: agent `%s` is not defined in %s or its dependency chain (make it explicitly optional: 'if installed, else ...')" % (f.relative_to(ROOT), ln, m.group(1), n))


REF_RE = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([^\s\"'`)>\]\\…]+)")
LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)")
PIN_RE = re.compile(r"[A-Za-z][\w.-]*\.[\w.-]+:[\w.-]+:\d+\.\d+(?:\.\d+)?|\bversion\s*=\s*\"\d+\.\d+")


def check_references(pdir):
    for f in sorted(pdir.rglob("*")):
        if not f.is_file() or f.suffix not in {".md", ".json", ".py", ".sh"} or "node_modules" in f.parts:
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        rel = f.relative_to(ROOT)
        for m in REF_RE.finditer(text):
            target = m.group(1).rstrip(".,;:")
            if any(c in target for c in "*<>{$"):
                continue
            if not (pdir / target).exists():
                err("%s: broken ${CLAUDE_PLUGIN_ROOT}/%s" % (rel, target))
        if f.suffix == ".md":
            in_code = False
            for ln, line in enumerate(text.splitlines(), 1):
                if line.lstrip().startswith("```"):
                    in_code = not in_code
                    continue
                if in_code:
                    continue
                for m in LINK_RE.finditer(line):
                    t = m.group(1).split("#")[0]
                    if not t or re.match(r"^[a-z][a-z0-9+.-]*:", t) or t.startswith("${") or any(c in t for c in "*<>"):
                        continue
                    if not (f.parent / t).exists():
                        err("%s:%d: broken relative link %s" % (rel, ln, t))
                if PIN_RE.search(line):
                    warn("%s:%d: possible hardcoded dependency version (resolve via tools, don't pin in docs)" % (rel, ln))


def check_cycles(plugins):
    graph = {n: [d if isinstance(d, str) else d.get("name") for d in (pj.get("dependencies") or [])] for n, pj in plugins.items()}
    state = {}

    def visit(n, path):
        if state.get(n) == 1:
            err("dependency cycle: %s" % " -> ".join(path + [n]))
            return
        if state.get(n) == 2 or n not in graph:
            return
        state[n] = 1
        for d in graph[n]:
            visit(d, path + [n])
        state[n] = 2

    for n in graph:
        visit(n, [])


def version_at(ref, path):
    """ref '' -> index (staged), else a git ref. None when the file did not exist."""
    rc, out = git("show", "%s:%s" % (ref, path))
    if rc != 0:
        return None
    try:
        return json.loads(out).get("version")
    except ValueError:
        return None


def check_bumps(base_ref, staged):
    if git("rev-parse", "--verify", "-q", base_ref)[0] != 0:
        print("note: no %s yet, skipping version-bump check" % base_ref)
        return
    if staged:
        rc, out = git("diff", "--cached", "--name-only", "--diff-filter=ACMRD", base_ref)
    else:
        rc, out = git("diff", "--name-only", base_ref)
        rc2, out2 = git("ls-files", "--others", "--exclude-standard")
        out += out2
    changed = {}
    for line in out.splitlines():
        parts = line.split("/")
        if len(parts) > 2 and parts[0] == "plugins":
            changed.setdefault(parts[1], []).append(line)
    for name, files in sorted(changed.items()):
        pjpath = "plugins/%s/.claude-plugin/plugin.json" % name
        old = version_at(base_ref, pjpath)
        if old is None:
            continue  # new plugin
        if staged:
            new = version_at("", pjpath)
        else:
            try:
                new = json.loads((ROOT / pjpath).read_text(encoding="utf-8")).get("version")
            except Exception:
                new = None
        if new is None:
            continue  # plugin removed
        if new == old:
            err("%s: files changed (%d) but plugin.json version is still %s -- bump it, or installed copies never update" % (name, len(files), old))
        elif _vkey(new) <= _vkey(old):
            err("%s: version went %s -> %s (must increase)" % (name, old, new))


def _vkey(v):
    try:
        return tuple(int(x) for x in v.split("."))
    except ValueError:
        return (0, 0, 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--all", action="store_true")
    g.add_argument("--staged", action="store_true")
    g.add_argument("--base", metavar="REF")
    a = ap.parse_args()

    listed = check_marketplace()
    plugins = {}
    if PLUGINS.is_dir():
        for pdir in sorted(p for p in PLUGINS.iterdir() if p.is_dir()):
            pj = check_plugin(pdir, listed)
            if pj:
                plugins[pdir.name] = pj
    check_cycles(plugins)
    check_agent_refs(plugins)
    if a.staged:
        check_bumps("HEAD", True)
    elif a.base:
        check_bumps(a.base, False)

    for w in warnings:
        print("WARN  " + w)
    for e in errors:
        print("ERROR " + e)
    print("%d plugin(s), %d error(s), %d warning(s)" % (len(plugins), len(errors), len(warnings)))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
