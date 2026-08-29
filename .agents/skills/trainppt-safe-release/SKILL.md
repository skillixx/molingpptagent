---
name: trainppt-safe-release
description: Assess, commit, push, open PRs, merge, restart, or deploy TrainPPTAgent safely with explicit per-operation authorization, fast-forward checks, process ownership verification, minimal restarts, and end-to-end health evidence. Do not use for ordinary code edits when no release or runtime action is requested.
---

# TrainPPTAgent Safe Release

Safely move verified TrainPPTAgent changes through Git and runtime operations without widening the user's authorization.

## Route the mode

- `assess`: read-only Git, test, diff, credential, conflict, and runtime readiness checks.
- `commit-local`: create a local commit only after the user asks to commit.
- `push-branch`: push an already committed branch only after the user asks for a remote push.
- `open-pr`: create or update a PR only after the user asks for a PR or an explicitly PR-based remote workflow.
- `merge-main`: merge only after the user explicitly asks to merge to `main`.
- `restart-local`: stop or start only verified TrainPPTAgent processes after an explicit restart request.
- `deploy-production`: follow the repository production manual; every production action keeps its own authorization gate.

Read [references/modes-and-authorization.md](references/modes-and-authorization.md) before every mutating mode. A message can authorize multiple named actions, but unnamed actions remain unauthorized.

## Readiness sequence

1. Preserve unrelated tracked and untracked work.
2. Run `scripts/verify-git-readiness.ps1` or equivalent read-only checks.
3. Use fresh tests proportional to the diff; never treat stale output as current evidence.
4. Prefer a PR and repository checks. A direct merge is allowed only when explicitly requested and `--ff-only` is possible.
5. Record the old and intended commits before a merge or restart.
6. Before runtime changes, run `scripts/inventory-runtime.ps1` and read [references/local-service-map.md](references/local-service-map.md).
7. Verify exact PID, command line, working directory or repository ownership before stopping a process.
8. Restart only components affected by the diff. Do not use `start.py` as the default targeted restart path.
9. After restart or deploy, run `scripts/verify-runtime.ps1` and apply [references/runtime-verification.md](references/runtime-verification.md).

## Merge invariants

- Never force-push, reset hard, clean, or silently discard changes.
- Fetch the base immediately before the final merge check when network access is authorized.
- Stop on non-fast-forward history, conflicts, failed tests, missing required CI, or unexpected remote drift.
- Keep the feature branch unless the user separately asks to delete it.
- Do not describe a local merge as a successful remote merge until the remote commit is verified.

## Runtime invariants

- Port ownership alone is insufficient. Verify PID, command line, process age, project path, and expected service.
- Prefer the project `.venv` and root `.env`; do not assume system Python has project dependencies.
- `/healthz` alone is insufficient. Verify the database, Worker, Agents, business boundaries, frontend proxy, template list, and release identity.
- A failed start remains failed until a new listening process and the complete verification chain pass.

## Production boundary

For production, read [references/production-release.md](references/production-release.md) and the repository `README_PRODUCTION.md`. Backup, build, migration, deploy/restart, billing enablement, and rollback are separately authorized operations. Do not recreate production implementation inside this Skill.

## Independent audit

For a risky merge or restart, dispatch the read-only `release-runtime-auditor` defined in [references/subagent-contracts.md](references/subagent-contracts.md). The main Agent retains all Git writes and process control. `INCONCLUSIVE` never counts as a pass.

## Completion report

Report the exact branch and commit, operations actually performed, fresh test evidence, runtime evidence, retained rollback point, and anything not verified. Never claim production completion from repository tests or a local health endpoint alone.
