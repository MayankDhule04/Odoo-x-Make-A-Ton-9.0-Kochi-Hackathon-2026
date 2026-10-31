"""Shared contract: every API route goes through require_role unless it is public.

If this fails for a route you added, protect it with AdminUser, StaffOrAdmin,
CurrentUser, CurrentCustomer or CurrentPrincipal from app.core.rbac. Add a route to
PUBLIC_ROUTES only if anonymous visitors genuinely need it, and say why.
"""

from fastapi import APIRouter, FastAPI
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute, iter_route_contexts

from app.core.rbac import CurrentUser, RBAC_ROLES_ATTR
from app.main import app

PUBLIC_ROUTES = {
    ("GET", "/api/health"),  # liveness check for Docker and the web app
    ("POST", "/api/auth/login"),  # anonymous by definition
}


def _requires_a_role(dependant: Dependant | None) -> bool:
    if dependant is None:
        return False
    if getattr(dependant.call, RBAC_ROLES_ATTR, None):
        return True
    return any(_requires_a_role(sub) for sub in dependant.dependencies)


def api_routes(application: FastAPI) -> list[tuple[str, str, Dependant | None]]:
    """(method, full path, dependency tree) for every API route, including routes from
    included routers. Since FastAPI 0.137, app.routes no longer lists those directly."""
    return [
        (method, context.path, context.dependant)
        for context in iter_route_contexts(application.routes)
        if isinstance(context.original_route, APIRoute)
        for method in sorted(context.methods or ())
    ]


def unprotected_routes(application: FastAPI, public: set[tuple[str, str]]) -> list[str]:
    return [
        f"{method} {path}"
        for method, path, dependant in api_routes(application)
        if (method, path) not in public and not _requires_a_role(dependant)
    ]


def test_every_non_public_route_requires_a_role() -> None:
    unprotected = unprotected_routes(app, PUBLIC_ROUTES)

    assert not unprotected, (
        f"These routes don't go through require_role: {unprotected}. Protect them with a "
        "dependency from app.core.rbac, or add them to PUBLIC_ROUTES with a reason."
    )


def test_public_routes_all_exist() -> None:
    existing = {(method, path) for method, path, _ in api_routes(app)}

    assert PUBLIC_ROUTES <= existing, f"Stale PUBLIC_ROUTES entries: {PUBLIC_ROUTES - existing}"


def test_the_guard_flags_an_unprotected_route_in_an_included_router() -> None:
    """Proves the check above can fail, so it never passes on an empty route list."""
    router = APIRouter(prefix="/things")

    @router.get("/open")
    def open_route() -> None: ...

    @router.get("/closed")
    def closed_route(user: CurrentUser) -> None: ...

    probe = FastAPI()
    probe.include_router(router, prefix="/api")

    assert unprotected_routes(probe, public=set()) == ["GET /api/things/open"]
