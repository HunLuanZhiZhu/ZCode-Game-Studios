---
name: auto-game-in-sleep
description: "Fully autonomous unattended game production run (auto-game-in-sleep — 'make the game while you're not at the keyboard'). Chains every studio workflow from concept to polished game, makes all decisions on the user's behalf (logged for audit), tests the running game itself via web export + browser automation, iterates until quality bars are met, and leaves a report for when you return. Game languages (array) and project-doc language are configurable. Use when the user wants a hands-off / non-interactive / fully automatic run — e.g. 'auto-game-in-sleep', 'autopilot', 'run the whole pipeline yourself', '睡一觉醒来游戏做好', '一晚上自动做完游戏', '不要问我，全部自己决定'."
argument-hint: "[resume | fresh] [— review: solo|lean|full] [— testing: browser|headless] [— game-lang: 简体中文,English] [— docs-lang: 简体中文] [— engine: Godot] [— target: Web] [— debug: control-browser] [— art: svg] [— vision: auto|native|mcp] [— rounds: 5] [— score: 9]"
user-invocable: true
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, TodoWrite, Agent, Skill
---

# auto-game-in-sleep — Autonomous Unattended Studio Run

`auto-game-in-sleep` means "make the game while you're not driving" — the run
executes in a non-interactive state, with no user in the loop. It is not a
literal overnight timer; the name is about *unattended* execution.

One invocation of this skill = one complete studio run. You pick up wherever
the project stands (or start from nothing), drive the full pipeline defined in
`.zcode/docs/workflow-catalog.yaml`, test the running game yourself, and only
stop when the game is done or further progress is impossible. **There is no one
to ask — the user is away from the keyboard.**

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
- `production/auto-game-in-sleep/morning-report.md` — the report for when the user returns (what was built, how to run it, what to do next)

---

## Constants

Override via arguments: `/auto-game-in-sleep — review: solo — testing: headless — game-lang: 简体中文,English — docs-lang: 简体中文 — engine: Godot — target: Web — debug: control-browser — art: svg — vision: auto|native|mcp — rounds: 5 — score: 9`

- **NO TIME CAP.** This skill imposes no time limit and you must not invent
  one. Run until the pipeline is complete or genuinely blocked. How long that
  takes depends on external factors (API throughput, tool availability) that
  you cannot estimate — guessing a duration only makes you stop early. The
  closest thing to a "stop" is the quality/stall logic below, never a clock.
- **GAME_LANGS = [简体中文]** — the languages the shipped game contains, as an
  array. Element `[0]` is the primary/default in-game language: all UI text,
  dialogue, menus, subtitles, and in-world text are authored in it. Each extra
  entry is a localization target — build the game localization-ready and, once
  playable, run `/localize` to populate that language's string table. A
  single-entry run just ships `GAME_LANGS[0]`.
- **DOCS_LANG = 简体中文** — the language every generated *project document*
  is written in: GDDs, art bible, ADRs, architecture, UX specs, review and
  playtest reports, the decision log, and the return report. This is the
  language *you* read, and it is independent of the game's own language.
- **ENGINE = Godot** (default location: the project root directory; if Godot
  is not present there, download it to that path) — the engine to configure
  when the project has none set. This location note applies only to the Godot
  default; when `ENGINE` is overridden with another engine, it no longer
  applies. Passed to `/setup-engine`. If an engine is already configured in
  `.zcode/docs/technical-preferences.md`, the run respects it; otherwise it
  configures `ENGINE`. Godot is the default because its web export is the
  cleanest path for the default `PREFERRED_TARGET`.
- **⚠️ GODOT + 中文必备字体** — When `ENGINE == Godot` and `GAME_LANGS` includes `简体中文` (or any CJK), the Web build MUST bundle a CJK-capable font from the host machine and use it in the project (e.g. `DynamicFont`/`Theme`/`FontFile` and ensure it is exported with the Web preset). Without this, Godot Web renders Chinese as unreadable tofu/mojibake (four small boxes/digits crammed together, etc.). Look up the latest Godot 4 tutorial for "Godot CJK font setup" and follow it. **This is a blocking requirement — do not mark `setup-engine` as `accepted` until the Web test run shows Chinese text renders correctly without tofu.**
- **PREFERRED_TARGET = Web** — the primary shipped artifact. The run builds and
  verifies toward this target (for `Web`, the Test Loop serves a web build and
  drives it in a browser). Adapt the build path and verification when this is a
  desktop or other target.
