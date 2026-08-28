<p align="center">
  <h1 align="center">Claude Code Game Studios</h1>
  <p align="center">
    Turn a single Claude Code session into a full game development studio.
    <br />
    49 agents. 74 skills. One coordinated AI team.
  </p>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT License"></a>
  <a href=".zcode/agents"><img src="https://img.shields.io/badge/agents-49-blueviolet" alt="49 Agents"></a>
  <a href=".zcode/skills"><img src="https://img.shields.io/badge/skills-74-green" alt="74 Skills"></a>
  <a href="ccgs-studio-hooks/hooks"><img src="https://img.shields.io/badge/hooks-12-orange" alt="12 Hooks"></a>
  <a href=".zcode/rules"><img src="https://img.shields.io/badge/rules-11-red" alt="11 Rules"></a>
  <a href="https://docs.anthropic.com/en/docs/claude-code"><img src="https://img.shields.io/badge/built%20for-Claude%20Code-f5f5f5?logo=anthropic" alt="Built for Claude Code"></a>
  <a href="https://www.buymeacoffee.com/donchitos3"><img src="https://img.shields.io/badge/Buy%20Me%20a%20Coffee-Support%20this%20project-FFDD00?logo=buymeacoffee&logoColor=black" alt="Buy Me a Coffee"></a>
  <a href="https://github.com/sponsors/Donchitos"><img src="https://img.shields.io/badge/GitHub%20Sponsors-Support%20this%20project-ea4aaa?logo=githubsponsors&logoColor=white" alt="GitHub Sponsors"></a>
</p>

---

## Why This Exists

Building a game solo with AI is powerful — but a single chat session has no structure. No one stops you from hardcoding magic numbers, skipping design docs, or writing spaghetti code. There's no QA pass, no design review, no one asking "does this actually fit the game's vision?"

**Claude Code Game Studios** solves this by giving your AI session the structure of a real studio. Instead of one general-purpose assistant, you get 49 specialized agents organized into a studio hierarchy — directors who guard the vision, department leads who own their domains, and specialists who do the hands-on work. Each agent has defined responsibilities, escalation paths, and quality gates.

The result: you still make every decision, but now you have a team that asks the right questions, catches mistakes early, and keeps your project organized from first brainstorm to launch.

---

## Table of Contents

