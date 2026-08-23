#!/bin/bash
# ccgs-context.sh <script-name> — guarded wrapper for informational SessionStart hooks.
# Plugin fires in every workspace: skip unless this is a CCGS project.
# Plain-text stdout does not enter model context; wrap it into the protocol
# JSON so the content is injected as additionalContext.
DIR="$(cd "$(dirname "$0")" && pwd)"
[ -f ".zcode/docs/technical-preferences.md" ] || exit 0
out=$(bash "$DIR/$1" 2>/dev/null | tr -d '\r')
[ -z "$out" ] && exit 0
PYTHON_CMD=""
for cmd in python python3 py; do
    if command -v "$cmd" >/dev/null 2>&1; then
        PYTHON_CMD="$cmd"
        break
    fi
done
if [ -z "$PYTHON_CMD" ]; then
    printf '%s\n' "$out"
    exit 0
fi
printf '%s' "$out" | "$PYTHON_CMD" -c 'import json,sys
print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": sys.stdin.read()}}))'
