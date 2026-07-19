from __future__ import annotations

import argparse
import json
import os
import uuid
from dataclasses import dataclass
from typing import Any, Sequence

import boto3
from botocore.exceptions import ClientError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Organization, User
from app.db.session import create_database


class ProvisioningError(RuntimeError):
    """Raised when an existing identity conflicts with the requested tenant."""


@dataclass(frozen=True)
class CognitoIdentity:
    subject: str
    created: bool


@dataclass(frozen=True)
class ProvisionedReviewer:
    organization_id: uuid.UUID
    user_id: uuid.UUID
    cognito_subject: str
    cognito_user_created: bool
    database_user_created: bool

    def safe_summary(self) -> dict[str, str | bool]:
        return {
            "organization_id": str(self.organization_id),
            "user_id": str(self.user_id),
            "cognito_subject": self.cognito_subject,
            "cognito_user_created": self.cognito_user_created,
            "database_user_created": self.database_user_created,
        }


def _attributes(values: Sequence[dict[str, str]]) -> dict[str, str]:
    return {item["Name"]: item["Value"] for item in values}


def ensure_cognito_reviewer(
    client: Any,
    *,
    user_pool_id: str,
    organization_id: uuid.UUID,
    email: str,
    display_name: str | None,
) -> CognitoIdentity:
    normalized_email = email.strip().lower()
    attributes = [
        {"Name": "email", "Value": normalized_email},
        {"Name": "email_verified", "Value": "true"},
        {"Name": "custom:organization_id", "Value": str(organization_id)},
    ]
    if display_name:
        attributes.append({"Name": "name", "Value": display_name.strip()})

    created = True
    try:
        response = client.admin_create_user(
            UserPoolId=user_pool_id,
            Username=normalized_email,
            UserAttributes=attributes,
            DesiredDeliveryMediums=["EMAIL"],
            ForceAliasCreation=False,
        )
        user = response["User"]
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "UsernameExistsException":
            raise
        created = False
        user = client.admin_get_user(
            UserPoolId=user_pool_id,
            Username=normalized_email,
        )

    stored = _attributes(
        user.get("Attributes", user.get("UserAttributes", []))
    )
    if stored.get("custom:organization_id") != str(organization_id):
        raise ProvisioningError("The Cognito user belongs to another organization.")
    if stored.get("email", "").strip().lower() != normalized_email:
        raise ProvisioningError("The Cognito user email does not match the request.")

    subject = stored.get("sub", "").strip()
    if not subject:
        raise ProvisioningError("Cognito did not return a stable user subject.")
    return CognitoIdentity(subject=subject, created=created)


def ensure_database_reviewer(
    session: Session,
    *,
    organization_id: uuid.UUID,
    organization_name: str,
    cognito_subject: str,
    email: str,
    display_name: str | None,
) -> tuple[User, bool]:
    normalized_name = organization_name.strip()
    normalized_email = email.strip().lower()
    normalized_display_name = display_name.strip() if display_name else None

    organization = session.get(Organization, organization_id)
    if organization is None:
        session.add(Organization(id=organization_id, name=normalized_name))
        session.flush()
    elif organization.name != normalized_name:
        raise ProvisioningError("The organization name does not match the existing tenant.")

    subject_user = session.scalar(
        select(User).where(
            User.organization_id == organization_id,
            User.external_subject == cognito_subject,
        )
    )
    if subject_user is not None:
        if subject_user.email.strip().lower() != normalized_email:
            raise ProvisioningError("The Cognito subject is already linked to another email.")
        return subject_user, False

    email_user = session.scalar(
        select(User).where(
            User.organization_id == organization_id,
            User.email == normalized_email,
        )
    )
    if email_user is not None:
        raise ProvisioningError("The email is already linked to another Cognito subject.")

    user = User(
        organization_id=organization_id,
        external_subject=cognito_subject,
        email=normalized_email,
        display_name=normalized_display_name,
        is_active=True,
    )
    session.add(user)
    session.flush()
    return user, True


def provision_reviewer(
    client: Any,
    session: Session,
    *,
    user_pool_id: str,
    organization_id: uuid.UUID,
    organization_name: str,
    email: str,
    display_name: str | None,
) -> ProvisionedReviewer:
    identity = ensure_cognito_reviewer(
        client,
        user_pool_id=user_pool_id,
        organization_id=organization_id,
        email=email,
        display_name=display_name,
    )
    user, database_created = ensure_database_reviewer(
        session,
        organization_id=organization_id,
        organization_name=organization_name,
        cognito_subject=identity.subject,
        email=email,
        display_name=display_name,
    )
    return ProvisionedReviewer(
        organization_id=organization_id,
        user_id=user.id,
        cognito_subject=identity.subject,
        cognito_user_created=identity.created,
        database_user_created=database_created,
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create one Cognito reviewer and its matching PostgreSQL tenant identity."
    )
    parser.add_argument("--organization-id", required=True, type=uuid.UUID)
    parser.add_argument("--organization-name", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--display-name")
    parser.add_argument(
        "--user-pool-id",
        default=os.environ.get("COGNITO_USER_POOL_ID", ""),
    )
    args = parser.parse_args(argv)
    if not args.organization_name.strip():
        parser.error("--organization-name cannot be empty")
    if "@" not in args.email or not args.email.strip():
        parser.error("--email must be a valid reviewer email")
    if not args.user_pool_id.strip():
        parser.error("--user-pool-id or COGNITO_USER_POOL_ID is required")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    settings = get_settings()
    database = create_database(settings)
    client = boto3.client("cognito-idp", region_name=settings.aws_region)
    try:
        with database.transaction() as session:
            result = provision_reviewer(
                client,
                session,
                user_pool_id=args.user_pool_id.strip(),
                organization_id=args.organization_id,
                organization_name=args.organization_name,
                email=args.email,
                display_name=args.display_name,
            )
        print(json.dumps(result.safe_summary(), sort_keys=True))
        return 0
    finally:
        database.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
