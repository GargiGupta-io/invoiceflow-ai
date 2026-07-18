from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TenantContext:
    """Trusted ownership context derived from authentication, never request IDs."""

    organization_id: uuid.UUID
    actor_id: uuid.UUID
