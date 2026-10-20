#!/usr/bin/env python3
"""Package the OpenCode artifacts into a deterministic release archive (stdlib only).

Usage:
  package-release.py --version vX.Y.Z [--out DIR]

Produces in DIR (default: dist/release):
  v1rus-opencode-<version>.tar.gz          deterministic: sorted entries, mtime 0, uid/gid 0, fixed modes, gzip mtime 0
  v1rus-opencode-<version>.tar.gz.sha256   "<sha256>  <file name>" (sha256sum format)

Archive layout (single top directory, so it is safe to extract anywhere):
  v1rus-opencode-<version>/VERSION         the version string
  v1rus-opencode-<version>/files/...       the OpenCode config-directory tree (skills/ agents/ commands/ plugins/ v1rus/)

Install-location independence: the agent/command texts need an absolute root (they have no base folder).
The archive is built with the placeholder PLACEHOLDER as `--opencode-root`; install.sh substitutes the real
root when installing. The placeholder appears only in text files (agents/, commands/); skills use relative
paths and the plugin finds its hooks relative to its own file. Anything else containing it is a build error.

Only READS plugins/ and .claude-plugin/ (through scripts/build-targets.py); writes only into --out.
"""
import argparse
import gzip
import hashlib
import importlib.util
import io
import re
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLACEHOLDER = "@@V1RUS_OPENCODE_ROOT@@"
VERSION_RE = re.compile(r"^v[0-9][0-9A-Za-z._-]*$")  # also what install.sh accepts for --version
# Top-level README.md of the generated tree describes the cp-based install; it must not land in the user's config dir.
EXCLUDE = {"README.md"}


def load_build_targets():
    spec = importlib.util.spec_from_file_location("build_targets", ROOT / "scripts" / "build-targets.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build_files(bt):
    """-> {relative posix path: bytes} of the OpenCode tree built with the placeholder root."""
    plugins = bt.load_plugins()
    oc, _cx, errs, _warnings, _renamed = bt.build_all(plugins, PLACEHOLDER, "~/.codex")
    if errs:
        raise bt.BuildError("; ".join(errs))
    files = {p: d for p, d in oc.files.items() if p not in EXCLUDE}
    for path, data in files.items():
        if PLACEHOLDER.encode() in data and not path.startswith(("agents/", "commands/")):
            raise bt.BuildError("placeholder in unexpected file %s (installer substitutes agents/ and commands/ only)" % path)
        if "\t" in path or "\n" in path or path.startswith("/") or ".." in path.split("/"):
            raise bt.BuildError("unsupported path in tree: %r" % path)
    return files


def make_archive(files, version):
    top = "v1rus-opencode-%s" % version
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.GNU_FORMAT) as tar:
        def add_dir(name):
            ti = tarfile.TarInfo(name)
            ti.type, ti.mode, ti.mtime = tarfile.DIRTYPE, 0o755, 0
            ti.uid = ti.gid = 0
            ti.uname = ti.gname = ""
            tar.addfile(ti)

        def add_file(name, data):
            ti = tarfile.TarInfo(name)
            ti.size, ti.mode, ti.mtime = len(data), 0o644, 0
            ti.uid = ti.gid = 0
            ti.uname = ti.gname = ""
            tar.addfile(ti, io.BytesIO(data))

        entries = {top + "/VERSION": (version + "\n").encode()}
        entries.update({top + "/files/" + p: d for p, d in files.items()})
        dirs = {top, top + "/files"}
        for name in entries:
            parent = name.rsplit("/", 1)[0]
            while parent not in dirs:
                dirs.add(parent)
                parent = parent.rsplit("/", 1)[0]
        for name in sorted(dirs | set(entries)):
            add_file(name, entries[name]) if name in entries else add_dir(name)
    out = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=out, compresslevel=9, mtime=0) as gz:
        gz.write(raw.getvalue())
    return out.getvalue()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", required=True, help="release tag, e.g. v1.2.3 (not hard-coded anywhere)")
    ap.add_argument("--out", default=str(ROOT / "dist" / "release"))
    args = ap.parse_args(argv)
    if not VERSION_RE.match(args.version):
        print("package-release: ERROR: version must match %s" % VERSION_RE.pattern, file=sys.stderr)
        return 2
    bt = load_build_targets()
    try:
        files = build_files(bt)
    except bt.BuildError as e:
        print("package-release: ERROR: %s" % e, file=sys.stderr)
        return 1
    blob = make_archive(files, args.version)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    name = "v1rus-opencode-%s.tar.gz" % args.version
    (out / name).write_bytes(blob)
    digest = hashlib.sha256(blob).hexdigest()
    (out / (name + ".sha256")).write_text("%s  %s\n" % (digest, name), encoding="utf-8")
    print("package-release: wrote %s (%d files, sha256 %s)" % (out / name, len(files), digest))
    return 0


if __name__ == "__main__":
    sys.exit(main())
