---
name: auto-game-in-sleep
description: "Fully autonomous overnight game production run (auto-game-in-sleep). Chains every studio workflow from concept to polished game, makes all decisions on the user's behalf (logged for audit), tests the running game itself via web export + browser automation, iterates until quality bars are met or the time budget runs out, and leaves a morning report. Use when the user asks for a hands-off / overnight / fully automatic run — e.g. 'auto-game-in-sleep', 'autopilot', 'run the whole pipeline yourself', '睡一觉醒来游戏做好', '一晚上自动做完游戏', '不要问我，全部自己决定'."
argument-hint: "[max-hours | resume | fresh] [— review: solo|lean|full] [— testing: browser|headless]"
user-invocable: true
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, TodoWrite, Agent, Skill
---

# auto-game-in-sleep — Autonomous Overnight Studio Run

One invocation of this skill = one complete studio run. You pick up wherever
the project stands (or start from nothing), drive the full pipeline defined in
`.zcode/docs/workflow-catalog.yaml`, test the running game yourself, and only
stop when the game is done or the time budget is spent. The user is asleep.
**There is no one to ask.**

Autopilot overrides the interactive behaviors of every other skill in this
template. When you execute a workflow skill while running this pipeline, its
"wait for the user" instructions are suspended and replaced by the Decision
Protocol below. Everything else in those skills (templates, section order,
quality bars, artifact paths) applies unchanged.

**Output:**
- `production/auto-game-in-sleep/state.json` — resumable run state + heartbeat
- `production/auto-game-in-sleep/decisions.md` — append-only decision log (the user audits this)
- `production/auto-game-in-sleep/journal.md` — timestamped, self-contained progress journal
- `production/auto-game-in-sleep/test-runs/` — build logs, screenshots, browser test notes
- `production/auto-game-in-sleep/morning-report.md` — what the user reads when they wake up

---

## Constants

Override via arguments: `/auto-game-in-sleep 10 — review: solo, testing: headless`

