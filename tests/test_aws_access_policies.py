from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPOSITORY_ROOT / "scripts" / "render_aws_access_policies.py"
SPEC = importlib.util.spec_from_file_location("render_aws_access_policies", SCRIPT_PATH)
assert SPEC and SPEC.loader
POLICY_RENDERER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(POLICY_RENDERER)


class AwsAccessPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.arguments = argparse.Namespace(
            account_id="123456789012",
            aws_region="ap-south-1",
            developer_user="invoiceflow-developer",
            deploy_role="InvoiceFlowTerraformDeployRole",
            project_name="invoiceflow",
            environment="showcase",
            state_bucket=None,
            lock_table="invoiceflow-terraform-locks",
            task_boundary_policy_name="InvoiceFlowTaskBoundary",
        )

    def _render(self, output_dir: Path) -> dict[str, dict]:
        paths = POLICY_RENDERER.render_policies(
            template_dir=REPOSITORY_ROOT / "infra" / "terraform" / "access",
            output_dir=output_dir,
            replacements=POLICY_RENDERER.build_replacements(self.arguments),
        )
        return {
            path.name: json.loads(path.read_text(encoding="utf-8")) for path in paths
        }

    def test_developer_can_only_assume_the_deployment_role(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            documents = self._render(Path(temporary_directory))

        policy = documents["developer-assume-role-policy.json"]
        self.assertEqual(
            policy["Statement"],
            [
                {
                    "Sid": "AssumeInvoiceFlowTerraformRole",
                    "Effect": "Allow",
                    "Action": "sts:AssumeRole",
                    "Resource": (
                        "arn:aws:iam::123456789012:role/"
                        "InvoiceFlowTerraformDeployRole"
                    ),
                }
            ],
        )

    def test_role_trusts_only_the_named_developer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            documents = self._render(Path(temporary_directory))

        trust = documents["deployer-trust-policy.json"]
        statement = trust["Statement"][0]
        self.assertEqual(
            statement["Principal"]["AWS"],
            "arn:aws:iam::123456789012:user/invoiceflow-developer",
        )
        self.assertEqual(statement["Action"], "sts:AssumeRole")

    def test_deployment_policy_has_no_administrator_or_user_management(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            documents = self._render(Path(temporary_directory))

        policy = documents["terraform-deploy-policy.json"]
        actions = {
            action
            for statement in policy["Statement"]
            for action in (
                statement["Action"]
                if isinstance(statement["Action"], list)
                else [statement["Action"]]
            )
        }
        self.assertNotIn("*", actions)
        self.assertNotIn("iam:*", actions)
        self.assertNotIn("iam:CreateUser", actions)
        self.assertNotIn("iam:CreateAccessKey", actions)
        self.assertNotIn("iam:CreatePolicy", actions)
        self.assertNotIn("organizations:*", actions)
        self.assertNotIn("cloudfront:*", actions)
        self.assertNotIn("s3:PutBucketEncryption", actions)
        self.assertNotIn("s3:PutBucketLifecycleConfiguration", actions)
        self.assertIn("cloudfront:CreateDistribution", actions)
        self.assertIn("cloudfront:UpdateDistribution", actions)
        self.assertIn("elasticloadbalancing:CreateRule", actions)
        self.assertIn("iam:PassRole", actions)
        self.assertIn("ec2:Describe*", actions)
        self.assertIn("ec2:GetManagedPrefixListEntries", actions)
        self.assertIn("s3:PutEncryptionConfiguration", actions)
        self.assertIn("s3:PutLifecycleConfiguration", actions)

        object_statement = next(
            statement
            for statement in policy["Statement"]
            if statement["Action"] == "s3:GetObject"
        )
        self.assertNotIn("*", object_statement["Resource"])

        create_role_statement = next(
            statement
            for statement in policy["Statement"]
            if statement["Action"] == "iam:CreateRole"
        )
        self.assertEqual(
            create_role_statement["Condition"]["ArnEquals"][
                "iam:PermissionsBoundary"
            ],
            "arn:aws:iam::123456789012:policy/InvoiceFlowTaskBoundary",
        )

        create_distribution_statement = next(
            statement
            for statement in policy["Statement"]
            if "cloudfront:CreateDistribution"
            in (
                statement["Action"]
                if isinstance(statement["Action"], list)
                else [statement["Action"]]
            )
        )
        self.assertEqual(create_distribution_statement["Resource"], "*")
        self.assertEqual(
            create_distribution_statement["Condition"]["StringEquals"][
                "aws:RequestTag/Application"
            ],
            "invoiceflow",
        )

        update_distribution_statement = next(
            statement
            for statement in policy["Statement"]
            if "cloudfront:UpdateDistribution"
            in (
                statement["Action"]
                if isinstance(statement["Action"], list)
                else [statement["Action"]]
            )
        )
        self.assertEqual(
            update_distribution_statement["Resource"],
            "arn:aws:cloudfront::123456789012:distribution/*",
        )
        self.assertEqual(
            update_distribution_statement["Condition"]["StringEquals"][
                "aws:ResourceTag/Environment"
            ],
            "showcase",
        )

    def test_task_boundary_caps_runtime_roles_to_invoiceflow_services(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            documents = self._render(Path(temporary_directory))

        boundary = documents["task-permissions-boundary-policy.json"]
        actions = {
            action
            for statement in boundary["Statement"]
            for action in (
                statement["Action"]
                if isinstance(statement["Action"], list)
                else [statement["Action"]]
            )
        }
        self.assertNotIn("iam:*", actions)
        self.assertNotIn("s3:*", actions)
        self.assertNotIn("sqs:*", actions)
        self.assertIn("s3:GetObject", actions)
        self.assertIn("sqs:ReceiveMessage", actions)
        self.assertIn("cognito-idp:AdminCreateUser", actions)

    def test_inline_role_policy_stays_within_iam_size_limit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            documents = self._render(Path(temporary_directory))

        policy = documents["terraform-deploy-policy.json"]
        compact_policy = json.dumps(policy, separators=(",", ":"))
        self.assertLessEqual(len(compact_policy), 10_240)

    def test_rendered_policy_files_are_owner_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory)
            POLICY_RENDERER.render_policies(
                template_dir=REPOSITORY_ROOT / "infra" / "terraform" / "access",
                output_dir=output_dir,
                replacements=POLICY_RENDERER.build_replacements(self.arguments),
            )
            modes = sorted(path.stat().st_mode & 0o777 for path in output_dir.iterdir())

        self.assertEqual(modes, [0o600, 0o600, 0o600, 0o600])

    def test_invalid_account_id_is_rejected(self) -> None:
        self.arguments.account_id = "not-an-account"
        with self.assertRaisesRegex(ValueError, "12 digits"):
            POLICY_RENDERER.build_replacements(self.arguments)


if __name__ == "__main__":
    unittest.main()
