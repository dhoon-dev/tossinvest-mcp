"""Operational health endpoint helpers."""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import JSONResponse

from ._version import __version__


async def healthz(_request: Request) -> JSONResponse:
    """Return a lightweight health response without calling TossInvest APIs."""
    return JSONResponse(
        {
            "status": "healthy",
            "service": "tossinvest-mcp",
            "version": __version__,
        }
    )