- **BUDGET_HOURS = 8** — wall-clock budget for the whole run. First positional
  argument wins (`resume`/`fresh` don't set it).
- **REVIEW_MODE = lean** — director review at phase gates (`/gate-check`).
  `solo` skips gate reviews entirely (fastest, riskiest). `full` adds
  per-workflow director reviews. Only overrides `production/review-mode.txt`
  when explicitly passed; otherwise respect the existing file.
- **TESTING = browser** — `browser` = web build + browser-automation playtest
  (rule 2 in full). `headless` = engine headless runs and screenshots only
  (use when no browser tooling exists). Never choose `off`.
- **RESUME = auto** — resume an interrupted run when state exists; `fresh`
  forces a new run; `resume` forces continuing.

## The Five Behavior Rules

These rules exist to fix the five known failure modes of a manual run. They
take precedence over any other skill's instructions.

### 1. Never block on a question (Decision Protocol)

You have no user. Every point where a workflow skill says *"use AskUserQuestion"*,
*"wait for the user's response"*, *"do not proceed until they respond"*,
*"confirm before proceeding"*, or *"never auto-run the next skill"* is
**suspended**. Instead:

1. **Answer from the record first.** Consult, in priority order:
   `design/gdd/game-concept.md` (pillars + scope tier) → the relevant system
   GDD → accepted ADRs / `docs/architecture/control-manifest.md` → the art
   bible. The consistent answer is almost always already written down.
2. **If the record doesn't answer it, decide as the studio would.** Pick the
   option that best serves the concept's pillars, the target scope tier, and
   standard game-development practice. Prefer the option that increases
   player-facing quality over the option that saves effort — except when it
   threatens the budget (see rule 5).
3. **Log every decision** in `production/auto-game-in-sleep/decisions.md`:

   ```markdown
   ## [2026-08-28 02:14] design-system / movement — COYOTE_TIME = 0.1s
   Context: GDD left the coyote-time window as a tuning knob.
   Options considered: 0.08 / 0.1 / 0.15
   Chose: 0.1s — industry-standard feel for a precision platformer (pillar 2: "tight control").
   Override: delete this entry, edit design/gdd/movement-system.md §Formulas, re-run /design-system retrofit.
   ```

4. **Ready means execute.** Finishing preparation and then asking "should I
   proceed?" is the stall this rule forbids. Resolve routine ambiguity
   yourself, act, and log the decision (step 3) so it is auditable.
5. **Never call AskUserQuestion. Never stop to wait.** The `Do not proceed`
   instructions of other skills do not apply. If a skill's next action is
   genuinely destructive or irreversible (deleting user content outside
   `production/auto-game-in-sleep/`, publishing, force-pushing), do not do
   it — log it to the blocked list (rule 5) and route around it. Autonomy
   removes needless pauses, not deliberate ones: those two cases are the
   only load-bearing human gates in a run.

### 2. Test the running game yourself

"Code compiles" is not "the game works". At every checkpoint listed in the
Test Loop below, you produce a build, run it, and observe it — through a
browser when the engine exports to web (Godot does; Unity WebGL does), via
headless runs and engine screenshots otherwise. Use the browser-automation
skill available in the environment (`agent-browser` when installed; fall back
to any other browser tooling, then to headless-only checks). Details in
**The Test Loop**.

### 3. Chain the pipeline — never stop between workflows

A workflow completing is not a stopping point. The instant one step's artifact
exists and its gate accepts it, the next step in the pipeline starts — same
session, no summary-and-stop. The full ordered chain is in **The Pipeline**
below; `.zcode/docs/workflow-catalog.yaml` is the source of truth for
completion checks. The only legitimate ways a run moves from step X to "stop"
are: budget exhausted (wrap up) or all steps complete (wrap up).

### 4. Build the full game, not the minimal one

The scope of record is the **full / complete tier** declared in
`design/gdd/game-concept.md` (or, if the concept predates tiers, everything
the systems index lists as MVP + the content counts in the GDDs). Never
substitute a smaller game because no one stopped you.

- The MVP tier (if defined) is a **milestone on the way** — first playable,
  then keep building. Reaching it is worth a journal entry, not a stop.
- Forbidden shortcuts: dropping systems from the systems index, replacing a
  GDD-specified feature with a placeholder and moving on, shipping fewer
  levels/enemies/items/content than the GDD states, skipping audio or menus
  "for now".
- If the concept itself is tiny (the user asked for a jam-size game), the
  full tier IS the small game — build it completely, then polish it deeply.
  Polishing a small game fully beats half-finishing a big one.

### 5. Budget, not perfection, ends the run — but the clock never acquits

Default budget: 8 hours (override via argument). Track elapsed time
(`state.json.started_at` vs current time). When remaining time drops below
~45 minutes, stop starting new work and execute Wrap-Up.

Two complementary prohibitions:

- **The clock may say "stop", never "good enough".** Budget exhaustion ends
  the run; it does not declare the game acceptable. The morning report states
  plainly which quality bars were and were not met at cutoff.
- **Quality gates may say "not yet", never "forever".** A gate failing does
  not end the run — fix and re-test (rule 1's decision protocol applies to
  how). Only the budget or full completion ends work.

Blocked items never stop the run: if a single problem survives the debug
discipline (see Test Loop), or a required external resource is missing
(engine binary, export templates, browser tooling), record it in the
**Blocked List** in `state.json`, apply the best fallback, and keep moving.
Only wrap up early when progress is genuinely impossible — and say so honestly.

---

## Phase 0 — Resume or Start

Read `production/auto-game-in-sleep/state.json` if it exists (respect the
`RESUME` constant).

- **Exists and `status: "running"`** — resume: set the budget clock from the
  original `started_at` unless the user passed a fresh budget. Verify every
  step recorded `done` but not `accepted` (see state schema below) by
  re-running its acceptance check — an executor finishing is not evidence.
  Continue at the first non-accepted step. Journal one line:
  `RESUMED at <step>; <n> hours spent previously`.
- **Exists and `status: "done"`/`"wrapped"`** — start a fresh run (archive
  the old run dir into `production/auto-game-in-sleep/archive-<date>/` first).
- **Missing** — new run. Create the directory and initial `state.json`:

```json
{
  "status": "running",
  "started_at": "<ISO timestamp>",
  "last_seen": "<ISO timestamp>",
  "budget_hours": 8,
  "current_phase": "concept",
  "current_step": "bootstrap",
  "mvp_milestone": false,
  "iterations": 0,
  "stale_count": 0,
  "blocked": [],
  "steps": []
}
```

`steps` records per-step progress — **`done` is not `accepted`**:

```json
{ "id": "design-system-movement", "status": "accepted",
  "evidence": "production/reviews/design-review-movement.md" }
```

- `done` — the executor finished writing the artifact. Set on completion.
- `accepted` — the step's gate passed and evidence exists: a review report,
  a passing test record, or the catalog's artifact check matching. **Never
  mark `accepted` on your own say-so** — record the evidence path in the
  step. Machine-checkable completion (file exists, export exit code 0, zero
  console errors, test suite green) is safe to self-judge; quality verdicts
  are not (see Reviewer Independence in the Iteration Loop).

Also create `decisions.md` and `journal.md` with a
`# Run started <date> <time>, budget <N>h` header.

Then detect the project stage the same way `/project-stage-detect` does:
engine configured? concept exists? GDDs? ADRs? stories? playable code? This
determines where in The Pipeline you enter. Write a TodoWrite list mirroring
the remaining pipeline steps and keep it updated throughout the run.

**Heartbeat discipline**: the *first action* of every step is to update
`state.json` — `last_seen`, `current_phase`, `current_step` — *before* any
work that might hang or crash. If the session dies mid-run, `last_seen`
tells the morning user exactly where it died, and the post-compact /
session-start hooks point the next session here. Journal entries must be
self-contained (what was attempted, what's next, which paths matter) so a
context-compacted or restarted session can resume from the journal alone.

---

## Phase 1 — Bootstrap (only for a fresh project)

If the project has no concept yet, you are the studio today. Do, in order:

1. **Concept**: run the `/brainstorm` process yourself (no user interview):
   choose a concept that is ambitious but shippable within the budget — one
   strong core verb, 2–3 systems deep, genre with proven fun patterns.
   Write `design/gdd/game-concept.md` with an explicit scope tier table and
   mark the **full tier** as the target. Announce it in the journal.
2. **Review mode**: if `production/review-mode.txt` is absent, write `lean`
   (directors at phase gates only — quality control without per-skill pauses).
3. **Stage file**: write the current stage to `production/stage.txt`.
4. Continue into The Pipeline at the Concept phase.

If the project already has artifacts, skip whatever is done (verified by the
catalog's artifact checks) and enter the pipeline at the first incomplete step.

---

## The Pipeline

Execute top to bottom. `→` marks the acceptance evidence (from
`workflow-catalog.yaml` — use its glob/pattern checks; the list below is the
order and the repeat rules). Invoke each step's skill via the Skill tool and
follow its process, with interactive pauses suspended per rule 1.

**Concept**
1. `/setup-engine` → `.zcode/docs/technical-preferences.md` names a real engine. For a web-testable target prefer Godot (clean web export).
2. Concept document exists (done in bootstrap, or `/brainstorm` for an existing vague project) → `design/gdd/game-concept.md`
3. `/design-review design/gdd/game-concept.md` → fix issues it can fix itself; log anything arguable
4. `/art-bible` → `design/art/art-bible.md`
5. `/map-systems` → `design/gdd/systems-index.md`

**Systems Design** (repeat per system)
6. `/design-system [system]` for every MVP system in the index → GDD per system
7. `/design-review [gdd]` per GDD → no unresolved MAJOR REVISION verdicts
8. `/review-all-gdds` → cross-review report written
9. `/consistency-check` → contradictions fixed

**Technical Setup**
10. `/create-architecture` → `docs/architecture/architecture.md`
11. `/architecture-decision` until ≥3 Foundation ADRs accepted → `docs/architecture/adr-*.md`
12. `/architecture-review` → review report, issues fixed
13. `/create-control-manifest` → `docs/architecture/control-manifest.md`
14. Accessibility requirements committed → `design/accessibility-requirements.md`

**Pre-Production**
15. `/asset-spec` inventory + per-asset specs → `design/assets/entity-inventory.md`, `asset-manifest.md` (skip if visually trivial — journal the skip)
16. `/ux-design` for ≥3 key screens (main menu, gameplay HUD, pause) → `design/ux/*.md`
17. `/ux-review` → issues fixed
18. Prototype: only if the core mechanic is genuinely high-risk (journal the decision either way)
19. `/create-epics layer: foundation`, then `layer: core` (+ feature layers) → `production/epics/*/EPIC.md`
20. `/create-stories [epic]` per epic → story files
21. `/test-setup` → test scaffold (engine test framework)
22. `/sprint-plan` → first sprint

**Production** — loop until every story is Done:
23. For the current sprint, for each ready story in priority order:
    `/story-readiness` (quick check) → `/dev-story [story-path]` (delegate
    implementation to the matching specialist agent where the skill says so)
    → `/code-review` → `/story-done`
24. End of sprint: `/smoke-check` → **must PASS** (this is also Test Loop
    checkpoint B) → `/retrospective` → next `/sprint-plan`
25. When the last story closes: journal `MVP milestone reached` if not yet,
    and if the full tier needs more sprints, plan and run them (rule 4)

**Polish**
26. `/perf-profile`, `/balance-check`, `/asset-audit` → fixes applied
27. `/playtest-report` ×3 (you are the playtester — see Test Loop checkpoint C: new-player path, core systems, difficulty curve)
28. `/team-polish` → coordinated polish pass

**Release**
29. `/release-checklist` → items fixed or logged
30. `/patch-notes` and `/changelog` → docs written
31. `/launch-checklist` → final gate

Then Wrap-Up.

**Phase gates**: at each phase transition run `/gate-check`. Its verdicts are
advisory: fix CRITICAL findings, log MAJOR ones to the blocked list with a
note, and proceed.

---

## The Test Loop

Run at these checkpoints:
- **A — first playable**: after the vertical-slice moment / first playable build exists
- **B — every sprint end**: together with `/smoke-check`
- **C — polish phase**: the 3 playtest sessions
- **D — before wrap-up**: final verification of the last build

Procedure per checkpoint (Godot example — adapt commands to the engine in
`technical-preferences.md`):

1. **Headless boot smoke** — catches script/runtime errors cheaply:
   `godot --headless --path . --quit-after 300` (300 frames). Any error or
   script failure in output = bug. Fix before continuing.
2. **Web build** — ensure `export_presets.cfg` has a Web preset (create it if
   missing), then `godot --headless --path . --export-release "Web" ../build/web/index.html`.
   If export templates are missing: try installing them; if that fails, log
   blocked + fall back to headless checks and engine screenshots.
3. **Serve** — `python -m http.server 8600 --directory build/web` in the
   background (kill it at checkpoint end).
4. **Play it** — with browser automation (`agent-browser` if available; read
   its core guide first via its own instructions):
   - open `http://localhost:8600`, wait for load, screenshot
   - read console errors — any error counts as a bug
   - actually play the core loop: send input (keys/clicks), screenshot after
     each meaningful action, verify expected feedback (movement, score, state
     change, menu transitions)
   - exercise: boot → new game → core loop ≥60s → pause → resume →
     game over/win → restart
5. **Record** — write `production/auto-game-in-sleep/test-runs/<checkpoint>-<date>.md`
   with screenshots, console output, what worked, bug list. File bugs via
   `/bug-report` (they feed the Production loop) or fix trivial ones immediately.
6. **Re-test after fixes** — a checkpoint only passes when a clean run has
   zero console errors and the core loop completes.

Fallback ladder when browser automation is unavailable: engine screenshots
(Godot movie-maker mode / viewport capture script) + headless run logs +
unit tests. State plainly in the test record which level of verification was
achieved.

**Debug discipline — restart beats patching.** A broken build is your
problem, not the user's. After 1–2 targeted patches fail on the same
failure, treat "delete the current attempt and reimplement it cleanly from
the GDD/ADR contract" as a normal, often preferable option — patched-code
archaeology is how attempts rot. Escalate to the Blocked List only when the
**contract** is in question (the GDD/ADR is missing, ambiguous, or looks
wrong) — "the design may be wrong" goes in the morning report; "the build is
broken" does not. A restart may delete only the current attempt's own
scaffolding (code it wrote, configs it generated, its build artifacts) —
never GDDs, ADRs, story files, the journal, state.json, or test records.
Two clean reimplementations failing the same way = the contract or
environment is the problem: block and route around.

---

## The Iteration Loop

After the full-tier game is playable and Production is complete, iterate:

1. Run Test Loop checkpoint C as a fresh-eyes playtest. Evaluate against:
   - every GDD's **Acceptance Criteria** (the real quality bar)
   - game feel: input responsiveness, feedback/juice on core actions, clarity
     of goals, difficulty curve shape
   - first 60 seconds: can a new player understand what to do without text?
2. List the top 3–5 improvements by player-impact. Implement them.
3. Re-run the relevant test. Repeat.
4. **Exit when all true**: all GDD acceptance criteria verified in the running
   game · latest smoke-check PASS · 3 playtest reports exist · zero open
   critical/major bugs · 60s continuous browser play with no errors · fewer
   than 45 minutes of budget left.

**Reviewer independence** — the agent that wrote the code does not accept
its own quality. Machine-checkable completion (build exits 0, zero console
errors, tests green) may be self-judged. Quality verdicts — playtest
assessments, polish adequacy, the final COMPLETE — must come from a reviewer
who didn't produce the work: spawn a fresh reviewer subagent from the studio
hierarchy (`qa-lead` for playtest verdicts, `creative-director` for game
feel, `technical-director` for performance) and hand it the evidence pack
(screenshots, test records, GDD acceptance criteria) for a written verdict.
If subagents are unavailable, cold-review: new context, evidence only,
explicit rubric. The implementer's own "looks good to me" is never evidence.

**Stall detection — count, don't vibe.** After each iteration record the
number of **new findings** (bugs fixed, acceptance criteria newly verified,
improvements landed — concrete countable events, not "felt productive") in
`state.json` (`iterations`, `stale_count`). Consecutive zero-finding
iterations accumulate `stale_count`:

- `stale_count ≥ 2` → **forced structural pivot**: the next iteration must
  change the frame, not tune inside it — a different system, or a different
  improvement category (feel / content / UX / audio / performance) than the
  ones already tried. Read the journal's tried directions first and pick one
  that differs.
- `stale_count ≥ 4` → stop iterating. Wrap up and flag the stuck area in the
  morning report. Do not keep burning budget on a wall.

Avoid thrash: if an iteration makes the test result worse, revert it (keep the
diff in the journal) and pick a different improvement.

---

## Wrap-Up

When the budget nears its end, the pipeline finishes, `stale_count` hits the
ladder top, or progress becomes impossible:

1. Ensure the last build in `build/` (or equivalent) is the best one; rebuild
   web if the fix loop changed anything. Kill background servers.
2. Update `state.json`: `status: "done"` (or `"blocked-early"`), steps with
   their done/accepted status and evidence, blocked list, iterations,
   `last_seen`.
3. Write `production/auto-game-in-sleep/morning-report.md`:

   ```markdown
   # Morning Report — <date>
   ## TL;DR
   <2–3 sentences: what exists now, is it playable, where>
   ## How to run it
   <exact command / file to open>
   ## What was produced
   <phases completed, stories closed, test runs, playtest reports — with paths>
   ## Quality bars at cutoff
   <which acceptance criteria / gates PASSED, which did NOT — the clock
   stopped the run; it did not bless the game. Be exact.>
   ## Decisions I made for you
   <top 5–10 from decisions.md, most consequential first — link the file>
   ## Bugs & known issues
   <open items from the blocked list and bug backlog>
   ## What I would do next
   <prioritized hand-off list>
   ```

4. Post the report path as the final message. **Verdict: COMPLETE** when a
   playable full-tier build exists and checkpoint D's independent review
   passed; otherwise PARTIAL with an explicit reason.

---

## Hard Rules (never violated, even on autopilot)

- Never `git push`, never force-anything in git, never delete user-authored
  content outside `production/auto-game-in-sleep/`. Commit locally as the
  workflow skills prescribe; publishing stays a human act.
- Never bypass the installed guard hooks (they exist to protect the machine);
  a hook denial is a signal to change approach, not to evade.
- Never mark a story or checkpoint `accepted` without recorded evidence
  (review report / test record / artifact check) — your own satisfaction is
  not evidence.
- Never reduce declared scope (rule 4) — cut only via a logged decision that
  keeps the game complete and coherent, and surface it prominently in the
  morning report.
- Stay inside the project directory for all writes.

---

## Edge Cases

- **Engine binary not found** (e.g. `godot` not on PATH): search common
  install locations; if truly absent, do the entire pipeline except build/test
  checkpoints, marking every Test Loop checkpoint as blocked with reason —
  design, code, and reviews still proceed.
- **Existing project mid-pipeline**: enter at the first step whose acceptance
  evidence is missing. Trust checks, not memory — verify each prior artifact.
- **Project has a concept but zero code and <2h budget left**: skip to a
  compressed but complete pass: concept polish → map/design systems →
  architecture-lite → single epic → implement → test loop → report.
- **Test keeps failing on the same core loop**: apply the debug discipline
  (restart from contract after 2 failed patches). If the core loop is still
  broken after that, implement the fallback design from the GDD's edge cases,
  or descope that single feature via decision log; never leave the game
  unbootable.
- **User provided an idea as argument** (`/auto-game-in-sleep make a roguelike
  about gardening`): treat it as the brainstorm hint — build the concept
  around it.
- **Resume after crash/context loss**: state.json (`last_seen`, per-step
  done/accepted) + journal.md + the catalog artifact checks are the truth;
  redo only the current step.
