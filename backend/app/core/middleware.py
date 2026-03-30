"""Application middleware for tenant resolution, locale, and request logging."""

import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Add request context (tenant, locale, timing) to each request."""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Extract locale from header or query param
        locale = request.headers.get("Accept-Language", "en")[:2]
        if locale not in ("en", "ar"):
            locale = "en"
        request.state.locale = locale

        # Extract tenant from header (Phase 2: resolve from subdomain)
        tenant_id = request.headers.get("X-Tenant-ID")
        request.state.tenant_id = tenant_id

        response = await call_next(request)

        # Add timing header
        duration = time.time() - start_time
        response.headers["X-Process-Time"] = f"{duration:.3f}"
        return response
