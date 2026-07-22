"""Render account-specific AWS access policies without committing account data."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path


TEMPLATE_NAMES = (
    "developer-assume-role-policy.json.tpl",
    "deployer-trust-policy.json.tpl",
    "task-permissions-boundary-policy.json.tpl",
    "terraform-deploy-policy.json.tpl",
    "terraform-deploy-support-policy.json.tpl",
)


def _valid_name(value: str, field: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9+=,.@_-]{1,64}", value):
        raise ValueError(f"{field} contains unsupported IAM name characters")
    return value


def build_replacements(args: argparse.Namespace) -> dict[str, str]:
    if not re.fullmatch(r"\d{12}", args.account_id):
        raise ValueError("account_id must contain exactly 12 digits")
    if not re.fullmatch(r"[a-z]{2}-[a-z]+-\d", args.aws_region):
        raise ValueError("aws_region is not a valid commercial AWS region name")
    if not re.fullmatch(r"[a-z][a-z0-9-]{2,20}", args.project_name):
        raise ValueError("project_name must match the Terraform project name format")
    if args.environment not in {"showcase", "production"}:
        raise ValueError("environment must be showcase or production")

    developer_user = _valid_name(args.developer_user, "developer_user")
    deploy_role = _valid_name(args.deploy_role, "deploy_role")
    if not re.fullmatch(r"[A-Za-z0-9+=,.@_-]{1,128}", args.task_boundary_policy_name):
        raise ValueError("task_boundary_policy_name contains unsupported characters")
    resource_prefix = f"{args.project_name}-{args.environment}"
    state_bucket = args.state_bucket or (
        f"{args.project_name}-terraform-state-{args.account_id}-{args.aws_region}"
    )
    if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", state_bucket):
        raise ValueError("state_bucket is not a valid lowercase S3 bucket name")
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,255}", args.lock_table):
        raise ValueError("lock_table is not a valid DynamoDB table name")

    return {
        "__ACCOUNT_ID__": args.account_id,
        "__AWS_REGION__": args.aws_region,
        "__DEVELOPER_USER_NAME__": developer_user,
        "__DEPLOY_ROLE_NAME__": deploy_role,
        "__PROJECT_NAME__": args.project_name,
        "__ENVIRONMENT__": args.environment,
        "__RESOURCE_PREFIX__": resource_prefix,
        "__STATE_BUCKET_NAME__": state_bucket,
        "__STATE_LOCK_TABLE_NAME__": args.lock_table,
        "__TASK_BOUNDARY_POLICY_NAME__": args.task_boundary_policy_name,
    }


def render_policies(
    template_dir: Path,
    output_dir: Path,
    replacements: dict[str, str],
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_paths: list[Path] = []
    for template_name in TEMPLATE_NAMES:
        rendered = (template_dir / template_name).read_text(encoding="utf-8")
        for placeholder, value in replacements.items():
            rendered = rendered.replace(placeholder, value)
        unresolved = sorted(set(re.findall(r"__[A-Z0-9_]+__", rendered)))
        if unresolved:
            raise ValueError(
                f"{template_name} contains unresolved placeholders: {unresolved}"
            )
        json.loads(rendered)
        output_path = output_dir / template_name.removesuffix(".tpl")
        output_path.write_text(rendered, encoding="utf-8")
        os.chmod(output_path, 0o600)
        output_paths.append(output_path)
    return output_paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render least-privilege InvoiceFlow AWS policy documents."
    )
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--aws-region", default="ap-south-1")
    parser.add_argument("--developer-user", default="invoiceflow-developer")
    parser.add_argument("--deploy-role", default="InvoiceFlowTerraformDeployRole")
    parser.add_argument("--project-name", default="invoiceflow")
    parser.add_argument("--environment", default="showcase")
    parser.add_argument("--state-bucket")
    parser.add_argument("--lock-table", default="invoiceflow-terraform-locks")
    parser.add_argument(
        "--task-boundary-policy-name", default="InvoiceFlowTaskBoundary"
    )
    parser.add_argument("--output-dir", type=Path, default=Path(".aws-local"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repository_root = Path(__file__).resolve().parents[1]
    template_dir = repository_root / "infra" / "terraform" / "access"
    output_paths = render_policies(
        template_dir=template_dir,
        output_dir=args.output_dir,
        replacements=build_replacements(args),
    )
    for output_path in output_paths:
        print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
