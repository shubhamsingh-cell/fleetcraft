#!/usr/bin/env bash
# fleetcraft installer — copies skills/agents/hooks into ~/.claude/.
#
# Run this with --dry-run first. It prints exactly what would happen and
# changes nothing on disk:
#
#   scripts/install.sh --dry-run
#
# Then run for real:
#
#   scripts/install.sh
#
# What it does NOT do: it never touches ~/.claude/settings.json. Wiring a
# hook into an event is a one-line change to a file that also holds your
# other permissions, other hooks, and other settings — a script-driven
# merge into that file risks corrupting or silently overwriting config that
# has nothing to do with this repo. Instead, after copying hooks, this
# script prints the exact JSON you need to paste into settings.json
# yourself, and you decide where it goes.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." >/dev/null 2>&1 && pwd)"

CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"
SKILLS_DEST="$CLAUDE_DIR/skills"
AGENTS_DEST="$CLAUDE_DIR/agents"
HOOKS_DEST="$CLAUDE_DIR/hooks"

DRY_RUN=0
DO_SKILLS=1
DO_AGENTS=1
DO_HOOKS=1
TS="$(date +%Y%m%d-%H%M%S)"

# Tallies for the final summary. Plain indexed arrays only — this targets
# the bash 3.2 that ships as /bin/bash on macOS, which has no associative
# arrays.
INSTALLED=()
BACKED_UP=()
SKIPPED=()