- **DEBUG_SKILL = control-browser** — the browser-automation skill used to play
  and observe the running game in the Test Loop. Load its own guide first if it
  ships one. Falls back to any other browser tooling, then to headless checks,
  if unavailable.
- **ART_METHOD = svg** — how art assets are actually produced. Default is a
  self-contained, no-image-model pipeline:
  - `svg` (default) — for each asset spec: (1) keep the AI-generation prompt in
    the spec for later human upgrade; (2) author the art as **SVG** (text the
    agent can write and iterate directly); (3) **rasterize** the SVG to PNG/JPG
    at the spec's dimensions — **prefer browser screenshots**: serve the file
    locally (`python -m http.server`) and capture with `DEBUG_SKILL` (`control-browser`)
    at the spec’s width/height; the screenshot is both the raster and the visual check
    artifact. Fall back to `cairosvg` / `rsvg-convert` / `Inkscape` only when the
    browser is unavailable.  (4) **convert to an engine asset** — only
    if the format isn't already PNG/JPG/SVG (most engines, e.g. Godot, import those natively, so
    usually skip this step; convert only when the engine needs a specialized
    texture/atlas format); (5) **visually check** the raster per `VISION`
    (`native`
    reads the image directly, `mcp` reads via the vision MCP, `auto` probes native
    first then MCP) and iterate the SVG until it matches the spec. A missing vision
    capability is a **blocking** error — do not silently skip; log `blocked` and stop
    the art sub-flow until vision is available.
    No external image model required;
    the game ships with real (vector-derived) art, not placeholders.
  - `generate` — run each spec's prompt through an image-generation tool/MCP
    instead of drawing SVG, then `/asset-audit` and advance the manifest to
    `Done`. Use this when a real image model is wired in and you want
    model-produced art over vector art.
- **VISION = auto|native|mcp** — how the run sees images. Do not let the model guess. The value here is the authority; there is no "if it has vision" self-test.
  - `auto` (default) — probe once at startup: try native image read first (direct `Read` of image files / `control-browser` screenshots); if unavailable, try the vision MCP. If neither exists, this is a **blocking** error — log `blocked` and stop the art/playtest sub-flow; do not degrade silently.
  - `native` — force direct image read. If the host cannot read images, log `blocked` as a hard error; do not silently skip visual checks.
  - `mcp` — force the vision MCP path (e.g. `view_image` / `read_image` tools). If the MCP is absent, log `blocked` as a hard error.
  Vision is **required** — a game without visual verification is not shippable. There is no `none` mode.
- **REVIEW_MODE = lean** — director review at phase gates (`/gate-check`).
  `solo` skips gate reviews entirely (fastest, riskiest). `full` adds
  per-workflow director reviews. Only overrides `production/review-mode.txt`
  when explicitly passed; otherwise respect the existing file.
- **MAX_ROUNDS = 5** — cap on adversarial review-loop rounds (see that
  subsection). The loop also stops early once the score threshold is met.
- **SCORE_THRESHOLD = 9** — overall score (0–10) that ends the adversarial
  review loop, combined with the `真实可玩性 ≥ 8` hard gate.
- **TESTING = browser** — `browser` = web build + browser-automation playtest
  (rule 2 in full). `headless` = engine headless runs and screenshots only
  (use when no browser tooling exists). Never choose `off`.
- **RESUME = auto** — resume an interrupted run when state exists; `fresh`
  forces a new run; `resume` forces continuing.

## State & Heartbeat

The run's live state is visible in `production/auto-game-in-sleep/state.json`.
If the file does not exist, this skill creates it on first entry (Phase 0);
otherwise the skill reads and resumes from it. Never store live values like
`current_phase/current_step/last_seen` in `AGENTS.md` — the anti-compression
anchor there (`<!-- ZCGS:BEGIN -->`, injected by `bash init.sh`) holds only
static instructions and pointers; `state.json` (plus `journal.md`) is the truth.

Heartbeat discipline — the FIRST action of every pipeline step:

1. Update `state.json` with `current_phase`, `current_step`, an ISO-8601
   `last_seen`, and `next` (the concrete next action).
2. Append a self-contained entry to `journal.md` (what was attempted, what is
   next, which paths matter) so a compacted session can resume from the journal
   plus `state.json` alone.
3. Journal entries must be self-contained; evidence paths in `state.json`
   `steps[]` must be review/test reports or catalog artifact checks — a step is
   `done` when the executor finished, `accepted` only when evidence passes.

