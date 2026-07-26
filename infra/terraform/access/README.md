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

The renderer creates six documents:

- `task-permissions-boundary-policy.json`: administrator-owned maximum
  permissions for every InvoiceFlow runtime role.
- `deployer-trust-policy.json`: allows only the named developer user to assume
  the deployment role.
- `terraform-deploy-policy.json`: lets the assumed deployment role manage the
  resources declared by this stack.
- `terraform-deploy-support-policy.json`: grants read-only discovery plus the
  narrowly scoped KMS and Secrets Manager calls RDS needs when creating its
  managed master-password secret.
- `terraform-elb-lifecycle-policy.json`: allows Terraform to replace only
  InvoiceFlow-prefixed Application Load Balancers, listeners, and listener
  rules without granting broader stack-deletion permissions.
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
4. On that role, create a second inline permissions policy named
   `InvoiceFlowTerraformDeploySupport` from
   `.aws-local/terraform-deploy-support-policy.json`.
5. Create a customer-managed policy named
   `InvoiceFlowTerraformElbLifecycle` from
   `.aws-local/terraform-elb-lifecycle-policy.json`, then attach it to
   `InvoiceFlowTerraformDeployRole`.
6. On the `invoiceflow-developer` user, create an inline policy named
   `InvoiceFlowAssumeTerraformRole` from
   `.aws-local/developer-assume-role-policy.json`.
7. Sign out of the administrator session when those changes are saved.

The role can manage only the AWS service families used by this Terraform stack.
IAM writes are restricted to task roles beginning with
`invoiceflow-showcase-`, and role creation succeeds only when the exact
`InvoiceFlowTaskBoundary` policy is attached. The deployment role cannot create
users, access keys, or additional managed policies. The developer user receives
only permission to assume this one deployment role.

The two inline deployment policies intentionally exclude stack-destruction
actions. The attached lifecycle policy grants only the three ELB delete actions
Terraform needs when replacing the InvoiceFlow-prefixed load-balancer path. It
does not permit teardown of RDS, S3, SQS, Cognito, ECS, IAM, VPC, or the rest of
the stack. A future full teardown still requires a separately reviewed,
temporary administrator elevation that is removed immediately afterward.

The boundary caps the resulting API, worker, execution, provisioner, and
Cognito hook roles to the runtime services InvoiceFlow needs. Updating an
inline role policy cannot grant permissions beyond that boundary.

## Updating The Deployment Role

Re-render and replace the deployment-role policies whenever the tracked
Terraform stack adds an AWS resource type. Keep normal write operations in the
core policy, discovery or service-integration permissions in the support
policy, and the narrowly scoped ELB replacement actions in the lifecycle
managed policy.

1. Render `.aws-local/terraform-deploy-policy.json` and
   `.aws-local/terraform-deploy-support-policy.json` with the current account
   and environment values.
2. Open IAM -> Roles -> `InvoiceFlowTerraformDeployRole` -> Permissions.
3. Expand `InvoiceFlowTerraformDeploy`, choose **Edit**, and open the JSON tab.
4. Replace the existing document with the newly rendered file, review the
   summary, and save.
5. Repeat for `InvoiceFlowTerraformDeploySupport` using the support policy.
6. If the ELB lifecycle document changed, create a new version of
   `InvoiceFlowTerraformElbLifecycle`, set it as default, and delete obsolete
   non-default versions after review.
7. Confirm the role has the two inline project policies and the one
   `InvoiceFlowTerraformElbLifecycle` attachment, then run a plan without
   applying it.

The applied domain-free showcase uses API Gateway, a VPC link, and an internal
Application Load Balancer. Load-balancer resources remain scoped to the
`invoiceflow-showcase-*` prefix. The generic listener type segment lets the
same AWS action cover AWS's documented listener ARN shapes, while load-balancer
deletion remains restricted to `loadbalancer/app`. Optional CloudFront actions
in the core policy remain tag-restricted for the alternative synthetic
endpoint mode.

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
- Never add deletion actions to the normal inline deployment policies as a
  shortcut; keep the reviewed ELB replacement exception isolated in
  `InvoiceFlowTerraformElbLifecycle`, and authorize full teardown separately
  and temporarily.
- Never apply a Terraform plan before reviewing its exact additions, changes,
  replacements, and deletions.
- When CloudFront mode is selected, never use the generated origin-header value
  in logs, screenshots, or support messages. It is a bearer secret stored in
  Terraform state.
- Treat an `AccessDenied` as a request to review one missing action, not as a
  reason to broaden a statement to `Action: "*"`.
- Remove the deployment role after the showcase is torn down if it is no longer
  needed.

The policy is source-derived for the resources currently declared in
`infra/terraform/`. Any future AWS resource must update the policy and its tests
before it can be deployed.
