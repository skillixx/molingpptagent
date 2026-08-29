# Local service discovery

Treat all values as discoverable runtime state, not permanent constants.

## Current candidates

The repository currently uses environment-backed candidates for frontend, Main API, Outline, Content, and PersonalDB. MySQL and object storage may run in containers. Read root `.env`, `start.py`, listeners, process command lines, and Docker state before acting.

## Inventory requirements

For every candidate service capture:

- listener address and port;
- PID and parent PID;
- executable and complete command line;
- creation time;
- project-path evidence;
- health endpoint and result;
- Git release identity when the service exposes it.

The current `start.py` installs dependencies, terminates processes by occupied port, and launches the whole local stack. It does not prove process ownership before termination. Do not use it as the default targeted restart command.

## Restart selection

- Backend route, registration, or configuration change: consider Main API and only other code-owning components in the diff.
- Worker implementation change: consider the persistent Worker, preserving healthy APIs.
- Frontend source change: consider the frontend dev server or rebuilt static frontend.
- Template JSON or static assets: verify whether the consumer reads on demand before deciding a restart is necessary.
- Database, MinIO, Outline, Content, and PersonalDB stay running unless their own code/config changed or they are unhealthy.

Use the project's `.venv` and root `.env`. Record old PID, new PID, old commit, new commit, exact command, working directory, and logs for every restart.
