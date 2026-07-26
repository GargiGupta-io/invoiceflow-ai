from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User


class UserRepository:
    def __init__(self, session: Session, organization_id: uuid.UUID) -> None:
        self.session = session
        self.organization_id = organization_id

    def find_active_by_subject(self, external_subject: str) -> User | None:
        statement = select(User).where(
            User.organization_id == self.organization_id,
            User.external_subject == external_subject,
            User.is_active.is_(True),
        )
        return self.session.scalar(statement)
