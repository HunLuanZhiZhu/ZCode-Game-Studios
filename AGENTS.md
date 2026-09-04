# ZCode Game Studios -- Game Studio Agent Architecture

Indie game development managed through 49 coordinated subagents
(defined in `.zcode/agents/`). Each agent owns a specific domain,
enforcing separation of concerns and quality.

## Technology Stack

- **Engine**: [CHOOSE: Godot 4 / Unity / Unreal Engine 5]
- **Language**: [CHOOSE: GDScript / C# / C++ / Blueprint]
- **Version Control**: Git with trunk-based development
- **Build System**: [SPECIFY after choosing engine]
- **Asset Pipeline**: [SPECIFY after choosing engine]

> **Note**: Engine-specialist agents exist for Godot, Unity, and Unreal with
> dedicated sub-specialists. Use the set matching your engine.

## Project Structure

@.zcode/docs/directory-structure.md

## Engine Version Reference

@docs/engine-reference/godot/VERSION.md

## Technical Preferences

@.zcode/docs/technical-preferences.md

## Coordination Rules

@.zcode/docs/coordination-rules.md

## Collaboration Protocol

**User-driven collaboration, not autonomous execution.**
Every task follows: **Question -> Options -> Decision -> Draft -> Approval**

- Agents MUST ask "May I write this to [filepath]?" before using Write/Edit tools
- Agents MUST show drafts or summaries before requesting approval
- Multi-file changes require explicit approval for the full changeset
- No commits without user instruction

See `docs/COLLABORATIVE-DESIGN-PRINCIPLE.md` for full protocol and examples.

> **First session?** If the project has no engine configured and no game concept,
> run `/start` to begin the guided onboarding flow.

## Coding Standards

@.zcode/docs/coding-standards.md
Path-scoped rules live in `.zcode/rules/`.

## Context Management

@.zcode/docs/context-management.md

<!-- ZCGS:BEGIN -->
## ZCGS Orchestrator — Anti-Compression Anchor

> Managed by `bash init.sh`. Do not edit this block manually — rerun `bash init.sh` to refresh.
> This block is STATIC — it holds instructions and pointers, never live state values.

### State Pointer (live state lives here — this block never holds stale values)

- Run state (machine truth): `production/auto-game-in-sleep/state.json`
  - If it does not exist, the run has not started — create it per the skill's heartbeat discipline (see below).
- Human-readable log: `production/auto-game-in-sleep/journal.md` (self-contained, last 50 lines are enough to resume)
- Decision audit trail: `production/auto-game-in-sleep/decisions.md`
- Test evidence packs: `production/auto-game-in-sleep/test-runs/`
- Orchestrator: invoke the `/auto-game-in-sleep` skill (the full pipeline spec lives there)
- Pipeline catalog: `.zcode/docs/workflow-catalog.yaml`
- This block does NOT contain `state` / `current_phase` / `last_seen` — those live only in `state.json`.

### Recovery Protocol (run immediately after compaction or new conversation)

1. **Resume the orchestrator.** Your conversation history has been summarized. Invoke the `/auto-game-in-sleep` skill via the Skill tool NOW, before any other action. Do NOT rely on your summary's memory of the pipeline — the steps, behavior rules, and acceptance definitions live in the skill.
2. Read `production/auto-game-in-sleep/state.json` — `status`, `current_phase`, `current_step`, `iterations`, `stale_count`, `blocked`, `steps[]`. If the file does not exist, the run has not started; follow the skill's Phase 0 to create it.
3. Read `production/auto-game-in-sleep/journal.md` (last 50 lines) — self-contained progress; also scan `decisions.md` for recent overrides.
4. If `state.json` `status == "running"`: resume the pipeline at the first `steps[]` entry whose `status != "accepted"` (re-verify any `done` without evidence). Follow the orchestrator skill, step-by-step. Do not stop for user questions.
5. Heartbeat discipline: at the START of every pipeline step, update `state.json` `last_seen`/`current_phase`/`current_step` and append a self-contained entry to `journal.md` before any long or crash-prone work — so the next compaction finds the true position in the state file, not in this AGENTS.md block.

### Rules while the orchestrator is active

- The Decision Protocol in `auto-game-in-sleep` suspends the `Question -> Options -> Decision -> Draft -> Approval` gate in `AGENTS.md#Collaboration Protocol`. Decisions are made autonomously and appended to `decisions.md` (template: Context / Options / Chose / Override).
- Never mark a step `accepted` without evidence (review report / test record / catalog artifact — see skill § Phase 0 / Steps definition).
- `journal.md` entries must be self-contained (what was attempted, what is next, which paths matter) so a compacted session can resume from the journal alone.
- This block coexists with `production/session-state/active.md` (`.zcode/docs/context-management.md`); that file tracks interactive work, while this block tracks the unattended orchestrator.
- Invoke pipeline skills via the Skill tool (`/setup-engine`, `/design-system`, ...); reading a SKILL.md with Read is for inspection only and never substitutes for invocation. Do not re-implement a skill's workflow by hand from its prose.

<!-- initialized: 2026-09-04T14:03:55Z — rerun bash init.sh to refresh -->
<!-- ZCGS:END -->