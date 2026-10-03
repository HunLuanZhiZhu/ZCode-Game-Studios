<div align="center">

<img src="./assets/zcode-game-studios-banner.svg" width="100%" alt="ZCode Game Studios — a ZCode-oriented adaptation of Claude Code Game Studios" />

<br/>

<a href="./READMEch.md"><img src="https://img.shields.io/badge/中文文档-READMEch.md-2563EB?style=for-the-badge" alt="Chinese README"/></a>
<a href="./README.original.md"><img src="https://img.shields.io/badge/Original_README-preserved-6B7280?style=for-the-badge" alt="Original README"/></a>
<a href="https://github.com/Donchitos/Claude-Code-Game-Studios"><img src="https://img.shields.io/badge/Upstream-Claude_Code_Game_Studios-181717?style=for-the-badge&logo=github" alt="Upstream project"/></a>

<br/><br/>

**A ZCode-oriented working fork for experimenting with multi-agent game-development workflows, autonomous execution, and evaluation.**

</div>

> [!IMPORTANT]
> This repository is based on **[Claude Code Game Studios](https://github.com/Donchitos/Claude-Code-Game-Studios)** by its original authors.  
> The previous project README has been preserved unchanged as **[README.original.md](./README.original.md)**.  
> This page describes how I use and position this fork rather than replacing the upstream project's documentation or attribution.

---

## What is this fork?

The upstream project turns an AI coding session into a structured game-development studio made of specialized agents, skills, rules, hooks, and production workflows.

This repository is my **ZCode-oriented adaptation and experimentation branch** of that idea.

The main focus is not to rewrite the upstream documentation. Instead, this README acts as a short landing page for the parts I care about most:

<table>
<tr>
<td width="33%" valign="top">

### 🎮 Multi-agent game development
A studio-style hierarchy of directors, leads, and specialists for design, engineering, art, QA, production, and release work.

</td>
<td width="33%" valign="top">

### 🤖 ZCode workflow adaptation
The repository uses <code>.zcode/</code> agents, skills, rules, and workflow assets so the studio can be used inside a ZCode-centered development environment.

</td>
<td width="33%" valign="top">

### 🌙 Autonomous experiments
Workflows such as <code>/auto-game-in-sleep</code> explore how much of the game-development pipeline can be chained, reviewed, tested, and iterated automatically.

</td>
</tr>
</table>

---

## At a glance

| Component | Current repository |
|---|---:|
| Specialized agents | **49** |
| Skills / slash workflows | **74** |
| Path-scoped rules | **11** |
| Document templates | **41** |
| Main environment | **ZCode-oriented** |
| Game engines represented | **Godot · Unity · Unreal** |

For the exhaustive upstream feature list, workflow catalog, hook behavior, installation notes, and design philosophy, read the preserved **[original README](./README.original.md)**.

---

## How I use this repository

My interest in this project is primarily in the **agent-system and evaluation layer** around game development:

~~~text
game concept
    │
    ▼
multi-agent planning
    │
    ├── design
    ├── architecture
    ├── implementation
    ├── assets
    ├── QA
    └── production
    │
    ▼
build / run / inspect
    │
    ▼
independent review
    │
    ▼
iterate
~~~

The interesting question is not simply whether an LLM can generate a game.

It is whether a structured set of agents, rules, tools, review gates, and execution loops can make AI-driven game creation **more reproducible, inspectable, and evaluable**.

---

## Repository structure

The most relevant pieces are:

| Path | Purpose |
|---|---|
| [<code>.zcode/agents/</code>](./.zcode/agents) | Specialized agent definitions |
| [<code>.zcode/skills/</code>](./.zcode/skills) | Workflow / slash-command skills |
| [<code>.zcode/rules/</code>](./.zcode/rules) | Path-scoped development rules |
| [<code>.zcode/docs/</code>](./.zcode/docs) | Workflow metadata and templates |
| [<code>ccgs-studio-hooks/</code>](./ccgs-studio-hooks) | Optional automation / safety hooks |
| [<code>production/</code>](./production) | Planning, milestones, autonomous-run state, and reports |
| [<code>design/</code>](./design) | Game design documents |
| [<code>src/</code>](./src) | Game implementation area |

---

## Autonomous game workflow

One of the most interesting parts of this fork is the <code>/auto-game-in-sleep</code> workflow.

At a high level, it is designed to chain multiple development stages:

<div align="center">

**concept → design → architecture → implementation → build → playtest → review → iterate**

</div>

The preserved upstream README contains the detailed behavior, safety rails, acceptance gates, state files, and reporting conventions.

See:

**[Original README → Unattended Autonomy](./README.original.md#unattended-autonomy-auto-game-in-sleep)**

---

## Related public evaluation

I also publish browser-facing AI game-generation evaluation work through my personal Browser Lab:

**[AI Game Generation Evaluation — Season 2](https://zyh.sryze.cc/projects/game-studio-eval-s2/)**

This is useful as a public-facing complement to the workflow and repository-level experimentation here.

---

## Getting started

For the full setup instructions, use the upstream-preserved documentation:

**[Open the original setup guide →](./README.original.md#getting-started)**

The short version is:

1. clone the repository;
2. open it in ZCode;
3. use <code>/start</code> to enter the guided workflow;
4. or invoke a specific skill such as <code>/brainstorm</code>, <code>/setup-engine</code>, or <code>/project-stage-detect</code>.

---

## Upstream and attribution

This repository builds on:

**[Donchitos / Claude-Code-Game-Studios](https://github.com/Donchitos/Claude-Code-Game-Studios)**

The original project's documentation, architecture, agents, workflows, and other upstream contributions remain credited to their respective authors.

To avoid losing that context, the README that previously occupied this repository root is retained here:

**[README.original.md](./README.original.md)**

---

<div align="center">

<sub>
This README describes my fork and usage context. For authoritative upstream documentation, use the original project and the preserved original README.
</sub>

</div>
