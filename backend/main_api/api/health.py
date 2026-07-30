"""T21 存活与就绪路由。"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..core.health import HealthService


def create_health_router(
    service: HealthService,
    *,
    release_commit: str | None = None,
    release_channel: str = "development",
) -> APIRouter:
    router = APIRouter(tags=["health"])

    @router.get("/healthz", summary="进程存活检查")
    def liveness():
        content = {
            "status": "ok",
            "component": "main_api",
            "release_channel": release_channel,
        }
        if release_commit is not None:
            content["release_commit"] = release_commit
        return content

    @router.get("/readyz", summary="关键依赖就绪检查")
    def readiness():
        ready, dependencies = service.readiness()
        return JSONResponse(
            status_code=200 if ready else 503,
            content={
                "status": "ready" if ready else "not_ready",
                "component": "main_api",
                "release_channel": release_channel,
                **({"release_commit": release_commit} if release_commit is not None else {}),
                "dependencies": dependencies,
            },
            headers={"Cache-Control": "no-store"},
        )

    return router


__all__ = ["create_health_router"]
