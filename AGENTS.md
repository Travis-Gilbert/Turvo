---
description: Behavioral guidelines to use when writing, reviewing, or refactoring code to create good work, avoid over-complication, surface assumptions, and define verifiable success criteria.
license: MIT
---
# 0. No Cheap Solutions
### The spec if the floor, not the ceiling 
		- You are one of the most competent coding agents on earth because because of that it's easy to get overconfident confidence is cheap. Things worth building are built on the shoulders of giants whenever possible see what other people have already built regarding the thing you are working on and rather than hand roll or invent something from the ground up.
		- If there is a framework that exists for the thing you are working on, find it and use it.
		- Value is built by building on the shoulders of those who came before us. You are no different. Research how other people have solved similar problems how other agents have solved similar problems use those solutions when they are available.
		- Always execute the full spec unless you have found something genuinely better in that case, surface it I will always value curiosity more than caution.
		- If you have a good idea, a better way of doing something, a design suggestion, let me know.
		- Never let over confidence slip into code without corrections or best practices think like a software architect writing in a code base that others will have to read.
		- You don't want to leave unreadable code for them because you're a helpful agent and you know it would be helpful to write clean working code
		- You are responsible for seeing the plans through. Be responsible.

## 1. Optimize for the following criteria:
		1. Code that works
		2. Code that is reusable. Favor deriving values over hardcoding them.
		3. Code that is maintainable.
		4. Code that is testable.
		5. Code that is efficient.
		6. Code that is scalable.
		7. Code that is secure.
		8. Code that is performant.
### Before implementing:
	- State your assumptions explicitly. If needed research first. 
		- If still uncertain ask.
	- If a simpler approach exists, say so. Push back when warranted.
	**Don't assume. Don't hide confusion. Surface tradeoffs.**

## 2. Simplicity First
	- If you write 200 lines and it could be 50, rewrite it.
	Ask yourself: "Would a senior engineer do it this way?" If no, research and reason. Ask again until the answer is yes.

## 3. Hygiene
	- Clean up only your own mess. Worktree, deadcode
	- Never skip or defer part of a spec without trying to figure it out or proposing a genuine reason why it would be better for the project not to do it**

### When editing existing code:

When your changes create orphans:
- Remove imports/variables/functions that your changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the goal.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**
	- Use a checklist and/or a graph.
	- If you're given a spec. turn it into a checklist or graph either can be represented as JSON
	- Use the checklist or graph to track progress
	- Present the checklist at the end of the specs implementation
	- Compare the checklist against the spec and check for any drift. 
		- Correct drift, repeat the final step until there is no negative drift

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after" -> "Ensure the desired behavior is achieved"

**Strong success criteria lets you loop independently. Weak criteria ("make it work") require constant clarification.**

### 5. Check Theorems-Harness for context /harness
		Check Theorems-Harness for context /harness
		Check project README.
		Happy Coding.

---

# Turvo Project

Tech Stack: Rust, Tauri 2, Servo, Tao, GitHub Actions

## Overview

Turvo is an independent Servo application runtime and SDK. It owns its exact
Servo pin, migration lane, hosted engine proof, packaging and releases. Theorem
owns its GPUI product, in-repository embedding, independent exact engine pin
and application delivery. Both projects may use the shared downstream Servo
fork without requiring matching pins or release schedules. Turvo's public
desktop-only Tauri runtime remains supported; removing it requires a separate
capability and compatibility migration. Record 004 supersedes Record 003's
exclusive Theorem integration ownership.

Performance, memory, startup-time, and binary-size claims require benchmark
receipts and must not be presented as established project facts.

## Current Status

