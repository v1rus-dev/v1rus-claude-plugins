#!/bin/sh
# v1rus-dev installer for OpenCode artifacts (no repository clone needed).
#
#   curl -fsSL <raw-url>/install.sh | sh -s opencode [options]
#
# Usage: install.sh opencode [--version vX.Y.Z|latest] [--project DIR] [--print] [--uninstall] [--yes]
#
#   --version V   release tag to install (default: latest)
#   --project DIR install into DIR/.opencode instead of the global OpenCode config directory
#   --print       dry run: downloads and verifies the archive into a temp dir, prints what would be
#                 created/changed, writes NOTHING to the install location
#   --uninstall   remove what a previous install put there (driven by the install manifest)
#   --yes         allow replacing files that were not installed by us (they are saved as .bak first)
#
# Environment:
#   V1RUS_RELEASE_BASE_URL  override the release URL prefix (default: the GitHub releases page of
#                           v1rus-dev/v1rus-claude-plugins). Layout below it, as on GitHub:
#                             <base>/download/<tag>/v1rus-opencode-<tag>.tar.gz[.sha256]
#                             <base>/latest/download/v1rus-opencode.tar.gz[.sha256]
#
# Requirements: POSIX sh, curl, tar, a sha256 tool (sha256sum | shasum | openssl). python3 is needed to edit
# opencode.json and by the installed hooks themselves; without it the install proceeds and prints the one
# manual opencode.json line.
#
# Install-location independence: the archive carries the placeholder @@V1RUS_OPENCODE_ROOT@@ in agent and
# command texts; this script substitutes the real (absolute) install root before anything is written, and
# fails if a placeholder is left over. Skills use relative paths and the plugin resolves hooks relative to
# its own file, so nothing else depends on the location.
#
# The whole script body lives in main() so that, when piped into `sh`, the shell has read it completely
# before running anything (children never compete with the shell for the script on stdin).
set -eu

DEFAULT_BASE_URL="https://github.com/v1rus-dev/v1rus-claude-plugins/releases"
PLACEHOLDER='@@V1RUS_OPENCODE_ROOT@@'
TAB=$(printf '\t')
NL='
'
TMP=""

say() { printf '%s\n' "$*"; }
warn() { printf 'install.sh: warning: %s\n' "$*" >&2; }
die() { printf 'install.sh: ERROR: %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<'EOF'
Usage: install.sh opencode [--version vX.Y.Z|latest] [--project DIR] [--print] [--uninstall] [--yes]
  --version V    release tag to install (default: latest)
  --project DIR  install into DIR/.opencode instead of the global OpenCode config directory
  --print        dry run: show what would happen, write nothing to the install location
  --uninstall    remove what a previous install put there (uses the install manifest)
  --yes          replace files not installed by us (saved as .bak first); required when stdin is not a terminal
EOF
}

cleanup() {
  if [ -n "$TMP" ] && [ -d "$TMP" ]; then rm -rf "$TMP"; fi
}

# ---------------------------------------------------------------- helpers

sha_of() { # file -> hex digest
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum -- "$1" | cut -d' ' -f1
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 -- "$1" | cut -d' ' -f1
  elif command -v openssl >/dev/null 2>&1; then
    openssl dgst -sha256 "$1" | sed 's/^.*= *//'
  else
    die "no sha256 tool found (need sha256sum, shasum or openssl)"
  fi
}

cur_hash() { # path -> digest | L (symlink) | D (directory) | O (other) | - (absent)
  if [ -L "$1" ]; then echo L
  elif [ -d "$1" ]; then echo D
  elif [ -f "$1" ]; then sha_of "$1"
  elif [ -e "$1" ]; then echo O
  else echo -
  fi
}

unused_bak() { # path -> first free <path>.bak[.N]
  ub_b="$1.bak"
  ub_n=0
  while [ -e "$ub_b" ] || [ -L "$ub_b" ]; do
    ub_n=$((ub_n + 1))
    ub_b="$1.bak.$ub_n"
  done
  printf '%s\n' "$ub_b"
}