usage() {
  cat <<'EOF'
Usage: scripts/install.sh [--dry-run] [--skills-only|--agents-only|--hooks-only] [-h|--help]

  --dry-run       Print exactly what would happen; write nothing. Run this first.
  --skills-only   Install only skills/*/ -> ~/.claude/skills/
  --agents-only   Install only agents/*.md -> ~/.claude/agents/
  --hooks-only    Install only hooks/*.py -> ~/.claude/hooks/
  -h, --help      Show this help.

With no selection flag, all three (skills, agents, hooks) are installed.
CLAUDE_DIR overrides the ~/.claude base directory (for testing).

Existing files/dirs that differ from what this repo ships are backed up to
<path>.bak.<timestamp> before being overwritten — never clobbered silently.
Identical existing files/dirs are left alone and reported as skipped.
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      ;;
    --skills-only)
      DO_SKILLS=1; DO_AGENTS=0; DO_HOOKS=0
      ;;
    --agents-only)
      DO_SKILLS=0; DO_AGENTS=1; DO_HOOKS=0
      ;;
    --hooks-only)
      DO_SKILLS=0; DO_AGENTS=0; DO_HOOKS=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "install.sh: unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
  shift
done

log() { printf '%s\n' "$*"; }
log_dry() { printf '  [dry-run] %s\n' "$*"; }

# Print a JSON string whose value is a shell-safe hook command. Claude Code's
# manual hook setting is a command string, so both the embedded path and the
# JSON representation must be quoted independently.
json_hook_command() {
  python3 - "$1" <<'PY'
import json
import shlex
import sys
print(json.dumps("python3 -B " + shlex.quote(sys.argv[1])))
PY
}

# backup_path DEST — print a non-existing backup path for this serial install.
# Check both normal paths and dangling symlinks. The suffix prevents a
# same-second reinstallation from overwriting an earlier backup; it is not a
# concurrency lock.
backup_path() {
  local dest candidate suffix
  dest="$1"
  candidate="${dest}.bak.${TS}"
  suffix=0
  while [ -e "$candidate" ] || [ -L "$candidate" ]; do
    suffix=$((suffix + 1))
    candidate="${dest}.bak.${TS}.${suffix}"
  done
  printf '%s' "$candidate"
}

# install_file SRC DEST — copy a single file into place, backing up an
# existing, differing DEST first. Never overwrites an identical DEST.
install_file() {
  local src dest bak
  src="$1"; dest="$2"
  if [ -e "$dest" ] || [ -L "$dest" ]; then
    if [ ! -L "$dest" ] && cmp -s -- "$src" "$dest"; then
      SKIPPED+=("$dest  (already up to date)")
      return
    fi
    bak="$(backup_path "$dest")"
    if [ "$DRY_RUN" -eq 1 ]; then
      log_dry "back up existing $dest -> $bak"
      log_dry "write $dest  (from ${src#"$REPO_ROOT"/})"
    else
      mv -- "$dest" "$bak"
      cp -- "$src" "$dest"
      BACKED_UP+=("$dest -> $bak")
    fi
    INSTALLED+=("$dest")
    return
  fi
  if [ "$DRY_RUN" -eq 1 ]; then
    log_dry "install $dest  (from ${src#"$REPO_ROOT"/})"
  else
    mkdir -p -- "$(dirname -- "$dest")"
    cp -- "$src" "$dest"
  fi
  INSTALLED+=("$dest")
}

# install_dir SRC_DIR DEST_DIR — copy a whole skill directory into place,
# backing up an existing, differing DEST_DIR first (whole-directory
# rename, not a per-file merge — a skill is one unit).
install_dir() {
  local src dest bak
  src="$1"; dest="$2"
  if [ -e "$dest" ] || [ -L "$dest" ]; then
    if [ ! -L "$dest" ] && diff -rq -- "$src" "$dest" >/dev/null 2>&1; then
      SKIPPED+=("$dest  (already up to date)")
      return
    fi
    bak="$(backup_path "$dest")"
    if [ "$DRY_RUN" -eq 1 ]; then
      log_dry "back up existing $dest -> $bak"
      log_dry "install $dest  (from ${src#"$REPO_ROOT"/}/)"
    else
      mv -- "$dest" "$bak"
      cp -R -- "$src" "$dest"
      BACKED_UP+=("$dest -> $bak")
    fi
    INSTALLED+=("$dest")
    return
  fi
  if [ "$DRY_RUN" -eq 1 ]; then
    log_dry "install $dest  (from ${src#"$REPO_ROOT"/}/)"
  else
    mkdir -p -- "$(dirname -- "$dest")"
    cp -R -- "$src" "$dest"
  fi
  INSTALLED+=("$dest")
}

# ---------------------------------------------------------------------------
# Skills — one directory per skill, discovered by glob (never hardcoded:
# the skill set changes independently of this script).
# ---------------------------------------------------------------------------
if [ "$DO_SKILLS" -eq 1 ]; then
  log "== skills -> $SKILLS_DEST =="
  shopt -s nullglob
  skill_dirs=("$REPO_ROOT"/skills/*/)
  shopt -u nullglob
  if [ "${#skill_dirs[@]}" -eq 0 ]; then
    log "  (no skills/ directories found in repo)"
  fi
  for skill_dir in "${skill_dirs[@]}"; do
    skill_dir="${skill_dir%/}"
    skill_name="$(basename -- "$skill_dir")"
    install_dir "$skill_dir" "$SKILLS_DEST/$skill_name"
  done
  log ""
fi