- [What's Included](#whats-included)
- [Studio Hierarchy](#studio-hierarchy)
- [Slash Commands](#slash-commands)
- [Getting Started](#getting-started)
- [Upgrading](#upgrading)
- [Project Structure](#project-structure)
- [How It Works](#how-it-works)
- [Design Philosophy](#design-philosophy)
- [Customization](#customization)
- [Platform Support](#platform-support)
- [Community](#community)
- [Supporting This Project](#supporting-this-project)
- [License](#license)

---

## What's Included

| Category | Count | Description |
|----------|-------|-------------|
| **Agents** | 49 | Specialized subagents across design, programming, art, audio, narrative, QA, and production |
| **Skills** | 74 | Slash commands for every workflow phase (`/start`, `/design-system`, `/create-epics`, `/create-stories`, `/dev-story`, `/story-done`, etc.), including `/auto-game-in-sleep` for fully hands-off unattended runs |
| **Hooks** | 12 | Automated validation on commits, pushes, asset changes, session lifecycle, agent audit trail, and gap detection |
| **Rules** | 11 | Path-scoped coding standards enforced when editing gameplay, engine, AI, UI, network code, and more |
| **Templates** | 41 | Document templates for GDDs, UX specs, ADRs, sprint plans, HUD design, accessibility, and more |

## Studio Hierarchy

Agents are organized into three tiers, matching how real studios operate:

```
Tier 1 — Directors (Opus)
  creative-director    technical-director    producer

Tier 2 — Department Leads (Sonnet)
  game-designer        lead-programmer       art-director
  audio-director       narrative-director    qa-lead
  release-manager      localization-lead

Tier 3 — Specialists (Sonnet/Haiku)
  gameplay-programmer  engine-programmer     ai-programmer
  network-programmer   tools-programmer      ui-programmer
  systems-designer     level-designer        economy-designer
  technical-artist     sound-designer        writer
  world-builder        ux-designer           prototyper
  performance-analyst  devops-engineer       analytics-engineer
  security-engineer    qa-tester             accessibility-specialist
  live-ops-designer    community-manager
```

### Engine Specialists

The template includes agent sets for all three major engines. Use the set that matches your project:

| Engine | Lead Agent | Sub-Specialists |
|--------|-----------|-----------------|
| **Godot 4** | `godot-specialist` | GDScript, Shaders, GDExtension |
| **Unity** | `unity-specialist` | DOTS/ECS, Shaders/VFX, Addressables, UI Toolkit |
| **Unreal Engine 5** | `unreal-specialist` | GAS, Blueprints, Replication, UMG/CommonUI |

## Slash Commands

Type `/` in Claude Code to access all 74 skills:

**Full Autonomy**
`/auto-game-in-sleep` — one command runs the entire studio unattended: every workflow from concept to polish, decisions made on your behalf (logged), the game built, played in a browser, and iterated until done. See [Unattended Autonomy](#unattended-autonomy-auto-game-in-sleep).

**Onboarding & Navigation**
`/start` `/help` `/project-stage-detect` `/setup-engine` `/adopt`

**Game Design**
`/brainstorm` `/map-systems` `/design-system` `/quick-design` `/review-all-gdds` `/propagate-design-change`

**Art & Assets**
`/art-bible` `/asset-spec` `/asset-audit`

**UX & Interface Design**
`/ux-design` `/ux-review`

**Architecture**
`/create-architecture` `/architecture-decision` `/architecture-review` `/create-control-manifest`

**Stories & Sprints**
`/create-epics` `/create-stories` `/dev-story` `/sprint-plan` `/sprint-status` `/story-readiness` `/story-done` `/estimate`

**Reviews & Analysis**
`/design-review` `/code-review` `/balance-check` `/content-audit` `/scope-check` `/perf-profile` `/tech-debt` `/gate-check` `/consistency-check` `/security-audit`

**QA & Testing**
`/qa-plan` `/smoke-check` `/soak-test` `/regression-suite` `/test-setup` `/test-helpers` `/test-evidence-review` `/test-flakiness` `/skill-test` `/skill-improve`

**Production**
`/milestone-review` `/retrospective` `/bug-report` `/bug-triage` `/reverse-document` `/playtest-report`

**Release**
`/release-checklist` `/launch-checklist` `/changelog` `/patch-notes` `/hotfix` `/day-one-patch`

**Creative & Content**
`/prototype` `/onboard` `/localize`

**Team Orchestration** (coordinate multiple agents on a single feature)
`/team-combat` `/team-narrative` `/team-ui` `/team-release` `/team-polish` `/team-audio` `/team-level` `/team-live-ops` `/team-qa`

## Getting Started

### Prerequisites

- [Git](https://git-scm.com/)
- [ZCode](https://zcode.z.ai/) desktop app
- **Recommended**: [jq](https://jqlang.github.io/jq/) (for hook validation) and Python 3 (for JSON validation)

All hooks fail gracefully if optional tools are missing — nothing breaks, you just lose validation.

### Setup

1. **Clone or use as template**:
   ```bash
   git clone <your-fork-url>.git my-game
   cd my-game
   ```

2. **Open the folder in ZCode** and start a new session.

3. **Run `/start`** — the system asks where you are (no idea, vague concept,
   clear design, existing work) and guides you to the right workflow. No assumptions.

   Or jump directly to a specific skill if you already know what you need:
   - `/brainstorm` — explore game ideas from scratch
   - `/setup-engine godot 4.6` — configure your engine if you already know
   - `/project-stage-detect` — analyze an existing project

That's it — `AGENTS.md`, the 74 skills in `.zcode/skills/`, and the path-scoped
rules are discovered automatically. You can start building your game right now.

### Optional: Install the Studio Hooks Plugin

The automated safety layer (commit validation, session orientation, compaction
recovery, agent audit trail) ships as a bundled plugin, `ccgs-studio-hooks/`.
It is **not required** to use this template — install it once if you want the
automation:

1. In ZCode: **Settings → Plugin Management → Add plugin marketplace**
2. Choose **local directory** and select this project's root folder
   (the marketplace manifest lives at `.claude-plugin/marketplace.json`)
3. Install and enable **ccgs-studio-hooks**
4. Start a **new session** (hook config is snapshotted at session start)

Notes:

- Hooks fire globally but self-guard: outside a CCGS project (no
  `.zcode/docs/technical-preferences.md`) every hook exits silently, so leaving
  the plugin enabled in all your other projects is safe.
- The plugin runs from ZCode's cache copy. After editing scripts under
  `ccgs-studio-hooks/hooks/`, refresh/update the plugin for changes to apply.

## Upgrading

Already using an older version of this template? See [UPGRADING.md](UPGRADING.md)
for step-by-step migration instructions, a breakdown of what changed between
versions, and which files are safe to overwrite vs. which need a manual merge.

## Project Structure

```
AGENTS.md                           # Master configuration
.claude-plugin/
  marketplace.json                  # Plugin marketplace manifest (repo root = local marketplace)
ccgs-studio-hooks/                  # Optional automation plugin (see Getting Started)
  .claude-plugin/plugin.json        # Plugin manifest
  hooks/hooks.json                  # Hook event wiring — 12 hooks across 7 events, pure Claude Code spec
  hooks/*.sh                        # Guarded hook scripts (bash, cross-platform)
.zcode/
  settings.json                     # Legacy permission reference (from the Claude Code original)
  agents/                           # 49 agent definitions (markdown + YAML frontmatter)
  skills/                           # 74 slash commands (subdirectory per skill)
  rules/                            # 11 path-scoped coding standards
  statusline.sh                     # Status line script (context%, model, stage, epic breadcrumb)
  docs/
    workflow-catalog.yaml           # 7-phase pipeline definition (read by /help)
    templates/                      # 41 document templates
src/                                # Game source code
assets/                             # Art, audio, VFX, shaders, data files
design/                             # GDDs, narrative docs, level designs
docs/                               # Technical documentation and ADRs
tests/                              # Test suites (unit, integration, performance, playtest)
tools/                              # Build and pipeline tools
prototypes/                         # Throwaway prototypes (isolated from src/)
production/                         # Sprint plans, milestones, release tracking
```

## How It Works

### Agent Coordination

Agents follow a structured delegation model:

1. **Vertical delegation** — directors delegate to leads, leads delegate to specialists
2. **Horizontal consultation** — same-tier agents can consult each other but can't make binding cross-domain decisions
3. **Conflict resolution** — disagreements escalate up to the shared parent (`creative-director` for design, `technical-director` for technical)
4. **Change propagation** — cross-department changes are coordinated by `producer`
5. **Domain boundaries** — agents don't modify files outside their domain without explicit delegation

### Collaborative, Not Autonomous

By default this is **not** an auto-pilot system. Every agent follows a strict collaboration protocol:

1. **Ask** — agents ask questions before proposing solutions
2. **Present options** — agents show 2-4 options with pros/cons
3. **You decide** — the user always makes the call
4. **Draft** — agents show work before finalizing
5. **Approve** — nothing gets written without your sign-off

You stay in control. The agents provide structure and expertise, not autonomy.

### Unattended Autonomy (auto-game-in-sleep)

When you **explicitly** run `/auto-game-in-sleep`, the studio switches to
autonomous mode for that run (no time limit — it runs until the game is done
or genuinely blocked, in the background while you are not at the keyboard):

- **The full pipeline chains itself** — concept → systems design → architecture →
  pre-production → sprints → polish → release, with no pausing between workflows.
- **Decisions are made on your behalf** — every question the workflows would
  have asked you is answered from your concept docs (or, failing that, by
  studio best practice) and recorded in
  `production/auto-game-in-sleep/decisions.md` with an "override" note, so you
  can audit and reverse anything in the morning.
- **The game builds the full scope, not a demo** — the target is the complete
  tier from the game concept; a minimal version is a milestone on the way, never
  the destination.
- **It plays its own game** — web builds are served locally and driven with a
  browser-automation skill (e.g. `control-browser`): boot, core loop, menus, game over,
  console errors, screenshots — feeding real bugs back into the sprint loop.
- **Produces art per `ART_METHOD`** — `svg` by default: writes AI prompts for
  later human upgrade, draws the art as SVG, rasterizes it to PNG for visual
  checking (model or vision MCP), converts to an engine asset only if the format
  isn't already PNG/JPG/SVG, then iterates the SVG (no image model needed; ships
  real vector-derived art). `generate` instead calls an image tool for model-produced art.
- **Runs an adversarial review loop** — an independent reviewer subagent scores
  the game on six dimensions (completeness / novelty / architecture from code;
  real playability / UI aesthetics / game feel from actual `control-browser`
  playthrough), forces fixes, and only stops at `总分 > 9` with `真实可玩性 ≥ 8`
  or after `MAX_ROUNDS = 5`. Gated by `REVIEW_MODE` (`solo` skips).
- **It iterates until good** — playtest → top improvements → re-test, until all
  GDD acceptance criteria pass, smoke check passes, and 3 playtest reports exist.
  Quality verdicts come from independent reviewer subagents, never from the agent
  that wrote the code, and repeated stalled iterations force a change of approach
  instead of more parameter tweaking.
- **Done is not accepted** — every pipeline step records `done` (executor
  finished) separately from `accepted` (gate passed, evidence on file), so an
  interrupted run resumes by re-verifying rather than trusting.
- **You get a return report** — `production/auto-game-in-sleep/morning-report.md`:
  what was built, how to run it, which quality bars passed or were missed, every
  decision made, open issues, and what to do next.

Safety rails still apply: no `git push`, no deletions of your content, guard
hooks stay active, and the run resumes cleanly if interrupted
(`production/auto-game-in-sleep/state.json` records a `last_seen` heartbeat at
every step).

### Automated Safety

**Hooks** ship as the optional [`ccgs-studio-hooks`](#optional-install-the-studio-hooks-plugin)
plugin (see Getting Started for installation). Declared in full Claude Code
plugin spec — hosts run what they support: ZCode runs 10 hooks across 5 events
(and ignores `PreCompact`/`Notification` entries), Claude Code runs all 12:

| Hook | Trigger | What It Does |
|------|---------|--------------|
| `validate-dangerous.sh` | PreToolUse (Bash\|Read) | Restores the original deny rules — blocks `rm -rf`, `git push --force`, `git reset --hard`, `git clean -f`, `sudo`, `chmod 777` and `.env` file access with a rejection reason |
| `validate-commit.sh` | PreToolUse (Bash) | Checks for hardcoded values, TODO format, JSON validity, design doc sections — exits early if the command is not `git commit` |
| `validate-push.sh` | PreToolUse (Bash) | Warns on pushes to protected branches — exits early if the command is not `git push` |
| `validate-assets.sh` | PostToolUse (Write/Edit) | Validates naming conventions and JSON structure — exits early if the file is not in `assets/` |
| `session-start.sh` | Session open | Shows current branch and recent commits for orientation |
| `detect-gaps.sh` | Session open | Detects fresh projects (suggests `/start`) and missing design docs when code or prototypes exist |
| `pre-compact.sh` | Before compaction | Preserves session progress notes into the conversation (Claude Code only — ZCode has no pre-compaction event) |
| `post-compact.sh` | Session restarts after context compaction | Reminds the model to restore session state from `active.md` |
| `notify.sh` | PermissionRequest / Notification | Shows Windows toast notification via PowerShell (deduplicated within 10 s) |
| `session-stop.sh` | Turn ends | Archives `active.md` to session log and records git activity |
| `log-agent.sh` | Agent spawned | Audit trail start — logs subagent invocation and type |
| `log-agent-stop.sh` | Agent stops | Audit trail stop — completes subagent record |
| `validate-skill-change.sh` | PostToolUse (Write/Edit) | Advises running `/skill-test` after any `.zcode/skills/` change |

> **Note**: `validate-commit.sh`, `validate-assets.sh`, and `validate-skill-change.sh` fire on every Bash/Write tool call and exit immediately (exit 0) when the command or file path is not relevant. This is normal hook behavior — not a performance concern.

**Permission rules** in `.zcode/settings.json` (kept as a legacy reference from
the Claude Code original) auto-allow safe operations and block dangerous ones;
ZCode manages permissions through its own security confirmation UI.

### Path-Scoped Rules

Coding standards are automatically enforced based on file location:

| Path | Enforces |
|------|----------|
| `src/gameplay/**` | Data-driven values, delta time usage, no UI references |
| `src/core/**` | Zero allocations in hot paths, thread safety, API stability |
| `src/ai/**` | Performance budgets, debuggability, data-driven parameters |
| `src/networking/**` | Server-authoritative, versioned messages, security |
| `src/ui/**` | No game state ownership, localization-ready, accessibility |
| `design/gdd/**` | Required 8 sections, formula format, edge cases |
| `tests/**` | Test naming, coverage requirements, fixture patterns |
| `prototypes/**` | Relaxed standards, README required, hypothesis documented |

## Design Philosophy

This template is grounded in professional game development practices:

- **MDA Framework** — Mechanics, Dynamics, Aesthetics analysis for game design
- **Self-Determination Theory** — Autonomy, Competence, Relatedness for player motivation
- **Flow State Design** — Challenge-skill balance for player engagement
- **Bartle Player Types** — Audience targeting and validation
- **Verification-Driven Development** — Tests first, then implementation

## Customization

This is a **template**, not a locked framework. Everything is meant to be customized:

- **Add/remove agents** — delete agent files you don't need, add new ones for your domains
- **Edit agent prompts** — tune agent behavior, add project-specific knowledge
- **Modify skills** — adjust workflows to match your team's process
- **Add rules** — create new path-scoped rules for your project's directory structure
- **Tune hooks** — adjust validation strictness, add new checks
- **Pick your engine** — use the Godot, Unity, or Unreal agent set (or none)
- **Set review intensity** — `full` (all director gates), `lean` (phase gates only), or `solo` (none). Set during `/start` or edit `production/review-mode.txt`. Override per-run with `--review solo` on any skill.

## Platform Support

Primary development and testing on **Windows 10** with Git Bash. All hooks use POSIX-compatible patterns (`grep -E`, not `grep -P`) and include fallbacks for missing tools, so they should run on macOS and Linux. The `notify.sh` hook uses PowerShell for Windows toast notifications and is a no-op elsewhere — desktop notifications on macOS/Linux are not yet wired. Cross-platform testing is ongoing; please file issues for any platform-specific breakage.

## Community

- **Discussions** — [GitHub Discussions](https://github.com/Donchitos/Claude-Code-Game-Studios/discussions) for questions, ideas, and showcasing what you've built
- **Issues** — [Bug reports and feature requests](https://github.com/Donchitos/Claude-Code-Game-Studios/issues)

---

## Supporting This Project

Claude Code Game Studios is free and open source. If it saves you time or helps you ship your game, consider supporting continued development:

<p>
  <a href="https://www.buymeacoffee.com/donchitos3"><img src="https://img.shields.io/badge/Buy%20Me%20a%20Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black" alt="Buy Me a Coffee"></a>
  &nbsp;
  <a href="https://github.com/sponsors/Donchitos"><img src="https://img.shields.io/badge/GitHub%20Sponsors-ea4aaa?style=for-the-badge&logo=githubsponsors&logoColor=white" alt="GitHub Sponsors"></a>
</p>

- **[Buy Me a Coffee](https://www.buymeacoffee.com/donchitos3)** — one-time support
- **[GitHub Sponsors](https://github.com/sponsors/Donchitos)** — recurring support through GitHub

Sponsorships help fund time spent maintaining skills, adding new agents, keeping up with Claude Code and engine API changes, and responding to community issues.

---

*Built for Claude Code. Maintained and extended — contributions welcome via [GitHub Discussions](https://github.com/Donchitos/Claude-Code-Game-Studios/discussions).*

## License

MIT License. See [LICENSE](LICENSE) for details.
