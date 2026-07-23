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
        support_policy = documents["terraform-deploy-support-policy.json"]
        actions = {
            action
            for document in (policy, support_policy)
            for statement in document["Statement"]
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
        self.assertFalse(any(action.startswith("cloudfront:") for action in actions))
        self.assertIn("apigateway:GET", actions)
        self.assertIn("apigateway:PATCH", actions)
        self.assertIn("apigateway:POST", actions)
        self.assertIn("apigateway:TagResource", actions)
        self.assertIn("elasticloadbalancing:Create*", actions)
        self.assertNotIn("elasticloadbalancing:*", actions)
        self.assertIn("iam:PassRole", actions)
        self.assertIn("ec2:Describe*", actions)
        self.assertIn("ec2:GetManagedPrefixListEntries", actions)
        self.assertIn("ec2:GetSecurityGroupsForVpc", actions)
        self.assertIn("ec2:CreateTags", actions)
        self.assertIn("ecr:BatchCheckLayerAvailability", actions)
        self.assertIn("ecr:CompleteLayerUpload", actions)
        self.assertIn("ecr:InitiateLayerUpload", actions)
        self.assertIn("ecr:PutImage", actions)
        self.assertIn("ecr:UploadLayerPart", actions)
        self.assertIn("ecs:RunTask", actions)
        self.assertIn("logs:DescribeLogStreams", actions)
        self.assertIn("logs:FilterLogEvents", actions)
        self.assertIn("logs:GetLogEvents", actions)
        self.assertIn("logs:ListTagsForResource", actions)
        self.assertIn("cloudwatch:ListTagsForResource", actions)
        self.assertIn("cloudwatch:TagResource", actions)
        self.assertIn("rds:ListTagsForResource", actions)
        self.assertIn("sns:SetTopicAttributes", actions)
        self.assertIn("lambda:ListVersionsByFunction", actions)
        self.assertIn("cognito-idp:GetUserPoolMfaConfig", actions)
        self.assertIn("budgets:ListTagsForResource", actions)
        self.assertIn("budgets:TagResource", actions)
        self.assertIn("s3:Get*Configuration", actions)
        self.assertIn("s3:PutEncryptionConfiguration", actions)
        self.assertIn("s3:PutLifecycleConfiguration", actions)
        self.assertIn("dynamodb:DescribeTimeToLive", actions)
        self.assertNotIn("ec2:AllocateAddress", actions)
        self.assertNotIn("ec2:CreateNatGateway", actions)
        self.assertNotIn("ec2:DeleteNatGateway", actions)
        self.assertNotIn("ec2:DisassociateAddress", actions)
        self.assertNotIn("ec2:ReleaseAddress", actions)
        self.assertNotIn("ec2:DeleteVpc", actions)
        self.assertNotIn("s3:DeleteBucket", actions)
        self.assertNotIn("rds:DeleteDBInstance", actions)
        self.assertNotIn("ecs:DeleteService", actions)
        self.assertNotIn("iam:DeleteRole", actions)
        self.assertNotIn("lambda:DeleteFunction", actions)
        self.assertNotIn("cognito-idp:DeleteUserPool", actions)

        security_group_rule_statement = next(
            statement
            for statement in policy["Statement"]
            if isinstance(statement["Resource"], str)
            and statement["Resource"].endswith("security-group-rule/*")
        )
        self.assertEqual(
            set(security_group_rule_statement["Action"]),
            {
                "ec2:AuthorizeSecurityGroupEgress",
                "ec2:AuthorizeSecurityGroupIngress",
                "ec2:CreateTags",
            },
        )
        self.assertEqual(
            security_group_rule_statement["Condition"]["StringEquals"],
            {
                "aws:RequestTag/Application": "invoiceflow",
                "aws:RequestTag/Environment": "showcase",
                "aws:RequestTag/ManagedBy": "Terraform",
            },
        )

        kms_statement = next(
            statement
            for statement in support_policy["Statement"]
            if statement["Action"] == "kms:DescribeKey"
        )
        self.assertEqual(
            kms_statement["Condition"]["ForAnyValue:StringEquals"][
                "kms:ResourceAliases"
            ],
            ["alias/aws/rds", "alias/aws/secretsmanager"],
        )

        secret_statement = next(
            statement
            for statement in support_policy["Statement"]
            if "secretsmanager:CreateSecret" in statement["Action"]
        )
        self.assertEqual(
            secret_statement["Resource"],
            "arn:aws:secretsmanager:ap-south-1:123456789012:secret:rds!*",
        )

        object_statement = next(
            statement
            for statement in policy["Statement"]
            if statement["Action"] == "s3:GetObject"
        )
        self.assertNotIn("*", object_statement["Resource"])

        configuration_statement = next(
            statement
            for statement in policy["Statement"]
            if "s3:Get*Configuration" in statement["Action"]
        )
        self.assertEqual(
            configuration_statement["Resource"],
            [
                "arn:aws:s3:::invoiceflow-showcase-*",
                "arn:aws:s3:::invoiceflow-terraform-state-123456789012-ap-south-1",
            ],
        )

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

        create_api_gateway_statement = next(
            statement
            for statement in policy["Statement"]
            if statement["Action"] == "apigateway:POST"
            and "arn:aws:apigateway:ap-south-1::/apis"
            in statement["Resource"]
        )
        self.assertEqual(
            create_api_gateway_statement["Resource"],
            [
                "arn:aws:apigateway:ap-south-1::/apis",
                "arn:aws:apigateway:ap-south-1::/vpclinks",
            ],
        )
        self.assertEqual(
            create_api_gateway_statement["Condition"]["StringEquals"][
                "aws:RequestTag/Application"
            ],
            "invoiceflow",
        )

        manage_api_gateway_statement = next(
            statement
            for statement in policy["Statement"]
            if isinstance(statement["Action"], list)
            and "apigateway:PATCH" in statement["Action"]
        )
        self.assertEqual(
            manage_api_gateway_statement["Resource"],
            [
                "arn:aws:apigateway:ap-south-1::/apis",
                "arn:aws:apigateway:ap-south-1::/apis/*",
                "arn:aws:apigateway:ap-south-1::/tags/*",
                "arn:aws:apigateway:ap-south-1::/vpclinks",
                "arn:aws:apigateway:ap-south-1::/vpclinks/*",
            ],
        )

        run_task_statement = next(
            statement
            for statement in policy["Statement"]
            if isinstance(statement["Action"], list)
            and "ecs:RunTask" in statement["Action"]
        )
        self.assertIn(
            "arn:aws:ecs:ap-south-1:123456789012:task-definition/invoiceflow-showcase-*:*",
            run_task_statement["Resource"],
        )

        service_linked_role_statement = next(
            statement
            for statement in policy["Statement"]
            if statement["Action"] == "iam:CreateServiceLinkedRole"
        )
        self.assertIn(
            "ops.apigateway.amazonaws.com",
            service_linked_role_statement["Condition"]["StringEquals"][
                "iam:AWSServiceName"
            ],
        )

        load_balancer_statement = next(
            statement
            for statement in policy["Statement"]
            if "elasticloadbalancing:Create*" in statement["Action"]
        )
        self.assertTrue(
            all(
                "invoiceflow-showcase-" in resource
                for resource in load_balancer_statement["Resource"]
            )
        )

        create_tags_statement = next(
            statement
            for statement in policy["Statement"]
            if statement["Action"] == "ec2:CreateTags"
        )
        create_tag_conditions = create_tags_statement["Condition"]["StringEquals"]
        self.assertEqual(
            create_tag_conditions["aws:RequestTag/Application"], "invoiceflow"
        )
        self.assertEqual(
            create_tag_conditions["aws:RequestTag/Environment"], "showcase"
        )
        self.assertEqual(
            create_tag_conditions["aws:RequestTag/ManagedBy"], "Terraform"
        )
        self.assertEqual(
            create_tag_conditions["ec2:CreateAction"],
            [
                "CreateInternetGateway",
                "CreateRouteTable",
                "CreateSecurityGroup",
                "CreateSubnet",
                "CreateVpc",
                "CreateVpcEndpoint",
            ],
        )

        parent_vpc_create_statement = next(
            statement
            for statement in policy["Statement"]
            if {
                "ec2:CreateRouteTable",
                "ec2:CreateSecurityGroup",
                "ec2:CreateSubnet",
                "ec2:CreateVpcEndpoint",
            }.issubset(set(statement["Action"]))
            and "ec2:ResourceTag/Application"
            in statement.get("Condition", {}).get("StringEquals", {})
        )
        self.assertEqual(parent_vpc_create_statement["Resource"], "*")
        self.assertEqual(
            parent_vpc_create_statement["Condition"]["StringEquals"],
            {
                "ec2:ResourceTag/Application": "invoiceflow",
                "ec2:ResourceTag/Environment": "showcase",
                "ec2:ResourceTag/ManagedBy": "Terraform",
            },
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

        deployment_policies = [
            documents["terraform-deploy-policy.json"],
            documents["terraform-deploy-support-policy.json"],
        ]
        aggregate_size = 0
        for policy in deployment_policies:
            compact_policy = json.dumps(policy, separators=(",", ":"))
            self.assertLessEqual(len(compact_policy), 10_240)
            aggregate_size += len(compact_policy)
        self.assertLessEqual(aggregate_size, 10_240)

    def test_rendered_policy_files_are_owner_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory)
            POLICY_RENDERER.render_policies(
                template_dir=REPOSITORY_ROOT / "infra" / "terraform" / "access",
                output_dir=output_dir,
                replacements=POLICY_RENDERER.build_replacements(self.arguments),
            )
            modes = sorted(path.stat().st_mode & 0o777 for path in output_dir.iterdir())

        self.assertEqual(modes, [0o600, 0o600, 0o600, 0o600, 0o600])

    def test_invalid_account_id_is_rejected(self) -> None:
        self.arguments.account_id = "not-an-account"
        with self.assertRaisesRegex(ValueError, "12 digits"):
            POLICY_RENDERER.build_replacements(self.arguments)


if __name__ == "__main__":
    unittest.main()
