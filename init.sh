#!/usr/bin/env bash
# init.sh — ZCode Game Studios anti-compression anchor (static instructions only)
#
# One-time (re-runnable) initializer that injects a managed block into AGENTS.md.
# The full orchestrator `.zcode/skills/auto-game-in-sleep/SKILL.md` is ~650 lines
# and 32 steps — it routinely spans multiple context compactions. Conversation
# history WILL be partially forgotten, but AGENTS.md is re-injected every session
# and after every compaction (new-conversation mode), so this block is the only
# text guaranteed to survive.
#
# Invariant: AGENTS.md is STATIC. It holds recovery instructions and pointers,
# never live state values. Live state lives in:
#   production/auto-game-in-sleep/state.json   (machine truth)
#   production/auto-game-in-sleep/journal.md   (human-readable, self-contained)
# The skill's heartbeat discipline keeps state.json current; the anchored
# Recovery Protocol tells a resumed session where to find it.
#
# What it does:
#   - Creates or updates a single managed block in AGENTS.md:
#       <!-- ZCGS:BEGIN --> ... <!-- ZCGS:END -->
#   - The block contains:
#       (a) State pointer — where the live run state lives (state.json/journal.md)
#           and which spec to re-read (SKILL.md + workflow-catalog.yaml)
#       (b) 5-step Recovery Protocol the resumed agent must run immediately
#           after compaction / new conversation (step 1 is re-reading the skill)
#       (c) The rule override that auto-game-in-sleep suspends the
#           Question -> Options -> Decision -> Draft -> Approval gate
#   - Idempotent, compare-and-swap, and safe to rerun. No other files are touched.
#
# Usage:
#   bash init.sh                # inject or refresh the managed block
#   bash init.sh --check        # verify block exists and print status
#   bash init.sh --revert       # remove the managed block
#   bash init.sh --dry-run      # show what would change, write nothing
#   bash init.sh --help         # show help
#
# Design notes (mirrors Auto-claude-code-research-in-sleep/tools/install_aris.sh):
#   - If AGENTS.md already contains the block, replace exactly that range (DOTALL).
#     Multiple blocks -> warn and skip (manual fix required).
#   - Otherwise append at EOF with a separating newline.
#   - Write via temp file + atomic mv in the same directory; re-read AGENTS.md
#     before mv to detect concurrent edits (compare-and-swap, best-effort).
#   - Prefers a working python for the regex replace; falls back to perl, then
#     aborts with a clear message if neither is available (avoids broken sed on
#     Windows Git Bash). Windows' `python3` shim (WindowsApps) reports `command -v`
#     success but exits 49 when invoked as `python3 -`, so we probe candidates.

set -euo pipefail

DOC_FILE_NAME="AGENTS.md"
BLOCK_BEGIN="<!-- ZCGS:BEGIN -->"
BLOCK_END="<!-- ZCGS:END -->"

PROJECT_ROOT=""
DRY_RUN=false
ACTION="apply"  # apply | check | revert

log()  { printf '%s\n' "$*"; }
warn() { printf 'warning: %s\n' "$*" >&2; }
die()  { printf 'error: %s\n' "$*" >&2; exit 1; }

# Portable python resolver — probe that stdin+args mode actually works.
_py_probe_stdin_args() { printf 'import sys; sys.exit(0)\n' | "$1" - "a" "b" >/dev/null 2>&1; }
_find_working_python() {
  local c
  for c in python3 python py; do
    if command -v "$c" >/dev/null 2>&1 && _py_probe_stdin_args "$c"; then
      if "$c" -c "import re, pathlib" >/dev/null 2>&1; then printf '%s' "$c"; return 0; fi
    fi
  done
  for c in "/d/anaconda3/python" "/d/anaconda3/python.exe" "/c/anaconda3/python.exe"; do
    if [[ -x "$c" ]] && "$c" -c "import re, pathlib" >/dev/null 2>&1; then printf '%s' "$c"; return 0; fi
  done
  return 1
}

