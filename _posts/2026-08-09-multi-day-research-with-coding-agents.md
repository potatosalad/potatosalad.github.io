---
layout: post
title: Multi-Day Research with Coding Agents
categories: [AI Engineering]
tags: [AI Agents, Research Automation]
hash: post-2026-08-09-984fdfd3
---

Some research tasks take coding agents hours or days.  A single session tends to collect too much context and may declare victory too early.

I wrote an agent skill named `/exp` to run these tasks as a series of smaller, persistent experiments.

<acronym title="Too long; didn't read">**TL;DR**</acronym> `/exp` starts a fresh coding agent for each iteration, keeps the handoff in files, challenges claims of completion, and commits the results to Git.

## Getting Started

Paste this prompt into [Claude Code](https://code.claude.com/docs/en/overview), [Codex](https://github.com/openai/codex), [Muse Code](https://dev.meta.ai/docs/muse-code), or another coding agent:

```text
Install or update `/exp` from:
https://github.com/potatosalad/notes/tree/main/skills/exp

Use your user-level skills directory, copy every file, replace any existing
version, run `scripts/install-providers.sh`, and verify that `/exp` works.
```

The source is in [`skills/exp`](https://github.com/potatosalad/notes/tree/main/skills/exp):

* [`SKILL.md`](https://github.com/potatosalad/notes/blob/main/skills/exp/SKILL.md)
* [`scripts/exp-init.sh`](https://github.com/potatosalad/notes/blob/main/skills/exp/scripts/exp-init.sh)
* [`templates/ralph.sh`](https://github.com/potatosalad/notes/blob/main/skills/exp/templates/ralph.sh)
* [`templates/`](https://github.com/potatosalad/notes/tree/main/skills/exp/templates)
* [`providers/`](https://github.com/potatosalad/notes/tree/main/skills/exp/providers)

The installer links `claude-max`, `codex-max`, `muse-max`, and their `-stream` variants into `~/.local/bin`.  These wrappers select maximum effort and unattended operation.

### A Real Example

The following request started an experiment to investigate a multi-node Erlang segmentation fault:

```text
/exp new experiment `edf-1` with Codex (X)

In TASK.md:

Goal is to isolate multi-node segmentation fault while in ASAN/LSAN/UBSAN
mode with OTP 29 (or possibly OTP 28) and put together a report about the
bug, proposals for how to fix it, and a concise bug report that I can submit
upstream to Erlang/OTP. If there are bugs in the erldist_filter NIF itself,
we also need to patch them and write up a separate report about them.

- Clone https://github.com/WhatsApp/erldist_filter into
  `~/gitrepos/erldist_filter`
- Get the basics running `rebar3 ct`, make sure `just sanitizers` works and
  we're able to collect crash information if one of the nodes has a SIGSEGV
  during the spbt tests
- Stress test until we can force a SIGSEGV
- Hint: previous runs indicated that `NEW_FUN_EXT` may be to blame, but
  there may be other bugs hiding

Rules:
- NEVER message humans
- NEVER get stuck behind permission gates, keep moving forward

Write things in a brutally short TASK.md, DO NOT do the work for the harness
ahead of time. Commit, push, and start the harness.
```

The last instruction matters: `/exp` should prepare and start the harness, not do the research itself.

The harness ran 24 iterations over a few days and reduced the rare crash to a deterministic stock OTP reproducer with no NIF loaded.  The result was Erlang/OTP issue [#11416](https://github.com/erlang/otp/issues/11416), later fixed by [pull request #11417](https://github.com/erlang/otp/pull/11417).

## The Harness Loop

`ralph.sh` runs forever under a systemd user service.

Each experiment gets its own directory:

```text
my-experiment/
├── justfile
├── ralph.sh                       # The harness loop
├── my-experiment-harness.service
├── TASK.md                        # Read-only goal and requirements
├── STEER.md                       # Used once, then moved to archive/
├── HARNESS.md                     # Reflector-owned worker playbook
├── TODO.md                        # Worker-owned living checklist
├── NOTES.md                       # Reflector-owned durable lessons
├── TOOLS.md                       # Reflector-owned command index
├── CONFUSIONS.md                  # Open questions from the worker
├── experiments/
├── iterations/
├── notes/
├── tools/
├── confusions/
├── archive/                       # Consumed STEER.md files
├── cleanup/
└── .harness/
    ├── status.txt                 # working | done | stuck | abandoned
    ├── iteration.txt              # Current iteration number
    └── schedule.txt               # Agent schedule, such as X or CXM
```

### Key Rules

* `TASK.md` never changes.
* `STEER.md` applies once, then moves to `archive/`.
* Workers update `TODO.md`, `CONFUSIONS.md`, and `experiments/`.
* Reflectors update `HARNESS.md`, `NOTES.md`, `TOOLS.md`, and `.harness/`.
* `iterations/` stores logs and summaries.
* Status is `working`, `done`, `stuck`, or `abandoned`.
* Agent schedule may use `C` for Claude, `X` for Codex, and `M` for Muse.
  * For example: `CXM` rotates through all three.

The files are the state.  `ralph.sh` repeats:

1. **Worker:** Do one task and save evidence.
2. **Summarizer:** Write `iterations/NNN/summary.md`.
3. **Reflector:** Update the handoff and status.
4. **Challenger:** Verify `done`, or return to `working`.
5. **Committer:** Commit and optionally push.

Every tenth iteration, cleanup compacts the handoff and archives older details.

### Steering

In the `edf-1` example above, I noticed that the harness was spending too much time broadly stress testing, so I wrote a one-time `STEER.md`:

```markdown
Stop broad stress testing for the next iteration.

Concentrate on producing the smallest possible SIGSEGV reproducer and
verify whether the crash occurs without erldist_filter loaded.
```

The next iteration of the loop will read the `STEER.md` and archive it.

## What's Next?

Useful prior art, in chronological order:

* **July 2025:** [Ralph Wiggum](https://ghuntley.com/ralph/) is the original crude Bash loop: one task per fresh agent.
* **November 2025:** [Anthropic's long-running agent harness](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) uses an initializer, incremental workers, a progress file, and Git.
* **March 2026:** [autoresearch](https://github.com/karpathy/autoresearch) edits training code, runs fixed five-minute experiments, and keeps improvements.
* **March 2026:** [Meta-Harness](https://arxiv.org/abs/2603.28052) searches over harness code itself.  The [reference code](https://github.com/stanford-iris-lab/meta-harness) is public.
* **August 2026:** [LongHorizon-Harness](https://github.com/AMAP-ML/LongHorizon-Harness) uses a fresh executor and read-only auditor.  Its [paper](https://arxiv.org/abs/2608.01964) reports gains on three benchmarks.
* **August 2026:** [Argus](https://github.com/lbx154/Argus) uses four roles around durable state.  Its [report](https://arxiv.org/abs/2608.05144) reports roughly 78% on SWE-Bench Pro versus 59% for a direct Copilot baseline.

`/exp` is crude, but it usually gets the job done.  It gives me a repeatable way to run research beyond one context window while keeping the evidence reviewable.