# ---------------------------------------------------------------------------
# Agents — one file per agent, discovered by glob.
# ---------------------------------------------------------------------------
if [ "$DO_AGENTS" -eq 1 ]; then
  log "== agents -> $AGENTS_DEST =="
  shopt -s nullglob
  agent_files=("$REPO_ROOT"/agents/*.md)
  shopt -u nullglob
  if [ "${#agent_files[@]}" -eq 0 ]; then
    log "  (no agents/*.md found in repo)"
  fi
  for agent_file in "${agent_files[@]}"; do
    install_file "$agent_file" "$AGENTS_DEST/$(basename -- "$agent_file")"
  done
  log ""
fi

# ---------------------------------------------------------------------------
# Hooks — one file per hook, discovered by glob. hooks/README.md is not a
# .py file so the glob already skips it.
# ---------------------------------------------------------------------------
HOOK_FILES=()
if [ "$DO_HOOKS" -eq 1 ]; then
  log "== hooks -> $HOOKS_DEST =="
  shopt -s nullglob
  HOOK_FILES=("$REPO_ROOT"/hooks/*.py)
  shopt -u nullglob
  if [ "${#HOOK_FILES[@]}" -eq 0 ]; then
    log "  (no hooks/*.py found in repo)"
  fi
  for hook_file in "${HOOK_FILES[@]}"; do
    dest="$HOOKS_DEST/$(basename -- "$hook_file")"
    install_file "$hook_file" "$dest"
    if [ "$DRY_RUN" -eq 1 ]; then
      log_dry "chmod +x $dest"
    else
      # BSD chmod (macOS /bin/chmod) does not understand a `--`
      # end-of-options marker the way GNU chmod and the rest of this
      # script's commands do, so this one call deliberately omits it.
      # $dest is always built from $HOOKS_DEST (absolute), never user
      # input, so it can't start with a `-` that chmod would misparse.
      chmod +x "$dest"
    fi
  done
  log ""
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
log "== summary =="
if [ "$DRY_RUN" -eq 1 ]; then
  log "(dry run — nothing was written)"
fi
if [ "${#INSTALLED[@]}" -eq 0 ]; then
  log "installed:  (none)"
else
  log "installed:"
  for p in "${INSTALLED[@]}"; do log "  $p"; done
fi
if [ "${#BACKED_UP[@]}" -eq 0 ]; then
  log "backed up:  (none)"
else
  log "backed up:"
  for p in "${BACKED_UP[@]}"; do log "  $p"; done
fi
if [ "${#SKIPPED[@]}" -eq 0 ]; then
  log "skipped:    (none)"
else
  log "skipped (already up to date):"
  for p in "${SKIPPED[@]}"; do log "  $p"; done
fi
log ""

# ---------------------------------------------------------------------------
# settings.json wiring block — printed, never written. Each hook's event
# (and, for PreToolUse/PostToolUse, its matcher) is detected from the hook
# file's own docstring/emitted JSON rather than hardcoded here, so this
# stays correct as hooks are added, renamed, or re-targeted.
# ---------------------------------------------------------------------------
if [ "$DO_HOOKS" -eq 1 ] && [ "${#HOOK_FILES[@]}" -gt 0 ]; then
  KNOWN_EVENTS='SessionStart PreToolUse PostToolUse PostToolBatch TaskCompleted UserPromptSubmit SubagentStart SubagentStop PreCompact Notification Stop'

  detect_event_and_matcher() {
    # Sets HOOK_EVENT / HOOK_MATCHER (HOOK_MATCHER may be empty) from a
    # hook source file. Three tiers, each covering a shape actually used
    # in this repo's hooks as of this writing:
    #   1. A docstring header written as "(EventName / matcher)" or
    #      "(EventName)" — covers hooks that name their own event inline.
    #   2. A `"hookEventName": "EventName"` string in the hook's own
    #      emitted JSON — covers hooks that don't, but do emit standard
    #      hookSpecificOutput.
    #   3. A bare known-event keyword anywhere in the first 20 lines —
    #      last resort for a hook (e.g. a Stop-hook using the plain
    #      {"decision": ...} shape) that does neither of the above.
    # NOTE: every scratch var here is `local` on purpose — the caller below
    # also runs a `for ev in $KNOWN_EVENTS` loop, and this function's own
    # tier-3 fallback loop reuses the name `ev`. Bash gives `for` loop
    # variables no implicit scoping, so without `local` the fallback loop
    # here silently clobbers the caller's loop variable mid-iteration.
    local f paren inner field head_text ev
    f="$1"
    HOOK_EVENT=""
    HOOK_MATCHER=""

    # Hooks that delegate JSON formatting to fleet_hook_utils do not carry
    # hookEventName literally. Keep this small registry explicit so the
    # printed manual configuration remains complete as well as quoted.
    case "$(basename -- "$f")" in
      evidence-batch.py) HOOK_EVENT="PostToolBatch"; return ;;
      agent-telemetry.py) HOOK_EVENT="PostToolUse"; HOOK_MATCHER="Agent"; return ;;
      completion-gate.py) HOOK_EVENT="TaskCompleted"; return ;;
      fleet-delegation-guard.py) HOOK_EVENT="PreToolUse"; HOOK_MATCHER="Bash|PowerShell"; return ;;
    esac

    paren="$(grep -m1 -oE '\((SessionStart|PreToolUse|PostToolUse|UserPromptSubmit|SubagentStart|SubagentStop|PreCompact|Notification|Stop)[^)]*\)' -- "$f" 2>/dev/null || true)"
    if [ -n "$paren" ]; then
      inner="${paren#\(}"
      inner="${inner%\)}"
      case "$inner" in
        */*)
          HOOK_EVENT="$(printf '%s' "${inner%%/*}" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')"
          HOOK_MATCHER="$(printf '%s' "${inner#*/}" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')"
          ;;
        *)
          HOOK_EVENT="$(printf '%s' "$inner" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')"
          ;;
      esac
      return
    fi

    field="$(grep -m1 -oE '"hookEventName"[[:space:]]*:[[:space:]]*"[A-Za-z]+"' -- "$f" 2>/dev/null || true)"
    if [ -n "$field" ]; then
      HOOK_EVENT="$(printf '%s' "$field" | grep -oE '"[A-Za-z]+"$' | tr -d '"')"
      return
    fi

    head_text="$(head -20 -- "$f")"
    for ev in $KNOWN_EVENTS; do
      if printf '%s\n' "$head_text" | grep -qE "\\b${ev}\\b"; then
        HOOK_EVENT="$ev"
        return
      fi
    done
  }

  echo "------------------------------------------------------------------"
  echo "Hooks were copied to $HOOKS_DEST, but this script will NOT touch"
  echo "$CLAUDE_DIR/settings.json. Paste the block(s) below into its"
  echo "\"hooks\" object yourself (merge by event key if you already have"
  echo "other hooks registered there) — a script-driven merge into a file"
  echo "that also holds your other permissions and settings is exactly"
  echo "the kind of edit that should stay a human decision."
  echo "------------------------------------------------------------------"
  echo

  for ev in $KNOWN_EVENTS; do
    ev_has_hook=0
    for hook_file in "${HOOK_FILES[@]}"; do
      detect_event_and_matcher "$hook_file"
      if [ "$HOOK_EVENT" = "$ev" ]; then
        ev_has_hook=1
        break
      fi
    done
    [ "$ev_has_hook" -eq 1 ] || continue

    echo "\"$ev\": ["
    first=1
    for hook_file in "${HOOK_FILES[@]}"; do
      detect_event_and_matcher "$hook_file"
      [ "$HOOK_EVENT" = "$ev" ] || continue
      name="$(basename -- "$hook_file")"
      if [ "$first" -eq 0 ]; then
        echo "  ,"
      fi
      first=0
      matcher_display="$HOOK_MATCHER"
      command_json="$(json_hook_command "$HOOKS_DEST/$name")"
      echo "  {"
      echo "    \"matcher\": \"$matcher_display\","
      echo "    \"hooks\": ["
      echo "      {"
      echo "        \"type\": \"command\","
      echo "        \"command\": $command_json,"
      echo "        \"timeout\": 10"
      echo "      }"
      echo "    ]"
      echo "  }"
    done
    echo "],"
    echo
  done
  echo "(Wrap the block(s) above in the top-level {\"hooks\": { ... }} object"
  echo "if you don't already have one, and drop the trailing comma after"
  echo "the last event key.)"
fi