usage() {
  sed -n '2,44p' "$0" | sed 's/^# \?//'
}

# ── args ───────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)  DRY_RUN=true; shift ;;
    --check)    ACTION="check"; shift ;;
    --revert)   ACTION="revert"; shift ;;
    -h|--help)  usage; exit 0 ;;
    --) shift; break ;;
    -*) die "unknown option: $1 (see --help)" ;;
    *)  # positional = project path (optional, for parity with install_aris.sh)
        if [[ -z "$PROJECT_ROOT" ]]; then PROJECT_ROOT="$1"; shift
        else die "unexpected positional: $1"; fi
        ;;
  esac
done

# ── resolve project root ──────────────────────────────────────────────────
if [[ -z "$PROJECT_ROOT" ]]; then
  _script_dir="$(cd "$(dirname "$0")" 2>/dev/null && pwd || pwd)"
  if [[ -f "$_script_dir/$DOC_FILE_NAME" ]]; then PROJECT_ROOT="$_script_dir"
  else PROJECT_ROOT="$(pwd)"
  fi
fi
PROJECT_ROOT="$(cd "$PROJECT_ROOT" 2>/dev/null && pwd)" || die "project path not found: $PROJECT_ROOT"
DOC_FILE="$PROJECT_ROOT/$DOC_FILE_NAME"

# ── helpers ───────────────────────────────────────────────────────────────
has_block() { grep -qF "$BLOCK_BEGIN" "$1" 2>/dev/null; }

count_blocks() { grep -cF "$BLOCK_BEGIN" "$1" 2>/dev/null || true; }

