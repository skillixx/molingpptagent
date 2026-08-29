# Production release routing

The repository root `README_PRODUCTION.md` is the production source of truth. Read it in full for a production request. Do not copy its commands into this Skill because confirmation tokens, database versions, endpoints, and deployment mechanics can change.

## Separate gates

Obtain explicit authority independently for:

1. production backup;
2. image or application build;
3. database migration;
4. deployment and service restart;
5. real billing enablement;
6. rollback.

The production preflight is read-only and does not grant authority for later steps. Never downgrade the production database, delete persistent data, copy `.env` into Git or logs, or claim Gate C5 from repository tests alone.

Production completion requires the current manual's release identity, dependency readiness, Worker identity, static frontend, database, billing, monitoring, and rollback evidence.
