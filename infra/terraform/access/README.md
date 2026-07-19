# AWS Deployment Access

InvoiceFlow uses a dedicated Terraform role instead of attaching infrastructure
write permissions directly to the everyday `invoiceflow-developer` user.

```text
aws login session
    -> invoiceflow-developer
       -> sts:AssumeRole only
          -> InvoiceFlowTerraformDeployRole
             -> InvoiceFlow resource and state permissions
```

The templates do not contain an AWS account number. Render local copies after
signing in:

```bash
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"

python3.11 scripts/render_aws_access_policies.py \
  --account-id "$ACCOUNT_ID" \
  --output-dir .aws-local
```

The generated `.aws-local/` directory is ignored by Git and each policy file is
written with owner-only permissions.

The renderer creates four documents:

- `task-permissions-boundary-policy.json`: administrator-owned maximum
  permissions for every InvoiceFlow runtime role.
- `deployer-trust-policy.json`: allows only the named developer user to assume
  the deployment role.
- `terraform-deploy-policy.json`: lets the assumed deployment role manage the
  resources declared by this stack.
- `developer-assume-role-policy.json`: gives the developer user permission to
  assume only the InvoiceFlow deployment role.

## One-Time Administrator Setup

Use an administrator browser session only for these setup actions. Do not make
the developer user an administrator and do not create an access key.

1. In IAM, create a customer-managed policy named `InvoiceFlowTaskBoundary`
   from `.aws-local/task-permissions-boundary-policy.json`. This policy is a
   permissions boundary, not a policy to attach directly to the developer.
2. In IAM, create the role `InvoiceFlowTerraformDeployRole` using
   `.aws-local/deployer-trust-policy.json` as its custom trust policy.
3. On that role, create an inline permissions policy named
   `InvoiceFlowTerraformDeploy` from
   `.aws-local/terraform-deploy-policy.json`.
4. On the `invoiceflow-developer` user, create an inline policy named
   `InvoiceFlowAssumeTerraformRole` from
   `.aws-local/developer-assume-role-policy.json`.
5. Sign out of the administrator session when those four changes are saved.

The role can manage only the AWS service families used by this Terraform stack.
IAM writes are restricted to task roles beginning with
`invoiceflow-showcase-`, and role creation succeeds only when the exact
`InvoiceFlowTaskBoundary` policy is attached. The deployment role cannot create
users, access keys, or additional managed policies. The developer user receives
only permission to assume this one deployment role.

The boundary caps the resulting API, worker, execution, provisioner, and
Cognito hook roles to the runtime services InvoiceFlow needs. Updating an
inline role policy cannot grant permissions beyond that boundary.

## Local Role Profile

Keep the browser-based AWS login as the source profile and add a role profile:

```bash
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"

aws configure set \
  role_arn "arn:aws:iam::${ACCOUNT_ID}:role/InvoiceFlowTerraformDeployRole" \
  --profile invoiceflow-deploy
aws configure set source_profile default --profile invoiceflow-deploy
aws configure set region ap-south-1 --profile invoiceflow-deploy

aws sts get-caller-identity --profile invoiceflow-deploy
```

The final command must return an assumed-role ARN containing
`InvoiceFlowTerraformDeployRole`. If it returns the IAM user ARN, stop before
running Terraform.

## Permission Review Rules

- Never attach `AdministratorAccess` or `PowerUserAccess` as a shortcut.
- Never attach `InvoiceFlowTaskBoundary` to the developer or deployment role;
  Terraform applies it only as a boundary on runtime roles.
- Never paste generated policy files into issues, logs, or screenshots.
- Never run Terraform as the root account.
- Never run `terraform apply` while reviewing Step 20C.
- Treat an `AccessDenied` as a request to review one missing action, not as a
  reason to broaden a statement to `Action: "*"`.
- Remove the deployment role after the showcase is torn down if it is no longer
  needed.

The policy is source-derived for the resources currently declared in
`infra/terraform/`. Any future AWS resource must update the policy and its tests
before it can be deployed.
