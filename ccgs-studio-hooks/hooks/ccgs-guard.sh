#!/bin/bash
# ccgs-guard.sh <script-name> — single entry for exit-code-based hooks.
# Plugin hooks fire in EVERY workspace of the user's machine; only proceed
# inside a CCGS project (marker file at workspace root), else exit 0 silently.
DIR="$(cd "$(dirname "$0")" && pwd)"
[ -f ".zcode/docs/technical-preferences.md" ] || exit 0
exec bash "$DIR/$1"
