#!/bin/bash
# validate-dangerous.sh — restores the reference project's settings.json deny
# rules as a PreToolUse hook (matcher: Bash|Read). Exit 2 = deny with reason.
#
# Blocked patterns (mirroring the original permission deny list):
#   Bash:   rm -rf (any -r/-f combo), git push --force/-f, git reset --hard,
#           git clean -f*, sudo, chmod 777, redirect/write .env, cat/type .env
#   Read:   any .env / secrets file path

INPUT=$(cat)

# Parse fields -- jq first, grep fallback (project convention)
if command -v jq >/dev/null 2>&1; then
    TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
    COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
    FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
else
    TOOL_NAME=$(echo "$INPUT" | grep -oE '"tool_name"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*: *"//;s/"$//')
    COMMAND=$(echo "$INPUT" | grep -oE '"command"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*: *"//;s/"$//')
    FILE_PATH=$(echo "$INPUT" | grep -oE '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*: *"//;s/"$//')
fi

deny() {
    echo "BLOCKED by CCGS safety rules: $1" >&2
    exit 2
}

# --- Read tool: never open env/secret files (reference: Read(**/.env*)) ---
if [ "$TOOL_NAME" = "Read" ]; then
    if [ -n "$FILE_PATH" ]; then
        case "$FILE_PATH" in
            */.env|*/.env/*|*.env|*.env.*)
                deny "reading env/secrets file: $FILE_PATH"
                ;;
        esac
    fi
    exit 0
fi

[ -z "$COMMAND" ] && exit 0

# --- Bash: deny list (reference settings.json) ---
echo "$COMMAND" | grep -qE 'rm[[:space:]]+-[[:alnum:]]*[rf][[:alnum:]]*[rf][[:alnum:]]*([[:space:]]|$)' \
    && deny "recursive force delete (rm -rf)"

echo "$COMMAND" | grep -qE 'git[[:space:]]+push[[:space:]][^|;&]*(--force|[[:space:]]-f([[:space:]]|$))' \
    && deny "force push (git push --force)"

echo "$COMMAND" | grep -qE 'git[[:space:]]+reset[[:space:]][^|;&]*--hard' \
    && deny "destructive history reset (git reset --hard)"

echo "$COMMAND" | grep -qE 'git[[:space:]]+clean[[:space:]][^|;&]*-f' \
    && deny "force untracked cleanup (git clean -f)"

echo "$COMMAND" | grep -qE '(^|[|;&[:space:]])sudo[[:space:]]' \
    && deny "superuser execution (sudo)"

echo "$COMMAND" | grep -qE 'chmod[[:space:]]+([^|;&]*[[:space:]])?777([[:space:]]|$)' \
    && deny "world-writable permissions (chmod 777)"

echo "$COMMAND" | grep -qE '>+[[:space:]]*[^|;&]*\.env|cat[[:space:]][^|;&]*\.env|type[[:space:]][^|;&]*\.env' \
    && deny "env/secrets file access"

exit 0