build_block() {
  local now
  now="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date)"
  cat <<EOF
$BLOCK_BEGIN
## ZCGS Orchestrator — Anti-Compression Anchor

> Managed by \`bash init.sh\`. Do not edit this block manually — rerun \`bash init.sh\` to refresh.
> This block is STATIC — it holds instructions and pointers, never live state values.

### State Pointer (live state lives here — this block never holds stale values)

- Run state (machine truth): \`production/auto-game-in-sleep/state.json\`
  - If it does not exist, the run has not started — create it per the skill's heartbeat discipline (see below).
- Human-readable log: \`production/auto-game-in-sleep/journal.md\` (self-contained, last 50 lines are enough to resume)
- Decision audit trail: \`production/auto-game-in-sleep/decisions.md\`
- Test evidence packs: \`production/auto-game-in-sleep/test-runs/\`
- Orchestrator: invoke the \`/auto-game-in-sleep\` skill (the full pipeline spec lives there)
- Pipeline catalog: \`.zcode/docs/workflow-catalog.yaml\`
- This block does NOT contain \`state\` / \`current_phase\` / \`last_seen\` — those live only in \`state.json\`.

### Recovery Protocol (run immediately after compaction or new conversation)

1. **Resume the orchestrator.** Your conversation history has been summarized. Invoke the \`/auto-game-in-sleep\` skill via the Skill tool NOW, before any other action. Do NOT rely on your summary's memory of the pipeline — the steps, behavior rules, and acceptance definitions live in the skill.
2. Read \`production/auto-game-in-sleep/state.json\` — \`status\`, \`current_phase\`, \`current_step\`, \`iterations\`, \`stale_count\`, \`blocked\`, \`steps[]\`. If the file does not exist, the run has not started; follow the skill's Phase 0 to create it.
3. Read \`production/auto-game-in-sleep/journal.md\` (last 50 lines) — self-contained progress; also scan \`decisions.md\` for recent overrides.
4. If \`state.json\` \`status == "running"\`: resume the pipeline at the first \`steps[]\` entry whose \`status != "accepted"\` (re-verify any \`done\` without evidence). Follow the orchestrator skill, step-by-step. Do not stop for user questions.
5. Heartbeat discipline: at the START of every pipeline step, update \`state.json\` \`last_seen\`/\`current_phase\`/\`current_step\` and append a self-contained entry to \`journal.md\` before any long or crash-prone work — so the next compaction finds the true position in the state file, not in this AGENTS.md block.

### Rules while the orchestrator is active

- The Decision Protocol in \`auto-game-in-sleep\` suspends the \`Question -> Options -> Decision -> Draft -> Approval\` gate in \`AGENTS.md#Collaboration Protocol\`. Decisions are made autonomously and appended to \`decisions.md\` (template: Context / Options / Chose / Override).
- Never mark a step \`accepted\` without evidence (review report / test record / catalog artifact — see skill § Phase 0 / Steps definition).
- \`journal.md\` entries must be self-contained (what was attempted, what is next, which paths matter) so a compacted session can resume from the journal alone.
- This block coexists with \`production/session-state/active.md\` (\`.zcode/docs/context-management.md\`); that file tracks interactive work, while this block tracks the unattended orchestrator.
- Invoke pipeline skills via the Skill tool (\`/setup-engine\`, \`/design-system\`, ...); reading a SKILL.md with Read is for inspection only and never substitutes for invocation. Do not re-implement a skill's workflow by hand from its prose.

<!-- initialized: $now — rerun bash init.sh to refresh -->
$BLOCK_END
EOF
}

# ── check mode ────────────────────────────────────────────────────────────
if [[ "$ACTION" == "check" ]]; then
  if [[ ! -f "$DOC_FILE" ]]; then
    log "AGENTS.md not found at $DOC_FILE"
    exit 1
  fi
  if has_block "$DOC_FILE"; then
    n="$(count_blocks "$DOC_FILE")"
    log "AGENTS.md: managed block present ($n occurrence(s)) at $DOC_FILE"
    sed -n "/$(printf '%s' "$BLOCK_BEGIN" | sed 's/[.*[\^$]/\\&/g')/,/$(printf '%s' "$BLOCK_END" | sed 's/[.*[\^$]/\\&/g')/p" "$DOC_FILE" | head -n 40
    if [[ "$n" -gt 1 ]]; then warn "multiple blocks found — rerun without --check to reconcile is not supported; remove duplicates manually"; exit 1; fi
    exit 0
  else
    log "AGENTS.md: managed block NOT present at $DOC_FILE"
    log "Run: bash init.sh"
    exit 1
  fi
fi

# ── revert mode ───────────────────────────────────────────────────────────
if [[ "$ACTION" == "revert" ]]; then
  if [[ ! -f "$DOC_FILE" ]]; then die "AGENTS.md not found at $DOC_FILE"; fi
  if ! has_block "$DOC_FILE"; then log "No managed block to remove."; exit 0; fi
  n="$(count_blocks "$DOC_FILE")"
  if [[ "$n" -gt 1 ]]; then die "multiple blocks found ($n) — remove duplicates manually before --revert"; fi
  original="$(cat "$DOC_FILE")"
  if _PY="$( _find_working_python )"; then
    new_content="$("$_PY" - "$DOC_FILE" "$BLOCK_BEGIN" "$BLOCK_END" <<'PYEOF'
import re, sys, pathlib
path, begin, end = sys.argv[1], sys.argv[2], sys.argv[3]
text = pathlib.Path(path).read_text(encoding="utf-8", errors="replace")
pat = re.compile(re.escape(begin) + r".*?" + re.escape(end) + r"\n?", re.DOTALL)
new = pat.sub("", text)
new = re.sub(r"\n{3,}", "\n\n", new)
sys.stdout.write(new)
PYEOF
    )" || die "revert failed (python error: $_PY)"
  elif command -v perl >/dev/null 2>&1; then
    new_content="$(perl -0777 -pe 'BEGIN{$b=shift;$e=shift} s/\Q$b\E.*?\Q$e\E\n?//s; s/\n{3,}/\n\n/g' "$BLOCK_BEGIN" "$BLOCK_END" "$DOC_FILE")" || die "revert failed (perl error)"
  else
    die "python or perl required for --revert (neither found)"
  fi
  if $DRY_RUN; then
    log "(dry-run) would remove managed block from $DOC_FILE"
    exit 0
  fi
  tmp="$DOC_FILE.zcgs-tmp.$$"
  printf '%s' "$new_content" > "$tmp"
  current="$(cat "$DOC_FILE")"
  if [[ "$current" != "$original" ]]; then rm -f "$tmp"; warn "AGENTS.md changed during revert — aborting (rerun to retry)"; exit 1; fi
  mv -f "$tmp" "$DOC_FILE"
  log "Removed managed block from $DOC_FILE"
  exit 0
fi

# ── apply mode (default) ──────────────────────────────────────────────────
if [[ ! -f "$DOC_FILE" ]]; then
  if $DRY_RUN; then
    log "(dry-run) would create $DOC_FILE with managed block"
    exit 0
  fi
  warn "AGENTS.md not found — creating minimal scaffold at $DOC_FILE"
  cat > "$DOC_FILE" <<'AGENTSEOF'
# ZCode Game Studios -- Game Studio Agent Architecture

Indie game development managed through 49 coordinated subagents
(defined in `.zcode/agents/`).

AGENTSEOF
fi

original="$(cat "$DOC_FILE")"
new_block="$(build_block)"

if has_block "$DOC_FILE"; then
  n="$(count_blocks "$DOC_FILE")"
  if [[ "$n" -gt 1 ]]; then
    die "multiple managed blocks found ($n) in $DOC_FILE — remove duplicates manually before rerunning"
  fi
  if _PY="$( _find_working_python )"; then
    new_content="$("$_PY" - "$DOC_FILE" "$BLOCK_BEGIN" "$BLOCK_END" "$new_block" <<'PYEOF'
import re, sys, pathlib
path, begin, end, body = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
text = pathlib.Path(path).read_text(encoding="utf-8", errors="replace")
pat = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.DOTALL)
m = pat.findall(text)
if len(m) > 1:
    sys.stderr.write("multiple blocks found\n")
    sys.exit(2)
sys.stdout.write(pat.sub(body, text))
PYEOF
    )" || die "AGENTS.md update failed (python error: $_PY — see above)"
  elif command -v perl >/dev/null 2>&1; then
    new_content="$(perl -0777 -pe 'BEGIN{$b=shift;$e=shift;$body=shift} s/\Q$b\E.*?\Q$e\E/$body/s' "$BLOCK_BEGIN" "$BLOCK_END" "$new_block" "$DOC_FILE")" || die "AGENTS.md update failed (perl error)"
  else
    die "python or perl required to update existing managed block (neither found)"
  fi
else
  new_content="$original"
  case "$new_content" in
    *$'\n') ;;
    *) new_content="${new_content}"$'\n' ;;
  esac
  if [[ -n "$original" ]]; then
    new_content="${new_content}"$'\n'
  fi
  new_content="${new_content}${new_block}"$'\n'
fi

if [[ "$new_content" == "$original" ]]; then
  log "AGENTS.md already up to date at $DOC_FILE"
  exit 0
fi

if $DRY_RUN; then
  log "(dry-run) would update $DOC_FILE"
  if has_block "$DOC_FILE"; then log "  -> refresh existing managed block"
  else log "  -> append new managed block"
  fi
  log "  (rerun without --dry-run to apply)"
  exit 0
fi

tmp="$DOC_FILE.zcgs-tmp.$$"
printf '%s' "$new_content" > "$tmp"
current="$(cat "$DOC_FILE")"
if [[ "$current" != "$original" ]]; then
  rm -f "$tmp"
  warn "AGENTS.md changed during init — skipping write (rerun bash init.sh to retry)"
  exit 1
fi
mv -f "$tmp" "$DOC_FILE"
log "Updated $DOC_FILE (managed block <!-- ZCGS:BEGIN -->..<!-- ZCGS:END -->)"
log "Next: run your pipeline (e.g. /auto-game-in-sleep) — compaction resumes from state.json via this anchor."