safe_rel() { # reject absolute paths, '..' components and tabs in a manifest/archive path
  case "$1" in
    ""|/*|..|../*|*/..|*/../*|*"$TAB"*|*"$NL"*) return 1 ;;
  esac
  return 0
}

manifest_get() { # key -> first value
  awk -F'\t' -v k="$1" '$1 == k { print $2; exit }' "$MANIFEST"
}

ensure_dir() { # absolute dir; records directories created at/under ROOT in $TMP/new.dirs
  if [ -d "$1" ]; then return 0; fi
  ensure_dir "$(dirname -- "$1")"
  mkdir -- "$1"
  case "$1" in
    "$ROOT") printf '.\n' >> "$TMP/new.dirs" ;;
    "$ROOT"/*) printf '%s\n' "${1#"$ROOT"/}" >> "$TMP/new.dirs" ;;
    *) printf '%s\n' "$1" >> "$TMP/new.xdirs" ;;   # ancestor of ROOT that we had to create (e.g. ~/.config)
  esac
}

fetch() { # url dest
  curl -fsSL --proto-redir '=https' --retry 2 -o "$2" "$1" </dev/null \
    || die "download failed: $1"
}

list_head() { # file [max] -> print up to max lines, then a "... and N more" line
  lh_max=${2:-40}
  lh_total=$(wc -l < "$1" | tr -d ' ')
  head -n "$lh_max" "$1" | while IFS= read -r lh_line; do say "    $lh_line"; done
  if [ "$lh_total" -gt "$lh_max" ]; then say "    ... and $((lh_total - lh_max)) more"; fi
}

write_jsonedit() { # writes the opencode.json editor to $TMP/jsonedit.py
  cat > "$TMP/jsonedit.py" <<'PYEOF'
# usage: jsonedit.py add|remove FILE ENTRY BACKUP_PATH   (env V1RUS_DRY=1: report only, write nothing)
# Prints exactly one status word. Never edits a file it cannot parse as plain JSON.
import json, os, re, shutil, sys
mode, path, entry, bak = sys.argv[1:5]
dry = os.environ.get("V1RUS_DRY") == "1"
real = os.path.realpath(path)  # keep dotfile-style symlinks intact: edit the target
if not os.path.exists(real):
    if mode == "add":
        if not dry:
            with open(real, "w", encoding="utf-8") as f:
                f.write(json.dumps({"instructions": [entry]}, indent=2) + "\n")
        print("created")
    else:
        print("absent")
    sys.exit(0)
try:
    with open(real, encoding="utf-8-sig") as f:
        raw = f.read()
    data = json.loads(raw)
except (ValueError, OSError):
    print("unparseable")
    sys.exit(0)
if not isinstance(data, dict):
    print("notobject")
    sys.exit(0)
ins = data.get("instructions")
if mode == "add":
    if ins is None:
        data["instructions"] = [entry]
    elif not isinstance(ins, list):
        print("notlist")
        sys.exit(0)
    elif entry in ins:
        print("present")
        sys.exit(0)
    else:
        ins.append(entry)
    status = "added"
else:
    if not isinstance(ins, list) or entry not in ins:
        print("absent")
        sys.exit(0)
    data["instructions"] = [x for x in ins if x != entry]
    if not data["instructions"]:
        del data["instructions"]
    status = "removed"
if not dry:
    shutil.copy2(real, bak)
    m = re.search(r'\n([ \t]+)"', raw)
    out = json.dumps(data, indent=m.group(1) if m else 2, ensure_ascii=False) + "\n"
    tmp = real + ".v1rus-tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(out)
    shutil.copymode(real, tmp)
    os.replace(tmp, real)
print(status)
PYEOF
}

json_edit() { # add|remove -> status word on stdout ("nopython" when python3 is missing)
  if ! command -v python3 >/dev/null 2>&1; then echo nopython; return 0; fi
  je_bak=$(unused_bak "$CONFIG")
  V1RUS_DRY=${JE_DRY:-0} python3 -I "$TMP/jsonedit.py" "$1" "$CONFIG" "$ENTRY" "$je_bak" </dev/null || echo error
}

manual_instruction() {
  warn "could not edit $CONFIG automatically ($1). Add this to its top-level \"instructions\" array yourself:"
  say "      \"$ENTRY\""
}

# ---------------------------------------------------------------- download + verify + stage

prepare_payload() {
  if [ -n "${V1RUS_RELEASE_BASE_URL:-}" ]; then BASE=${V1RUS_RELEASE_BASE_URL%/}; else BASE=$DEFAULT_BASE_URL; fi
  if [ "$VERSION" = latest ]; then
    URL="$BASE/latest/download/v1rus-opencode.tar.gz"
  else
    URL="$BASE/download/$VERSION/v1rus-opencode-$VERSION.tar.gz"
  fi
  say "Downloading $URL"
  fetch "$URL" "$TMP/archive.tar.gz"
  fetch "$URL.sha256" "$TMP/archive.sha256"
  want=$(awk 'NR == 1 { print tolower($1); exit }' "$TMP/archive.sha256")
  case "$want" in
    *[!0-9a-f]*|"") die "malformed checksum file: $URL.sha256" ;;
  esac
  if [ "${#want}" -ne 64 ]; then die "malformed checksum file: $URL.sha256"; fi
  have=$(sha_of "$TMP/archive.tar.gz")
  if [ "$have" != "$want" ]; then
    die "sha256 mismatch for $URL (expected $want, got $have); nothing was installed"
  fi
  say "sha256 OK ($have)"

  # Inspect before extracting: no absolute paths, no '..', no tabs/newlines in names.
  tar -tzf "$TMP/archive.tar.gz" > "$TMP/archive.list" </dev/null || die "cannot read the archive"
  while IFS= read -r entry; do
    safe_rel "$entry" || die "unsafe path in archive: $entry"
  done < "$TMP/archive.list"
  mkdir "$TMP/x"
  tar -xzf "$TMP/archive.tar.gz" -C "$TMP/x" </dev/null || die "cannot extract the archive"
  if [ -n "$(find "$TMP/x" ! -type f ! -type d)" ]; then die "archive contains links or special files"; fi
  if [ -n "$(find "$TMP/x" -name "*$NL*" -o -name "*$TAB*")" ]; then die "archive contains unsupported file names"; fi
  set -- "$TMP/x"/*
  if [ "$#" -ne 1 ] || [ ! -d "$1" ]; then die "unexpected archive layout (need a single top directory)"; fi
  TOP=$1
  [ -f "$TOP/VERSION" ] && [ -d "$TOP/files" ] || die "unexpected archive layout (VERSION or files/ missing)"
  REL_VERSION=$(head -n 1 "$TOP/VERSION")
  if [ "$VERSION" != latest ] && [ "$REL_VERSION" != "$VERSION" ]; then
    die "archive says version $REL_VERSION but $VERSION was requested"
  fi

  # Stage a copy and substitute the install root (escape \ & | for sed).
  STAGE="$TMP/stage"
  mkdir "$STAGE"
  cp -R "$TOP/files/." "$STAGE/"
  esc=$(printf '%s' "$ROOT" | sed -e 's/[\\&|]/\\&/g')
  find "$STAGE" -type f -exec grep -lF -- "$PLACEHOLDER" {} + 2>/dev/null > "$TMP/subst.list" || true
  while IFS= read -r f; do
    sed "s|$PLACEHOLDER|$esc|g" "$f" > "$f.v1rus-sub"
    mv -f "$f.v1rus-sub" "$f"
  done < "$TMP/subst.list"
  if [ -n "$(find "$STAGE" -type f -exec grep -lF -- "$PLACEHOLDER" {} + 2>/dev/null)" ]; then
    die "unsubstituted placeholder left in the payload"
  fi
  [ -f "$STAGE/v1rus/charter.md" ] || die "payload has no v1rus/charter.md"
}

# ---------------------------------------------------------------- install

do_install() {
  prepare_payload
  : > "$TMP/new.dirs"; : > "$TMP/new.xdirs"; : > "$TMP/old.xdirs"
  OLD_VERSION=""
  : > "$TMP/plan.in"
  : > "$TMP/old.files"; : > "$TMP/old.dirs"; : > "$TMP/old.backups"
  if [ -f "$MANIFEST" ]; then
    OLD_VERSION=$(manifest_get version)
    old_root=$(manifest_get root)
    if [ "$old_root" != "$ROOT" ]; then
      die "manifest at $MANIFEST belongs to a different root ($old_root); refusing to continue"
    fi
    while IFS="$TAB" read -r kind a b; do
      case "$kind" in
        file) safe_rel "$b" || die "corrupt manifest path: $b"; printf 'O\t%s\t%s\n' "$a" "$b" >> "$TMP/plan.in" ;;
        xdir) case "$a" in /*) printf '%s\n' "$a" >> "$TMP/old.xdirs" ;; *) die "corrupt manifest path: $a" ;; esac ;;
        dir) safe_rel "$a" || [ "$a" = "." ] || die "corrupt manifest path: $a"; printf '%s\n' "$a" >> "$TMP/old.dirs" ;;
        backup) safe_rel "$b" || die "corrupt manifest path: $b"; printf '%s\t%s\n' "$a" "$b" >> "$TMP/old.backups" ;;
      esac
    done < "$MANIFEST"
    say "Existing install found: ${OLD_VERSION:-unknown version} -> $REL_VERSION"
  fi

  (cd "$STAGE" && find . -type f | sed 's|^\./||' | LC_ALL=C sort) > "$TMP/new.rels"
  while IFS= read -r rel; do
    printf 'N\t%s\t%s\n' "$(sha_of "$STAGE/$rel")" "$rel" >> "$TMP/plan.in"
  done < "$TMP/new.rels"
  awk -F'\t' '$1 == "N" || $1 == "O" { print $3 }' "$TMP/plan.in" | LC_ALL=C sort -u > "$TMP/all.rels"
  while IFS= read -r rel; do
    printf 'C\t%s\t%s\n' "$(cur_hash "$ROOT/$rel")" "$rel" >> "$TMP/plan.in"
  done < "$TMP/all.rels"

  awk -F'\t' '
    $1 == "O" { old[$3] = $2; seen[$3] = 1 }
    $1 == "N" { new[$3] = $2; seen[$3] = 1 }
    $1 == "C" { cur[$3] = $2 }
    END {
      for (r in seen) {
        c = cur[r]
        if (r in new) {
          if (c == "-") a = "create"
          else if (c == "D" || c == "O") a = "error"
          else if (c == new[r]) a = ((r in old) ? "same" : "adopt")
          else if ((r in old) && c == old[r]) a = "update"
          else a = "conflict"
        } else {
          if (c == "-") a = "gone"
          else if (c == old[r]) a = "remove"
          else a = "conflict-remove"
        }
        print a "\t" r
      }
    }' "$TMP/plan.in" | LC_ALL=C sort > "$TMP/plan"

  count() { grep -c "^$1$TAB" "$TMP/plan" || true; }
  n_create=$(count create); n_update=$(count update); n_same=$(count same); n_adopt=$(count adopt)
  n_conflict=$(count conflict); n_remove=$(count remove); n_cremove=$(count conflict-remove); n_error=$(count error)
  grep "^error$TAB" "$TMP/plan" | cut -f2 > "$TMP/errors.list" || true
  if [ "$n_error" -gt 0 ]; then
    say "A directory exists where a file must be installed:"; list_head "$TMP/errors.list"
    die "resolve the paths above (under $ROOT) and run again"
  fi
  grep -E "^(conflict|conflict-remove)$TAB" "$TMP/plan" | cut -f2 > "$TMP/conflicts.list" || true
  n_conf_all=$((n_conflict + n_cremove))

  # opencode.json preview (never writes in dry mode)
  CONFIG_NOTE=""
  if [ -f "$ROOT/opencode.jsonc" ] && [ ! -e "$CONFIG" ] && [ ! -L "$CONFIG" ]; then
    CONFIG_STATUS=jsonc
  elif command -v python3 >/dev/null 2>&1; then
    JE_DRY=1
    CONFIG_STATUS=$(json_edit add)
    JE_DRY=0
  else
    CONFIG_STATUS=nopython
  fi

  say ""
  say "Target:  $ROOT"
  say "Version: $REL_VERSION"
  say "Files:   $n_create new, $n_update updated, $((n_same + n_adopt)) already identical, $n_remove obsolete removed"
  case "$CONFIG_STATUS" in
    created) say "Config:  $CONFIG would be created with the charter in \"instructions\"" ;;
    added) say "Config:  $CONFIG would get the charter added to \"instructions\" (backup: opencode.json.bak)" ;;
    present) say "Config:  $CONFIG already lists the charter; unchanged" ;;
    *) say "Config:  $CONFIG will NOT be edited automatically ($CONFIG_STATUS); a manual line will be printed" ;;
  esac
  if [ "$n_conf_all" -gt 0 ]; then
    say ""
    say "$n_conf_all file(s) exist and were NOT installed by v1rus (or were edited since); they would be saved as .bak and replaced:"
    list_head "$TMP/conflicts.list"
  fi

  if [ "$DRY" = 1 ]; then
    say ""
    say "Dry run: nothing was written to $ROOT."
    return 0
  fi

  if [ "$n_conf_all" -gt 0 ] && [ "$YES" != 1 ]; then
    if [ -t 0 ]; then
      printf 'Replace these files (originals saved as .bak)? [y/N] '
      read -r ans || ans=n
      case "$ans" in y|Y|yes|YES) ;; *) die "aborted; nothing was changed" ;; esac
    else
      say ""
      die "$n_conf_all conflicting file(s) and stdin is not a terminal. Nothing was changed. Review the list above (or run with --print), then re-run with --yes to back them up as .bak and continue."
    fi
  fi

  # ---- apply
  : > "$TMP/new.backups"
  while IFS="$TAB" read -r action rel; do
    dest="$ROOT/$rel"
    case "$action" in
      create|update|conflict)
        ensure_dir "$(dirname -- "$dest")"
        if [ "$action" = conflict ]; then
          bak=$(unused_bak "$dest")
          mv -- "$dest" "$bak"
          printf '%s\t%s\n' "${bak#"$ROOT"/}" "$rel" >> "$TMP/new.backups"
        fi
        cp -- "$STAGE/$rel" "$dest.v1rus-new"
        mv -f -- "$dest.v1rus-new" "$dest"
        ;;
      remove) rm -f -- "$dest" ;;
      conflict-remove) mv -- "$dest" "$(unused_bak "$dest")" ;;
    esac
  done < "$TMP/plan"

  # carry forward only backups of files that are still managed and still exist (earliest backup wins)
  { cat "$TMP/old.backups"; cat "$TMP/new.backups"; } | awk -F'\t' '!seen[$2]++' > "$TMP/all.backups"
  : > "$TMP/final.backups"
  while IFS="$TAB" read -r bak rel; do
    if [ -e "$ROOT/$bak" ] && grep -qxF -- "$rel" "$TMP/new.rels"; then printf '%s\t%s\n' "$bak" "$rel" >> "$TMP/final.backups"; fi
  done < "$TMP/all.backups"

  # directories: union of recorded ones, minus those that are now empty and removable
  cat "$TMP/old.dirs" "$TMP/new.dirs" | LC_ALL=C sort -u > "$TMP/dirs.all"
  : > "$TMP/dirs.final"
  LC_ALL=C sort -r "$TMP/dirs.all" | while IFS= read -r d; do
    if [ "$d" != "." ] && rmdir "$ROOT/$d" 2>/dev/null; then continue; fi
    if [ -d "$ROOT/$d" ]; then printf '%s\n' "$d" >> "$TMP/dirs.final"; fi
  done

  # ---- opencode.json
  M_INSTR=""; M_CREATED=""; M_CBAK=""; M_CSHA=""
  old_instr=""
  if [ -f "$MANIFEST" ]; then old_instr=$(manifest_get instruction); fi
  case "$CONFIG_STATUS" in
    jsonc|nopython|unparseable|notlist|notobject|error) manual_instruction "$CONFIG_STATUS" ;;
    *)
      ensure_dir "$ROOT"
      cfg_bak=$(unused_bak "$CONFIG")
      status=$(json_edit add)
      case "$status" in
        created) M_INSTR=$ENTRY; M_CREATED=1; M_CSHA=$(sha_of "$CONFIG") ;;
        added) M_INSTR=$ENTRY; M_CSHA=$(sha_of "$CONFIG"); if [ -f "$cfg_bak" ]; then M_CBAK=$cfg_bak; fi ;;
        present)
          if [ -n "$old_instr" ]; then
            M_INSTR=$old_instr; M_CREATED=$(manifest_get config-created); M_CBAK=$(manifest_get config-bak); M_CSHA=$(manifest_get config-sha)
          fi ;;
        *) manual_instruction "$status" ;;
      esac ;;
  esac

  # ---- manifest (written last; a failure before this point leaves files without a manifest)
  ensure_dir "$ROOT/v1rus"
  {
    printf '# v1rus OpenCode install manifest (managed by install.sh, do not edit)\n'
    printf 'version\t%s\nroot\t%s\n' "$REL_VERSION" "$ROOT"
    awk -F'\t' '$1 == "N" { print "file\t" $2 "\t" $3 }' "$TMP/plan.in"
    while IFS= read -r d; do printf 'dir\t%s\n' "$d"; done < "$TMP/dirs.final"
    cat "$TMP/old.xdirs" "$TMP/new.xdirs" | LC_ALL=C sort -u | while IFS= read -r d; do
      if [ -d "$d" ]; then printf 'xdir\t%s\n' "$d"; fi
    done
    while IFS="$TAB" read -r bak rel; do printf 'backup\t%s\t%s\n' "$bak" "$rel"; done < "$TMP/final.backups"
    if [ -n "$M_INSTR" ]; then printf 'instruction\t%s\n' "$M_INSTR"; fi
    if [ -n "$M_CREATED" ]; then printf 'config-created\t1\n'; fi
    if [ -n "$M_CBAK" ]; then printf 'config-bak\t%s\n' "$M_CBAK"; fi
    if [ -n "$M_CSHA" ]; then printf 'config-sha\t%s\n' "$M_CSHA"; fi
  } > "$MANIFEST.v1rus-new"
  mv -f -- "$MANIFEST.v1rus-new" "$MANIFEST"

  say ""
  say "Installed v1rus OpenCode artifacts $REL_VERSION into $ROOT"
  if [ "$n_conf_all" -gt 0 ]; then say "Replaced files were saved next to the originals as <name>.bak"; fi
  command -v python3 >/dev/null 2>&1 || warn "python3 not found on PATH: the v1rus hooks need it at runtime"
  say "Undo with: install.sh opencode --uninstall$( [ -n "$PROJECT" ] && printf ' --project %s' "$PROJECT")"
}

# ---------------------------------------------------------------- uninstall

do_uninstall() {
  [ -f "$MANIFEST" ] || die "no install manifest at $MANIFEST: nothing to uninstall (files are only removed when listed there)"
  old_root=$(manifest_get root)
  if [ "$old_root" != "$ROOT" ]; then die "manifest belongs to a different root ($old_root); refusing to continue"; fi
  ver=$(manifest_get version)
  say "Uninstalling v1rus OpenCode artifacts ${ver:-unknown version} from $ROOT"
  : > "$TMP/u.remove"; : > "$TMP/u.modified"; : > "$TMP/u.dirs"; : > "$TMP/u.backups"; : > "$TMP/u.xdirs"
  while IFS="$TAB" read -r kind a b; do
    case "$kind" in
      file)
        safe_rel "$b" || die "corrupt manifest path: $b"
        h=$(cur_hash "$ROOT/$b")
        if [ "$h" = "$a" ]; then printf '%s\n' "$b" >> "$TMP/u.remove"
        elif [ "$h" = "-" ] || [ "$h" = "D" ]; then :
        else printf '%s\n' "$b" >> "$TMP/u.modified"; fi ;;
      dir) printf '%s\n' "$a" >> "$TMP/u.dirs" ;;
      xdir) case "$a" in /*) printf '%s\n' "$a" >> "$TMP/u.xdirs" ;; esac ;;
      backup) safe_rel "$a" && safe_rel "$b" && printf '%s\t%s\n' "$a" "$b" >> "$TMP/u.backups" ;;
    esac
  done < "$MANIFEST"
  n_rm=$(wc -l < "$TMP/u.remove" | tr -d ' '); n_mod=$(wc -l < "$TMP/u.modified" | tr -d ' ')
  say "  $n_rm file(s) to remove, $n_mod edited since install (kept as .bak), $(wc -l < "$TMP/u.backups" | tr -d ' ') backup(s) to restore"
  if [ "$n_mod" -gt 0 ]; then list_head "$TMP/u.modified" 20; fi

  instr=$(manifest_get instruction)
  c_created=$(manifest_get config-created); c_bak=$(manifest_get config-bak); c_sha=$(manifest_get config-sha)
  if [ -n "$instr" ]; then ENTRY=$instr; say "  opencode.json: remove the \"$instr\" entry from \"instructions\""; fi
  if [ "$DRY" = 1 ]; then say "Dry run: nothing was changed."; return 0; fi

  while IFS= read -r rel; do rm -f -- "$ROOT/$rel"; done < "$TMP/u.remove"
  while IFS= read -r rel; do mv -- "$ROOT/$rel" "$(unused_bak "$ROOT/$rel")"; done < "$TMP/u.modified"
  while IFS="$TAB" read -r bak rel; do
    if [ -e "$ROOT/$bak" ] && [ ! -e "$ROOT/$rel" ] && [ ! -L "$ROOT/$rel" ]; then mv -- "$ROOT/$bak" "$ROOT/$rel"; fi
  done < "$TMP/u.backups"

  if [ -n "$instr" ]; then
    ch=$(cur_hash "$CONFIG")
    if [ -n "$c_sha" ] && [ "$ch" = "$c_sha" ] && [ "$c_created" = 1 ]; then
      rm -f -- "$CONFIG"
    elif [ -n "$c_sha" ] && [ "$ch" = "$c_sha" ] && [ -n "$c_bak" ] && [ -f "$c_bak" ]; then
      mv -f -- "$c_bak" "$CONFIG"   # untouched since install: restore the exact original bytes
    else
      status=$(json_edit remove)
      case "$status" in
        removed|absent) ;;
        *) manual_instruction "$status"; say "      (remove that line instead of adding it)" ;;
      esac
    fi
  fi

  rm -f -- "$MANIFEST"
  LC_ALL=C sort -ru "$TMP/u.dirs" | while IFS= read -r d; do
    if [ "$d" != "." ]; then rmdir "$ROOT/$d" 2>/dev/null || true; fi
  done
  if grep -qx '\.' "$TMP/u.dirs"; then rmdir "$ROOT" 2>/dev/null || true; fi
  LC_ALL=C sort -ru "$TMP/u.xdirs" | while IFS= read -r d; do rmdir "$d" 2>/dev/null || true; done
  say "Uninstalled. Files you edited were kept as <name>.bak."
}

# ---------------------------------------------------------------- main

main() {
  if [ "$#" -lt 1 ]; then usage >&2; exit 2; fi
  case "$1" in
    opencode) shift ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'install.sh: unknown target: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
  VERSION=latest; PROJECT=""; DRY=0; UNINSTALL=0; YES=0
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --version) [ "$#" -ge 2 ] || { usage >&2; exit 2; }; VERSION=$2; shift 2 ;;
      --version=*) VERSION=${1#--version=}; shift ;;
      --project) [ "$#" -ge 2 ] || { usage >&2; exit 2; }; PROJECT=$2; shift 2 ;;
      --project=*) PROJECT=${1#--project=}; shift ;;
      --print) DRY=1; shift ;;
      --uninstall) UNINSTALL=1; shift ;;
      --yes|-y) YES=1; shift ;;
      -h|--help) usage; exit 0 ;;
      *) printf 'install.sh: unknown option: %s\n' "$1" >&2; usage >&2; exit 2 ;;
    esac
  done
  case "$VERSION" in
    latest) ;;
    v[0-9]*) case "$VERSION" in *[!0-9A-Za-z._-]*) die "invalid --version: $VERSION" ;; esac ;;
    *) die "invalid --version: $VERSION (expected vX.Y.Z or latest)" ;;
  esac

  if [ -n "$PROJECT" ]; then
    [ -d "$PROJECT" ] || die "--project directory does not exist: $PROJECT"
    ROOT="$(cd "$PROJECT" && pwd)/.opencode"
  else
    cfg=${XDG_CONFIG_HOME:-}
    case "$cfg" in /*) ;; *) cfg="" ;; esac   # XDG: a relative XDG_CONFIG_HOME must be ignored
    if [ -z "$cfg" ]; then
      [ -n "${HOME:-}" ] || die "HOME is not set"
      cfg="$HOME/.config"
    fi
    ROOT="$cfg/opencode"
  fi
  case "$ROOT" in /*) ;; *) die "install root must be absolute: $ROOT" ;; esac
  case "$ROOT" in *"$NL"*|*"$TAB"*) die "install root contains a tab or newline" ;; esac
  CONFIG="$ROOT/opencode.json"
  MANIFEST="$ROOT/v1rus/.install-manifest"
  ENTRY="$ROOT/v1rus/charter.md"

  if [ "$UNINSTALL" != 1 ]; then
    command -v curl >/dev/null 2>&1 || die "curl is required"
    command -v tar >/dev/null 2>&1 || die "tar is required"
  fi
  TMP=$(mktemp -d "${TMPDIR:-/tmp}/v1rus-install.XXXXXX") || die "cannot create a temp directory"
  JE_DRY=0
  trap cleanup EXIT
  trap 'exit 1' INT TERM HUP
  write_jsonedit

  if [ "$UNINSTALL" = 1 ]; then do_uninstall; else do_install; fi
}

main "$@"
