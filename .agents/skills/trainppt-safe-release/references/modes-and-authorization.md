# Modes and authorization

Use the narrowest mode that satisfies the user's current request.

| User intent | Mode | Authorized mutation |
|---|---|---|
| 判断、检查、评估 | `assess` | None |
| 提交代码 | `commit-local` | Local commit only |
| 推送远端、提交远程仓库 | `push-branch` | Remote branch update |
| 创建或更新 PR | `open-pr` | PR mutation |
| 合并到 main | `merge-main` | Base branch merge |
| 启动或重启项目 | `restart-local` | Exact owned local process set |
| 部署生产 | `deploy-production` | No production mutation until the specific sub-action is authorized |

## Non-transferable authority

- Commit does not imply push.
- Push does not imply PR or merge.
- Merge does not imply restart or deploy.
- Restart does not imply dependency installation, migration, or billing changes.
- Production deploy does not automatically authorize backup, build, migration, billing enablement, or rollback.
- Template development does not imply any Git or runtime mutation.

Read-only inspection, tests, diff review, process inventory, and health queries may run when relevant. Stop before a mutation that is not named or necessarily contained in the user's request.

## Hard stops

Stop for conflicts, non-fast-forward history, failed in-scope tests, unknown process ownership, missing production authorization, destructive Git requirements, or a verification failure that would make a completion claim false.