On resume, the Recovery Protocol in the `AGENTS.md` anchor (re-read this
`SKILL.md` first, then `state.json`, then `journal.md`) determines the first
non-`accepted` step and re-verifies any `done` without evidence.

## Language

Two independent language settings — do not conflate them:

- **Game content** (UI strings, dialogue, menus, subtitles, in-world text) is
  authored in `GAME_LANGS[0]`. Extra entries are localization targets: keep
  all strings in external string tables (never hardcoded in scenes/scripts),
  and once the game is playable, run `/localize` for each additional language
  to populate its table. A single-language run ships only `GAME_LANGS[0]`.
- **Project documents** (GDDs, art bible, ADRs, architecture, UX specs, review
  and playtest reports, the decision log, and the return report) are written in
  `DOCS_LANG` — the language *you* read. This is independent of the game's
  language: a Japanese game can sit on top of Chinese dev docs.

Discipline:

- Never hardcode in-game text in scenes or scripts — it must stay localizable,
  because `GAME_LANGS` may name more than one language.
- Dev docs are always in `DOCS_LANG`, never in the game's language.
- If `GAME_LANGS` has more than one entry, add a localization pass to the
  Release phase: after `/launch-checklist`, run `/localize` once per extra
  language, then re-run the relevant test checkpoint to confirm no broken strings.

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
  risks leaving the game incomplete (see rule 5).
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
headless runs and engine screenshots otherwise. Use the debug skill
`DEBUG_SKILL` (default `control-browser`) to play and observe the build; fall
back to any other browser tooling, then to headless-only checks. Details in
**The Test Loop**.

### 3. Chain the pipeline — never stop between workflows

A workflow completing is not a stopping point. The instant one step's artifact
exists and its gate accepts it, the next step in the pipeline starts — same
session, no summary-and-stop. The full ordered chain is in **The Pipeline**
below; `.zcode/docs/workflow-catalog.yaml` is the source of truth for
completion checks. The only legitimate ways a run moves from step X to "stop"
are: the run is genuinely blocked (wrap up) or all steps complete (wrap up).

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

### 5. Run to completion, not to a clock

There is no time budget. Keep working through the pipeline until it is
complete or genuinely blocked — see Wrap-Up for the only legitimate stop
conditions. Do not invent a duration limit, and do not treat "the user is
away" as a reason to rush or cut scope.

One non-negotiable prohibition:

- **Quality gates may say "not yet", never "forever".** A gate failing does
  not end the run — fix and re-test (rule 1's decision protocol applies to
  how). Only full completion or a genuine block ends work.

Blocked items never stop the run: if a single problem survives the debug
discipline (see Test Loop), or a required external resource is missing
(engine binary, export templates, browser tooling), record it in the
**Blocked List** in `state.json`, apply the best fallback, and keep moving.
Only wrap up early when progress is genuinely impossible — and say so honestly.

---

## Phase 0 — Resume or Start

Read `production/auto-game-in-sleep/state.json` if it exists (respect the
`RESUME` constant).

- **Exists and `status: "running"`** — resume: verify every step recorded
  `done` but not `accepted` (see state schema below) by re-running its
  acceptance check — an executor finishing is not evidence. Continue at the
  first non-accepted step. Journal one line: `RESUMED at <step>`.
- **Exists and `status: "done"`/`"wrapped"`** — start a fresh run (archive
  the old run dir into `production/auto-game-in-sleep/archive-<date>/` first).
- **Missing** — new run. Create the directory and initial `state.json`:

