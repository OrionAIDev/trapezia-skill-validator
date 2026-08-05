# Phase 2 — Protection Group Implementation Plan

> **For agentic workers:** this is an **ops/investigation** plan (remote Docker + live
> discovery on `hermeslab`), not a code-TDD plan — "tests" here are verification commands
> against a live container with expected output, and several tasks produce **documented
> findings**, not application code. Execute task-by-task; each task's live verification is
> the pass/fail gate, not a pytest run.

**Goal:** Prove Phase 2's core, still-unproven thesis element — *"delivered skills are
corruption-proof by filesystem (ro-mount/lock), not by agent judgment"* — against the live
`hermeslab` container, and close the four open checkboxes under #128's protection group:
ro-mount the three delivered insure skills, verify `skill_manage` fails cleanly on the ro
mount (no retry loop), verify name-shadowing behavior, and verify redeploy-vs-pending-writes
behavior.

**Roadmap:** `OrionAIDev/trapezia-roadmap#128`, Phase 2. Tier (a)/(b) e2e work is out of
scope for this plan — see `docs/superhuman/notes/2026-08-05-tier-a-webhook-investigation.md`
for that decision.

**Server access:** `ssh root@100.117.27.98` (Tailscale, preferred) or
`ssh root@204.168.222.57` (public).

---

## What was found investigating this (corrects the original #128 scoping)

1. **`skills.write_approval: true` and `skills.guard_agent_created: true` are already
   live** on `hermeslab` (`hermes config get skills` confirms both `true` — KQ-1's earlier
   verification). Nothing to enable; this plan only needs to exercise the behavior.
2. **F-7's native drift-detection (`list-modified` / `diff` / `repair-official` / `audit`)
   does NOT cover our delivered skills.** `hermes skills list` shows all three insure
   skills as `Source: local, Trust: local`; `hermes skills audit` reports *"No hub-installed
   skills to audit."* `list-modified`/`diff`/`repair-official` are scoped to **bundled**
   (official, shipped-with-Hermes) skills, and `audit`/`check`/`update` to **hub-installed**
   skills (from `skills.sh`/registries/taps). Our skills are neither — they were copied in
   directly. **Ro-mount is therefore the only protection lever for these skills, not
   "ro-mount + native repair" as #128 originally framed.** This is a real narrowing of the
   thesis, not a blocker: ro-mount alone is still a filesystem-level, agent-judgment-
   independent guarantee, which is the actual claim being tested.
3. **The single compose volume forces a layered-bind design.** `docker-compose-hermeslab.yml`
   mounts one volume for all of Hermes' state (`/opt/hermeslab/data:/opt/data` — config,
   sessions, memories, skills, logs together). Making the whole volume `:ro` breaks the
   process (`state.db` writes, logs, session files). The three delivered skill directories
   must each get their **own** `:ro` bind, layered on top of the base `rw` mount, so only
   those specific subtrees are immutable from inside the container while everything else
   (including the host side of those same directories) stays writable.
4. **Read `src/trapezia_skill_validator` / Hermes source, not assumptions, for the actual
   write path** (`/opt/hermes/tools/skill_manager_tool.py`,
   `/opt/hermes/tools/write_approval.py` inside the `hermeslab` container):
   - `skill_manage(action, name, ...)` — the tool the agent calls for `create` / `edit` /
     `patch` / `delete` / `write_file` / `remove_file`.
   - The **write-approval gate runs first**, before any of the action handlers (including
     `_create_skill`'s own name-collision check). When `write_approval: true`, every
     `skill_manage` call for these six actions **stages** immediately
     (`write_approval.stage_write` → a JSON record under the pending-skills store) and
     returns `{"staged": true, "pending_id": ...}` — it never touches the filesystem at
     stage time. **Consequence: a staged `create` is not collision-checked until approval
     time**, and a staged `edit`/`patch`/`write_file` against a ro-mounted skill is not
     filesystem-checked until approval time either. This is a real, worth-flagging gap in
     Hermes' own staging validation, not something to fix here — but it shapes the test
     design (Tasks 3–5 must go through stage **and** approve, not just stage).
   - Approval replays the original call via `apply_skill_pending`, which sets a context-var
     bypass and re-invokes `skill_manage` with the gate short-circuited — so the **real**
     filesystem write (and, for `create`, the real collision check) only happens here.
   - The actual write is `_atomic_write_text`: `tempfile.mkstemp(dir=file_path.parent, ...)`
     followed by `os.replace()`. On a read-only bind, `mkstemp` itself raises
     `OSError`/`PermissionError` (errno 30) **before any partial write occurs** — the
     function's `except Exception: ... raise` only cleans up the temp file and re-raises,
     it does not retry or swallow the error. This is the code-level basis for "fails
     cleanly, no retry loop"; Task 3 confirms it holds true end-to-end through the actual
     approval surface (Discord `/skills approve`), not just in isolation.
   - `_create_skill`'s collision check (`_find_skill(name)` across **all** skill
     directories, ro or rw) runs before any directory is created — so a same-name `create`
     against an existing ro skill fails cleanly with `"A skill named '<name>' already
     exists..."` and never creates an orphan directory. This is what Task 4 verifies live.

