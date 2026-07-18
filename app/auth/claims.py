from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class VerifiedIdentity:
    subject: str
    organization_id: uuid.UUID
    username: str | None
    scopes: frozenset[str]


class TokenVerifier(Protocol):
    def verify(self, token: str) -> VerifiedIdentity:
        """Verify a bearer token and return only normalized trusted claims."""
