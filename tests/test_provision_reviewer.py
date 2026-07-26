from __future__ import annotations

import unittest
import uuid

from botocore.exceptions import ClientError
from sqlalchemy import func, select

from app.admin.provision_reviewer import ProvisioningError, provision_reviewer
from app.db.base import Base
from app.db.models import Organization, User
from app.db.session import create_database


class FakeCognitoClient:
    def __init__(self) -> None:
        self.users: dict[str, dict] = {}

    def admin_create_user(self, **request):
        username = request["Username"]
        if username in self.users:
            raise ClientError(
                {
                    "Error": {
                        "Code": "UsernameExistsException",
                        "Message": "User already exists",
                    }
                },
                "AdminCreateUser",
            )
        attributes = list(request["UserAttributes"])
        attributes.append({"Name": "sub", "Value": str(uuid.uuid4())})
        user = {"Username": username, "Attributes": attributes}
        self.users[username] = user
        return {"User": user}

    def admin_get_user(self, **request):
        user = self.users[request["Username"]]
        return {
            "Username": user["Username"],
            "UserAttributes": list(user["Attributes"]),
        }


class ProvisionReviewerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.database = create_database(database_url="sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.database.engine)
        self.client = FakeCognitoClient()
        self.organization_id = uuid.uuid4()

    def tearDown(self) -> None:
        self.database.dispose()

    def provision(self):
        with self.database.transaction() as session:
            return provision_reviewer(
                self.client,
                session,
                user_pool_id="ap-south-1_TEST",
                organization_id=self.organization_id,
                organization_name="InvoiceFlow Demo Finance",
                email="Reviewer@Example.com",
                display_name="Demo Reviewer",
            )

    def test_creates_matching_cognito_and_database_identity(self) -> None:
        result = self.provision()

        self.assertTrue(result.cognito_user_created)
        self.assertTrue(result.database_user_created)
        with self.database.transaction() as session:
            organization = session.get(Organization, self.organization_id)
            user = session.get(User, result.user_id)

        self.assertEqual(organization.name, "InvoiceFlow Demo Finance")
        self.assertEqual(user.organization_id, self.organization_id)
        self.assertEqual(user.external_subject, result.cognito_subject)
        self.assertEqual(user.email, "reviewer@example.com")
        self.assertNotIn("reviewer@example.com", str(result.safe_summary()))

    def test_rerun_reuses_both_identities(self) -> None:
        first = self.provision()
        second = self.provision()

        self.assertFalse(second.cognito_user_created)
        self.assertFalse(second.database_user_created)
        self.assertEqual(second.user_id, first.user_id)
        self.assertEqual(second.cognito_subject, first.cognito_subject)
        with self.database.transaction() as session:
            organization_count = session.scalar(select(func.count()).select_from(Organization))
            user_count = session.scalar(select(func.count()).select_from(User))
        self.assertEqual(organization_count, 1)
        self.assertEqual(user_count, 1)

    def test_rejects_existing_cognito_user_from_another_tenant(self) -> None:
        self.provision()

        with self.assertRaisesRegex(ProvisioningError, "another organization"):
            with self.database.transaction() as session:
                provision_reviewer(
                    self.client,
                    session,
                    user_pool_id="ap-south-1_TEST",
                    organization_id=uuid.uuid4(),
                    organization_name="Another Organization",
                    email="reviewer@example.com",
                    display_name="Demo Reviewer",
                )

    def test_rejects_tenant_name_change_on_rerun(self) -> None:
        self.provision()

        with self.assertRaisesRegex(ProvisioningError, "organization name"):
            with self.database.transaction() as session:
                provision_reviewer(
                    self.client,
                    session,
                    user_pool_id="ap-south-1_TEST",
                    organization_id=self.organization_id,
                    organization_name="Changed Organization",
                    email="reviewer@example.com",
                    display_name="Demo Reviewer",
                )


if __name__ == "__main__":
    unittest.main()