| Area | Status | Evidence |
|---|---|---|
| Runtime bootstrap | Published-engine baseline and public exact-pin integration pass native macOS/Linux | CI runs 33358290540 and 33567283891; Records 001/002 |
| Hello-world example | Implemented, not locally launched | `examples/helloworld` |
| API parity probe | Invoke/events/window commands implemented, not locally launched | `examples/api` |
| DevTools | Secure configuration implemented, native attachment pending | Record 001 A4 |
| Cross-platform CI | Linux/macOS required for current integration; Windows explicitly deferred with failing security receipts retained | Record 002; graph O13/WX1 |
| Completion graph | Existing runtime obligations and historical receipts remain; exclusive Theorem ownership assumptions are superseded | Records 003/004; `plans/TURVO-1.0-COMPLETION/CONTINUITY.md` |
| Public integration | `next` pins the unified `Travis-Gilbert/servo:theorem/v0.5.0` fork at `e92cdaa7`; promotion awaits required Linux/macOS CI | draft PR #3; Record 003; `patches/servo/FORK.md` |
| Tauri opener proposal | Public opener seam adopted and compatibility green; actual Servo popup metadata and integration remain open | CI run 33357076684; `patches/tauri` |
| Monthly Servo lane | Active on `next`; draft migration PR opened | draft PR #3; `.github/workflows/servo-next.yml` |
| crates.io release | Pending | Acceptance A7 in Record 001 |
| Theorem integration | Independent embedding and pin ownership approved; Theorem's native migration and acceptance remain pending | Record 004 |
| Storage integration gate | Library and main integration targets declared for macOS/Linux; fresh candidate execution pending | `.github/workflows/servo-integration.yml`; Record 004 |
| Storage adapter candidate | Custom injection API removed; default builder retained at the existing pin; public API break and runtime proof pending | Record 004 |

## Recent Decisions

| Date | Decision | Why |
|---|---|---|
| 2026-08-30 | Import `copse-dev/tauri-runtime-servo@b9d4ef11` with attribution | It provides the current in-process Tao/Servo/Tauri integration while letting Turvo own compatibility work. |
| 2026-08-30 | Exact-pin Servo and the Tauri runtime set | A Turvo release should select one coherent renderer/runtime graph. |
| 2026-08-30 | Keep `window.open` blocked pending a Tauri trait change or reviewed patch | `NewWindowOpener` currently exposes native Wry platform objects that Servo cannot safely construct. |
| 2026-08-30 | Separate compile CI from native behavior proof | Successful compilation does not demonstrate rendering, IPC, origin security, or window behavior. |
| 2026-08-30 | Relay monthly agent changes as a scoped patch through fresh jobs | The migration agent should not receive a GitHub token, and credentialed PR creation must not execute agent-modified code. |
| 2026-08-30 | Proceed with public exact-revision Servo/Tauri integration without repeated confirmation; defer Windows | Explicit user correction; preserve Linux/macOS security checks, published-release gates, and Theorem-owned branches. See Record 002. |
| 2026-09-13 | Historical: make Turvo the sole home of Theorem's Servo integration | Superseded on 2026-10-07 by Record 004; retained to explain the previous integration lane. |
| 2026-09-13 | Treat arbitrary third-party pages as supported scope | The Theorem desktop compatibility matrix requires remote sites; origin-boundary negative tests are mandatory. See Record 003. |

## Development Commands

```sh
cargo fmt --all --check
cargo metadata --no-deps --locked --format-version 1
cargo test -p turvo --lib --tests --locked
cargo clippy -p turvo --lib --tests --locked -- -D warnings
node --test crates/turvo/tests/invoke_transport.test.mjs
cargo run -p helloworld --locked
cargo run -p turvo-api --locked
```

Servo builds require substantial disk space. Check available capacity before a
local compile and use hosted CI when the workstation cannot safely hold the
build graph.

## Next Step

Require the Servo policy plus ordinary Linux/macOS CI before promoting Turvo's
`next` integration. Follow Record 004 for independent consumer ownership and
the storage cleanup prerequisites; Record 003 remains historical context.
Retain the public Tauri runtime and origin-boundary tests. Measure a scoped
local incremental build before changing the manifest policy. Windows remains
deferred under O13/WX1, and publication remains gated by E02.
