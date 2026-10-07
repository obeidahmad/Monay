"""Liveness + version."""

from __future__ import annotations

from fastapi import APIRouter

from monay import __version__
from monay.api.schemas import HealthOut

router = APIRouter(tags=["meta"])


@router.get("/health")
def health() -> HealthOut:
    """Answers once the app has started (and so has migrated its database)."""
    return HealthOut(status="ok", version=__version__)