---

## Guardrails

- **This mutates live `hermeslab` config and requires a container recreate.** Confirm with
  Chris before Task 2 executes (Task 0/1 are read-only reconnaissance and can proceed
  without a separate check-in).
- **Compose changes go in `orion-compose`** (`~/dev/orion-compose`,
  `docker-compose-hermeslab.yml`), never hand-edited only on the server — mirror Phase 0's
  convention so the change survives a redeploy.
- **No PHI; insure domain only.** Unaffected by this work either way.
- **`hermestest` is untouched.** This plan targets `hermeslab` only — `hermestest` mirrors
  Discord-fidelity infra, not the protection group.
- **Normalize ownership before ro-mounting, not after.** `ls -la /opt/data/skills/insure/`
  shows mixed ownership (`trapezia-commercial-policy-check` and the `insure/` dir itself are
  `root:root`; `policy-form-lister` / `policy-declarations-check` are `hermes:hermes`, uid
  10000 per F-8). Ownership doesn't affect *read* access for either, but normalize to
  `10000:10000` (matching F-8's baked-in convention) before flipping to `:ro` so the state
  is unambiguous if ever reverted to `:rw`.
- **Every live test that mutates state must be reversible or already-intended-permanent.**
  Prefer creating throwaway test skills (unique, obviously-scoped names like
  `zz-protection-test-*`) over touching the three real delivered skills where a test doesn't
  specifically require targeting one of them.

---

### Task 0: Pre-flight — resolve the pending-store path, snapshot current state

**Verification, not code.**

- [ ] **Step 1: Trigger one real staged write to resolve where pending records actually
  land.** Nothing has staged yet (`/opt/data/pending` doesn't exist — confirmed live). Via
  Discord, ask HermesLab to create a throwaway skill (`zz-protection-test-preflight`, trivial
  content, no category collision). Expect a `staged: true` reply with a `pending_id`.

  Run: `docker exec hermeslab find /opt/data -iname "*pending*" -not -path "*/logs/*"`
  Expected: a `pending/skills/<pending_id>.json` (or equivalent) path appears. Record the
  exact path — earlier docs guessed `~/.hermes/pending/skills/`; confirm the real one.

- [ ] **Step 2: Reject the preflight staged write** via `/skills reject <pending_id>` so it
  never lands, then confirm: `hermes skills list | grep zz-protection-test-preflight` →
  no output.

- [ ] **Step 3: Snapshot the three delivered skills' current content + ownership** for
  before/after comparison:

  ```bash
  docker exec hermeslab sh -c "sha256sum /opt/data/skills/insure/*/SKILL.md; ls -la /opt/data/skills/insure/"
  ```
  Save the output in the eventual validation note.

Commit: none (recon only).

---

### Task 1: Normalize skill-directory ownership

- [ ] **Step 1:** `docker exec hermeslab id hermes` → confirm uid:gid (expect `10000:10000`
  per F-8).
- [ ] **Step 2:** `docker exec -u root hermeslab chown -R 10000:10000 /opt/data/skills/insure`
- [ ] **Step 3: Verify.** `docker exec hermeslab ls -la /opt/data/skills/insure/` → all three
  skill dirs + the `insure/` dir itself owned `hermes:hermes` (10000:10000).
- [ ] **Step 4: Verify skills still load correctly post-chown** (ownership change alone
  shouldn't affect anything, but confirm before compounding with the mount change):
  `hermes skills list | grep insure` → all three still `enabled`.

Commit: none (server-side only; no repo artifact for a chown).

---

### Task 2: Add the layered ro-bind mounts

**Requires Chris's go-ahead — this recreates the live `hermeslab` container.**

**Files:**
- Edit: `~/dev/orion-compose/docker-compose-hermeslab.yml` — add three `:ro` binds after the
  base volume, one per delivered skill:

  ```yaml
  volumes:
    - /opt/hermeslab/data:/opt/data
    - /opt/hermeslab/data/skills/insure/trapezia-commercial-policy-check:/opt/data/skills/insure/trapezia-commercial-policy-check:ro
    - /opt/hermeslab/data/skills/insure/policy-form-lister:/opt/data/skills/insure/policy-form-lister:ro
    - /opt/hermeslab/data/skills/insure/policy-declarations-check:/opt/data/skills/insure/policy-declarations-check:ro
  ```

  (Each source path is the same host directory the base volume already exposes — Docker
  layers a more specific bind on top of a broader one at the kernel mount-namespace level,
  so reads still pass through untouched and only writes under the three subpaths are
  blocked. The **host** side of those directories is untouched by `:ro` — only the
  in-container view is immutable.)

- [ ] **Step 1: Apply the compose change**, commit it in `orion-compose`, then on the server:
  `docker compose -f /opt/orion/docker-compose-hermeslab.yml up -d` (recreate).
- [ ] **Step 2: Verify the mounts landed.**
  `docker exec hermeslab mount | grep insure` → three `ro` entries.
- [ ] **Step 3: Verify reads still work.**
  `docker exec hermeslab cat /opt/data/skills/insure/policy-form-lister/SKILL.md | head -5`
  → succeeds; content unchanged from Task 0's snapshot.
- [ ] **Step 4: Verify writes are blocked at the OS level** (sanity check before testing
  through the agent):
  `docker exec hermeslab sh -c "touch /opt/data/skills/insure/policy-form-lister/probe 2>&1"`
  → `Read-only file system`. `docker exec hermeslab sh -c "touch /opt/data/skills/policy-form-lister-does-not-exist/probe 2>&1; touch /opt/data/skills/probe 2>&1"` at a **non**-ro path
  → succeeds (confirms the rest of `/opt/data` is still writable, i.e. the layering worked
  and didn't over-broadly lock the volume). Clean up the second probe file.
- [ ] **Step 5: Verify HermesLab still functions end-to-end** — repeat the F-9 Discord
  `health`-tool check (`use the trapezia-commercial-policy-check health tool...`) → same
  JSON as before. Confirms the ro-mount didn't break MCP registration or agent startup.

Commit (in this repo): none — infra lives in `orion-compose`. Update the deploy note if
`orion-compose`'s own README/runbook expects one (check when executing).

---

### Task 3: `skill_manage` fails cleanly on the ro mount — no retry loop

**Goal:** confirm the code-level analysis above (stage → approve → clean single exception,
no auto-retry) holds through the real approval surface.

- [ ] **Step 1: Stage an edit against a real ro-mounted skill.** Via Discord:
  *"edit the policy-form-lister skill's SKILL.md, append one harmless sentence to the
  description"*. Expect `staged: true` + `pending_id` (the gate short-circuits before
  touching the ro path — matches the code read above; staging itself must succeed
  regardless of the mount).
- [ ] **Step 2: Approve it** via `/skills approve <pending_id>` (the real filesystem write
  now attempts, and must fail against the ro mount).
- [ ] **Step 3: Assert clean failure.**
  - The agent/CLI surfaces **one** error (not a hang, not an unhandled traceback dumped to
    the user, not the session crashing) — capture the exact user-facing text.
  - `docker exec hermeslab tail -50 /opt/data/logs/errors.log` → exactly one
    `PermissionError`/`OSError: [Errno 30] Read-only file system` entry for this action, not
    a burst of repeated attempts (which would indicate an internal retry loop).
  - **Content unchanged:** `sha256sum` of `policy-form-lister/SKILL.md` matches Task 0's
    snapshot.
  - **No orphan temp file:** `ls -la /opt/data/skills/insure/policy-form-lister/` shows no
    stray `.SKILL.md.tmp.*` (confirms `mkstemp` itself failed, as predicted — it never got
    far enough to create a temp file to clean up).
  - **The pending record itself is resolved**, not left dangling forever in a
    half-approved state: `hermes skills list-pending` (or equivalent — confirm the exact
    surface in Task 0) shows the record either removed or marked failed, not stuck
    "pending" after a completed approve attempt.
- [ ] **Step 4: Confirm the agent does not automatically retry the same write in the same
  turn** — read the transcript of the turn that triggered the approval replay; the agent
  should report the failure and stop, not immediately re-issue `skill_manage(edit, ...)`
  in a loop. (This is an LLM-behavior observation, not a code guarantee — record what
  actually happened.)

Document outcome in the validation note (Task 6).

---

### Task 4: Name-shadowing

**Goal:** confirm an agent cannot create a same-named skill that shadows a delivered one,
and that the failure is clean (no orphan directory, no silent precedence ambiguity).

- [ ] **Step 1: Stage a `create` with a colliding name.** Via Discord: *"create a new skill
  named `policy-form-lister` that just prints hello"* (deliberately colliding with the real,
  ro-mounted skill). Per the code read, the gate stages this **without** running the
  collision check (gate runs before `_create_skill`). Expect `staged: true`.
- [ ] **Step 2: Approve it.** Replay now runs `_create_skill` → `_find_skill('policy-form-lister')`
  finds the existing ro skill → returns `{"success": false, "error": "A skill named
  'policy-form-lister' already exists at ..."}` **before** `mkdir`/`_atomic_write_text` run.
- [ ] **Step 3: Assert.**
  - Clean rejection message reaches the user/agent (not a raw exception).
  - `docker exec hermeslab ls /opt/data/skills/insure/` → still exactly the original three
    directories — no new directory created anywhere (check the default/no-category skill
    root too, e.g. `/opt/data/skills/`, in case `_resolve_skill_dir` would have picked a
    different parent).
  - `sha256sum` of the real `policy-form-lister/SKILL.md` unchanged.
  - `hermes skills list | grep policy-form-lister` → exactly one row, pointing at the
    original ro path.

Document outcome in the validation note.

---

### Task 5: Redeploy vs. pending writes

**Goal:** confirm an operator redeploy (host-side, outside the container) always wins over
a stale pending write, and that ro-mount protection holds across a redeploy cycle — this is
the actual "corruption-proof by filesystem, not by agent judgment" claim in end-to-end form.

- [ ] **Step 1: Stage (but do not approve) an edit** against `policy-declarations-check`
  (different skill from Tasks 3–4, to keep evidence isolated) — same staging move as Task 3
  Step 1. Leave it pending.
- [ ] **Step 2: Perform a real operator redeploy** of `policy-declarations-check` from the
  **host** side while the container is running: regenerate via
  `trapezia-skill-gen` in this repo (or hand-edit a harmless, clearly-marked line for the
  test) and `scp`/copy the new `SKILL.md` to
  `/opt/hermeslab/data/skills/insure/policy-declarations-check/SKILL.md` directly (root on
  the host, not through the container). No container restart required — the mount is a
  live passthrough to the same host path.
- [ ] **Step 3: Verify the redeploy took effect** despite the container-side `:ro` mount:
  `docker exec hermeslab cat /opt/data/skills/insure/policy-declarations-check/SKILL.md` →
  shows the new content. Confirms `:ro` is container-side-only, exactly as designed — the
  deploy path (host writes) and the agent-write path (container writes) are genuinely
  separate, which is the property #128 is asking to prove.
- [ ] **Step 4: Now approve the stale pending edit from Step 1.** It targets content that no
  longer matches what it was staged against. Assert it **still fails the same way** as
  Task 3 (ro-mount blocks it regardless of what changed underneath) — i.e., the redeploy is
  never silently clobbered by an old pending approval landing after it. Confirm via
  `sha256sum`: matches the Step 2 redeployed content, not the pre-redeploy content and not
  whatever the stale pending record would have produced.
- [ ] **Step 5: Clean up** — discard any leftover pending records from this task.

Document outcome in the validation note.

---

### Task 6: Validation note + roadmap update

- [ ] **Step 1:** Write
  `docs/superhuman/notes/2026-08-05-phase2-protection-validation.md` (or dated to the actual
  execution date) covering: the ro-mount mechanism as implemented, exact command
  transcripts/output for Tasks 3–5, the F-7-scope correction, the "gate runs before
  collision/filesystem checks" finding (flag as a Hermes staging-validation gap worth
  knowing, not something this POC fixes), and the resolved pending-store path from Task 0.
- [ ] **Step 2:** Update `OrionAIDev/trapezia-roadmap#128` — check off the four protection
  checkboxes, update "Current state," and fold in the corrected F-7 scoping so it doesn't
  mislead a future reader the way the tier-(a) framing did.
- [ ] **Step 3:** Per the standing session-handoff habit, update the `multi-harness-poc`
  project memory and hand off a kickoff prompt for whatever Phase 2 (tier-(b) strengthening)
  or Phase 3 work is next.

Commit: `git add docs/superhuman/notes/2026-08-05-phase2-protection-validation.md` +
roadmap edit. Push and confirm CI green (this plan doesn't touch `src/`, so CI should be a
no-op pass, but confirm per the trapezia-disciplines convention anyway).