```json
{
  "status": "running",
  "started_at": "<ISO timestamp>",
  "last_seen": "<ISO timestamp>",
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
`# Run started <date> <time>` header.

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
   choose a concept that is ambitious but shippable — one
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
1. `/setup-engine [ENGINE]` → `.zcode/docs/technical-preferences.md` names a real engine. When none is configured, configure `ENGINE` (default Godot); if one is already set, respect it. Target `PREFERRED_TARGET` (default Web) — Godot+Web is the cleanest export path, which is why both default there.
   Acceptance: if `ENGINE == Godot` and `GAME_LANGS` includes CJK (简体中文/繁體中文/日本語/한국어), verify a CJK-capable font is bundled, assigned via `Theme`/`DynamicFont`/`FontFile`, exported with the Web preset, and the Web smoke run renders Chinese without tofu/mojibake before marking the step `accepted`.
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

    **Asset production** (driven by `ART_METHOD`, after specs exist):
    - `svg` (default) — keep each spec's AI prompt for later human upgrade;
      author the art as SVG, then:
      1. **Rasterize** the SVG to PNG/JPG at the spec's dimensions — **prefer
         browser screenshots**: serve the SVG locally and capture with
         `DEBUG_SKILL` (`control-browser`) at the spec’s dimensions; the
         screenshot is both the raster and the visual-check artifact. Fall back
         to `cairosvg` / `rsvg-convert` / `Inkscape` only when the browser is
         unavailable.
      2. **Convert to an engine asset** — only if the format isn't already
         PNG/JPG/SVG (most engines, e.g. Godot, import those natively, so usually omit this step;
         convert only when the engine needs a specialized texture/atlas format).
      3. **Visually check** per `VISION` (`native` reads directly, `mcp` via the
         vision MCP, `auto` probes native first then MCP). **Iterate the SVG**
         until it matches the spec. If vision is unavailable, do not skip —
         log `blocked` and stop this asset’s sub-flow.
    - `generate` — run each spec's prompt through an image-generation tool/MCP,
      write the result into `assets/`, then `/asset-audit` and advance the
      manifest to `Done`.
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
29. **Adversarial review loop** — independent scored review that drives the
    game to a quality bar (see [The Adversarial Review Loop](#the-adversarial-review-loop)).
    Gated by `REVIEW_MODE`: `solo` skips it; `lean` runs it once here; `full`
    runs it per major artifact.

**Release**
30. `/release-checklist` → items fixed or logged
31. `/patch-notes` and `/changelog` → docs written
32. `/launch-checklist` → final gate

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

Procedure per checkpoint (commands below are the `ENGINE=Godot`,
`PREFERRED_TARGET=Web` path; adapt the engine binary and export target when
either differs):

1. **Headless boot smoke** — catches script/runtime errors cheaply:
   `godot --headless --path . --quit-after 300` (300 frames). Any error or
   script failure in output = bug. Fix before continuing.
   Redirect output to a timestamped log: `test-runs/<checkpoint>-<YYYYMMDD-HHMMSS>.boot.log`
   (e.g. `checkpoint-B-20260904-120500.boot.log`); judge state by reading the log tail.
2. **Web build** — ensure `export_presets.cfg` has a Web preset (create it if
   missing), then `godot --headless --path . --export-release "Web" ../build/web/index.html`,
   with output redirected to `test-runs/<checkpoint>-<YYYYMMDD-HHMMSS>.export.log`.
   If export templates are missing: try installing them; if that fails, log
   blocked + fall back to headless checks and engine screenshots.
3. **Serve** — serve `build/web` locally. Pick the port by probing upward from
   8600: use the first free port (`test_server_port`, recorded in `state.json`
   so the whole checkpoint reads the same value). Example:
   `python -m http.server <test_server_port> --directory build/web` in the
   background (kill it at checkpoint end). Never hardcode 8600 — a stale server
   from a previous run may still hold it.
4. **Play it** — drive the running build with the debug skill `DEBUG_SKILL`
   (default `control-browser`; load its guide first if it ships one). Open
   `http://localhost:<test_server_port>` (the probed port from step 3, not a
   hardcoded value). If
   `DEBUG_SKILL` is unavailable, fall back to any other browser-automation
   tooling, then to headless-only checks:
   - open the served URL, wait for load, screenshot
   - read console errors — any error counts as a bug; save console output to
     `test-runs/<checkpoint>-<YYYYMMDD-HHMMSS>.console.log`
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
   critical/major bugs · 60s continuous browser play with no errors.

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
  morning report. Do not keep grinding against a wall.

Avoid thrash: if an iteration makes the test result worse, revert it (keep the
diff in the journal) and pick a different improvement.

---

## The Adversarial Review Loop

A scored, independent challenge loop that pushes the game to a quality bar
before Wrap-Up. It is the studio's equivalent of a cross-model jury: an
independent reviewer subagent attacks the work, scores it, and forces fixes
until a threshold — the implementer never acquits its own work.

**Gating (`REVIEW_MODE`)**: `solo` skips the loop entirely; `lean` runs it once
at the Polish step above; `full` runs it per major artifact (per system GDD,
per sprint, per release gate). When skipped, journal it.

**One reviewer, all dimensions.** Spawn a single fresh-context reviewer
subagent (e.g. `creative-director` or `qa-lead` — never the agent that wrote the
code) to score every dimension below and emit 意见 / 建议 / 疑问. Scoring from a
single rater keeps the dimensions comparable across rounds.

**Mechanism per round**

1. **Gather evidence via the debug skill.** The main agent builds the game,
   launches it, and drives it with `DEBUG_SKILL` (`control-browser`): enter the
   game, play the core loop, pause/resume, reach a win/lose, capture screenshots,
   console output, and input→feedback notes. Write the evidence pack to
   `production/auto-game-in-sleep/test-runs/review-<round>.md`. Real-play
   dimensions are scored **only** from this pack — never from reading code.
2. **Hand the pack to the reviewer.** Give the subagent: the evidence pack, the
   GDD acceptance criteria, and the score tables below. For Part A it may also
   read the GDDs and source in its fresh context; for Part B it scores strictly
   from the evidence pack.
3. **The reviewer scores and writes** 意见 / 建议 / 疑问 (formats below). Every
   dimension score carries a one-line reason anchored to the rubric, so it
   cannot be handed out arbitrarily.
4. **The main agent implements the 建议** (prioritized fixes), then the next
   round begins. Update `state.json`: `iterations`, `stale_count`, and the
   `adversarial-review` step's `done`/`accepted` + evidence path.

**Scoring — two parts, six dimensions (each 0–10)**

Part A — design & implementation (static; from GDD + source)

| Dimension | 0 | 5 | 8 | 10 |
|-----------|---|---|---|----|
| 完整度 | GDD-promised systems mostly absent | core present, several GDD features missing | all MVP systems in place, minor gaps | full tier implemented per GDD |
| 新颖性 | cliché clone, no identity | competent but familiar | clear original turn on a known genre | genuinely novel core loop |
| 架构与可维护性 | spaghetti, no structure | follows basic conventions, some smells | clean, follows `.zcode/rules` | exemplary, easy to extend |

Part B — artifact (dynamic; scored **only** from the `DEBUG_SKILL` evidence pack)

| Dimension | 0 | 5 | 8 | 10 | source |
|-----------|---|---|---|----|--------|
| 真实可玩性 | can't even enter / crashes on boot | enters but core loop breaks early / softlock | core loop completable to win/lose, minor issues | smooth full playthrough, no blockers | DEBUG_SKILL play |
| 界面美观性 (static) | broken / unstyled | functional but plain | clean, on-theme | polished, clear, matches art bible | DEBUG_SKILL frame |
| 动态体验 (feel/feedback) | no feedback, laggy input | basic feedback, ok response | clear timely feedback, satisfying | excellent juice, fluid | DEBUG_SKILL play |

`真实可玩性` and `动态体验` are dynamic (during play); `界面美观性` is the
static look — the three are orthogonal.

**Aggregate & termination**

- **总分 = mean of the 6 dimension scores.**
- **Hard gate**: while `真实可玩性 < 8`, the loop MUST NOT stop — a 9/10 average
  that can't even enter the game is never accepted.
- **Stop when**: `总分 > SCORE_THRESHOLD (9)` **and** `真实可玩性 ≥ 8`, **or**
  `iterations > MAX_ROUNDS (5)`.
- On stop, record the final scores in the `adversarial-review` step as
  `accepted` (with the evidence pack path) and carry them into the morning
  report's Quality bars section.

**Outputs per round (the reviewer writes)**

- **意见** — per-dimension score + one-line reason; what works, what doesn't.
- **建议** — concrete, prioritized fixes; each tied to a dimension; mark which
  are the minimum to clear the threshold.
- **疑问** — things the reviewer cannot resolve from evidence (e.g. "is X
  intended or a bug?"). If a 疑问 blocks acceptance, log it to the blocked list
  / morning report for the human.

**Reuses (no new machinery)**

- *done≠accepted* — the loop step is `accepted` only with the score + evidence
  pack on file; "I fixed it" is not evidence.
- *stale ladder* — a round with zero new findings increments `stale_count`;
  ≥2 forces a different review angle next round; ≥4 stops the loop and wraps up.
- *reviewer independence* — fresh subagent, never the implementer; scores from
  evidence (Part B) / fresh read (Part A), not its own memory.

## Wrap-Up

When the pipeline finishes, `stale_count` hits the ladder top, or progress
becomes impossible:

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
   ## Quality bars
   <which acceptance criteria / gates PASSED, which did NOT — be exact. The
   run stopped because it completed or hit a stall, never because a clock ran out.>
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
- **Project has a concept but zero code and you must deliver a minimal-but-complete game**: skip to a
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
