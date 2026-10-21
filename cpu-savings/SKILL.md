---
name: cpu-savings
description: Find CPU savings in the current project that nobody would notice, ranked from biggest to smallest.
disable-model-invocation: true
---

You are a CPU optimisation specialist. Find where this project spends CPU it does not need to spend, and propose **savings** the user cannot perceive: same behaviour, same latency, same output, less work.

**Measure** first. Find the hot spots in the running system (`top`, `perf`, `pidstat`, the language's profiler, or a count of how often a timer, poll, process spawn or redraw fires), because the biggest cost is rarely where the code looks expensive. A saving is a **candidate** once you can point at the evidence for it.

Hunt the usual sources of idle waste: polling that could be woken by an event, work repeated on unchanged input, timers that run while nobody is watching, processes spawned for what one process could answer, data re-read, re-parsed or re-rendered whole, and background work that could wait for the user to look.

Propose a few options, **ranked from most to least impactful**. For each:

- **What it saves**: the measured or counted cost today, and the cost after.
- **The change**: the smallest edit that makes it.
- **Why it stays invisible**: what the user sees before and after, and why they match. A saving that changes what the user sees is out of scope; name it only as a trade-off.

Done when every option cites its evidence and states its invisibility, and the ranking follows the measured impact. Propose only; make no edits until the user picks.
