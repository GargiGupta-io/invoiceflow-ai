# InvoiceFlow AWS Infrastructure

This directory defines the production-shaped Version 2 AWS foundation. It is
validated infrastructure code, not proof that the resources are currently
provisioned.

## What It Creates

- A two-availability-zone VPC
- Public subnets for an Application Load Balancer
- An AWS-provided CloudFront HTTPS endpoint for the domain-free showcase
- Private application subnets for production API, worker, and migration tasks
- Isolated database subnets for RDS PostgreSQL
- Zero, one, or two NAT gateways, depending on the deployment profile
- A private encrypted and versioned S3 document bucket
- An encrypted SQS processing queue and dead-letter queue
- A private encrypted RDS PostgreSQL instance
- An RDS-managed database password in Secrets Manager
- A Cognito user pool, scoped resource server, and browser client
- A Cognito pre-token hook that adds the immutable tenant ID to access tokens
- Separate least-privilege API, worker, and execution IAM roles
- An ECR repository with image scanning and immutable tags
- ECS/Fargate API and worker services
- A one-off Alembic migration task definition
- CloudWatch log groups, profile-aware Container Insights, metrics, and alarms
- An SNS alarm topic with an optional email subscription
- An optional account-wide monthly usage budget measured before credits

## Trust Boundary

```text
Internet
   -> HTTPS CloudFront endpoint (domain-free showcase)
      -> restricted HTTP Application Load Balancer origin (public subnets)
      -> FastAPI tasks (private in production; public egress in showcase)
         -> RDS PostgreSQL (isolated database subnets)
         -> private S3 bucket
         -> SQS processing queue

SQS
   -> worker tasks (private in production; public egress in showcase)
      -> private S3 bucket
      -> RDS PostgreSQL
```

In the `production` profile, RDS and Fargate tasks receive no public IP
addresses. In the lower-cost `showcase` profile, Fargate receives public egress
in the public subnets so no NAT gateway is required, but inbound application
traffic is still accepted only from the load balancer security group. RDS is
isolated and private in both profiles. PostgreSQL accepts port 5432 only from
the Fargate task security group.

The domain-free showcase gives users HTTPS through the AWS-managed
`*.cloudfront.net` certificate. CloudFront reaches the load balancer over HTTP,
so this mode is limited to synthetic portfolio data. Direct origin requests
are restricted to the CloudFront origin-facing managed prefix list and receive
`403` unless they also contain a generated secret header. The secret is stored
only in sensitive Terraform state and the CloudFront origin configuration.

The `production` profile uses `custom_domain` mode instead: HTTP redirects to
an HTTPS load-balancer listener backed by the supplied ACM certificate. Use
that mode for end-to-end TLS and any non-synthetic environment.

## Prerequisites

1. An AWS account and the dedicated deployment role described in
   [`access/README.md`](access/README.md).
2. The administrator-owned `InvoiceFlowTaskBoundary` managed policy described
   in that access guide. Terraform refuses to create runtime roles without it.
3. Terraform 1.7 or newer.
4. A separately bootstrapped S3 state bucket and DynamoDB lock table.
5. Docker and the AWS CLI for building and pushing the application image.

The showcase does not require a purchased domain or ACM certificate. The
production profile additionally requires an ACM certificate in the selected
region and a matching DNS name.

Do not use a personal long-lived AWS access key in CI. Use GitHub Actions OIDC
to assume a narrowly scoped deployment role when deployment automation is
added.

## Remote State Bootstrap

Terraform cannot create the bucket that holds its own state in the same state
file. Review the separate [`bootstrap/`](bootstrap/) stack first. Step 20C may
plan that stack, but it must not apply it. The approved Step 20D rollout creates
the backend before the main stack is reinitialized against remote state.

Then initialize this stack:

```bash
cd infra/terraform
terraform init \
  -backend-config="bucket=REPLACE_STATE_BUCKET" \
  -backend-config="key=invoiceflow/production.tfstate" \
  -backend-config="region=ap-south-1" \
  -backend-config="dynamodb_table=REPLACE_LOCK_TABLE" \
  -backend-config="encrypt=true"
```

Remote state contains infrastructure identifiers and must be access-controlled,
encrypted, versioned, and excluded from public access.

## Plan Safely

Confirm Terraform is using the assumed deployment role, never the root account
or the direct developer identity:

```bash
aws sts get-caller-identity --profile invoiceflow-deploy
```

For the Free Plan showcase, start from the dedicated profile:

```bash
cp showcase.tfvars.example terraform.tfvars
```

For a production-shaped plan with private Fargate networking and stronger
deletion protection, start from `terraform.tfvars.example` instead.

```bash
# Replace the image tag, email, and account-specific values. For production,
# also replace the certificate, application domain, and OAuth URLs. Keep
# task_permissions_boundary_name set to the administrator-created
# InvoiceFlowTaskBoundary policy.

terraform fmt -check -recursive
terraform validate
AWS_PROFILE=invoiceflow-deploy terraform plan -out=invoiceflow.tfplan
```

Review the plan before applying it. Terraform variable files and plan files may
contain environment details and are ignored by Git.

`terraform init -backend=false` supports validation but does not support a
normal plan while this root declares an S3 backend. Before the backend exists,
use a disposable copy of this directory with the backend declaration omitted
to inspect a real-provider plan. Do not commit that copy or alter the tracked
backend configuration. The resulting plan is for permission, dependency, and
cost-surface review only.

The sanitized Step 20C findings are recorded in
[`../../docs/aws-showcase-plan-review.md`](../../docs/aws-showcase-plan-review.md).
A deployable plan must be regenerated after the approved backend bootstrap and
remote initialization.

`public_endpoint_mode = "cloudfront"` derives Cognito callback and logout URLs
from the generated distribution domain, so the showcase needs no placeholder
certificate or DNS name. CloudFront's default certificate covers that generated
hostname. `custom_domain` mode still requires a real ACM certificate, matching
domain, and explicit HTTPS callback/logout URLs.

The CloudFront adaptation does not approve an apply. Regenerate and inspect a
real plan after the deployment role policy is updated and the remote backend is
bootstrapped. Confirm that the showcase contains one CloudFront distribution,
no HTTPS load-balancer listener, no public CIDR ingress to the load balancer,
and zero-count ECS services on the first apply.

For the first release, keep `services_enabled = false`. The first apply creates
the ECR repository, database, queues, identity resources, load balancer, task
definitions, and zero-count ECS services. It must not try to start a container
before the immutable image exists or before the database migration succeeds.

```bash
terraform apply invoiceflow.tfplan
```

## Build And Push The Image

Use an immutable Git commit SHA as the image tag:

```bash
AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
AWS_REGION="ap-south-1"
IMAGE_TAG="$(git rev-parse --short=12 HEAD)"
REPOSITORY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/invoiceflow-production"

aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin \
    "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

docker build --platform linux/amd64 -t "${REPOSITORY}:${IMAGE_TAG}" .
docker push "${REPOSITORY}:${IMAGE_TAG}"
```

Set `container_image_tag` to the same immutable tag before the first apply. The
first apply creates ECR while services remain stopped; then push that exact tag.
The repository rejects overwriting an existing tag.

## Database Migration Order

Do not start a new API or worker revision before its migration succeeds.

1. Plan and apply with `services_enabled = false`.
2. Push the immutable image into the newly created ECR repository.
3. Run the one-off migration task using `runtime_subnet_ids`,
   `task_security_group_id`, and `runtime_assign_public_ip` outputs.
4. Wait for the task to stop and verify container exit code zero.
5. Run the one-off reviewer provisioner for each approved sample reviewer.
6. Set `services_enabled = true`, review a second plan, and apply it.
7. Wait for the API and worker services to stabilize.
8. In `custom_domain` mode, create the application DNS record for the load
   balancer. The domain-free showcase skips this action.
9. Verify `/health/live`, `/health/ready`, `/reviewer`, and Cognito login at the
   `public_base_url` output.

The required cluster, task definition, subnets, and security-group identifiers
are Terraform outputs. The migration task runs `alembic upgrade head` using the
same RDS-managed password injection as the services.

The production image also builds and serves the React reviewer shell at
`/reviewer`. Cognito browser settings are injected into the API task at runtime
and returned through the non-secret `/v2/auth/config` endpoint. Access and ID
tokens are not compiled into the image.

## First Reviewer Provisioning

The provisioner task creates one Cognito user and the matching PostgreSQL
organization/user rows as one idempotent operator workflow. Cognito sends the
temporary-password invitation email; the command does not accept or print a
password.

Choose one organization UUID and keep it stable for every reviewer in that
tenant:

```bash
ORGANIZATION_ID="$(python -c 'import uuid; print(uuid.uuid4())')"
```

Run the Terraform output `provisioner_task_definition_arn` using
`runtime_subnet_ids`, `task_security_group_id`, and
`runtime_assign_public_ip`. Override its command as follows:

```text
python -m app.admin.provision_reviewer
  --organization-id <stable-organization-uuid>
  --organization-name "InvoiceFlow Demo Finance"
  --email <approved-sample-reviewer-email>
  --display-name "Demo Reviewer"
```

The task role can call only `cognito-idp:AdminCreateUser` and
`cognito-idp:AdminGetUser` for this stack's user pool. It has no document,
queue, or general Cognito administration permissions. Re-running the command
with the same tenant and email reuses both identities. Conflicting tenant,
subject, name, or email mappings fail instead of silently changing ownership.

Do not use real customer identities or documents in the portfolio deployment.

## Database Credentials

RDS generates and rotates the master password through Secrets Manager.
Terraform does not generate a plaintext password or construct a secret-bearing
database URL. ECS injects only `DATABASE_PASSWORD`; host, port, database, and
username are ordinary task environment values.

The application assembles the SQLAlchemy URL inside the process. Never print
the resulting URL or include it in health responses.

## Cognito Organization Claim

The custom `organization_id` attribute is immutable and admin-managed. Create
the matching organization and user rows in PostgreSQL before enabling an
employee. Cognito does not copy custom attributes into access tokens by default,
so the pre-token Lambda copies this one attribute into the signed access token.
The authenticated claim identifies a tenant, while repository queries still
enforce that tenant on every database operation. A user without the attribute
receives a token that the API rejects.

## S3 Retention

- Quarantine objects expire after two days as an orphan-cleanup safety net.
- The application performs business-aware deletion at the configured retention
  date and writes a safe audit event.
- Validated objects expire seven days after the application retention period as
  a final storage backstop.
- Incomplete multipart uploads expire after one day.

The lifecycle rule is not a substitute for the application deletion worker
because S3 cannot remove PostgreSQL extraction, review, or evidence records.

## Cost And Availability

`deployment_profile = "showcase"` is the Free Plan portfolio configuration. It:

- provisions no NAT gateway;
- runs one API task and one worker when services are enabled;
- caps API autoscaling at the configured desired count;
- uses single-AZ private RDS with one day of backups and no Performance Insights;
- disables Container Insights;
- uses seven-day document and log retention in the example file; and
- disables deletion protection for resources that otherwise block teardown.

The showcase tasks use public IP addresses only for outbound internet/AWS API
access. Their security group still accepts API traffic only from the load
balancer, and the database and document bucket remain private.

`deployment_profile = "production"` keeps Fargate in private application
subnets. The default uses two API tasks and Multi-AZ RDS, but only one NAT
gateway. One NAT gateway is a network availability compromise. Set
`single_nat_gateway = false` for one gateway per availability zone.

The main recurring credit consumers are Fargate tasks, the load balancer, RDS,
CloudFront traffic and requests, the Cognito Plus tier used for access-token
customization and advanced security, CloudWatch, public IPv4 addresses, and
data transfer. Production also adds NAT gateway hourly and data-processing
usage. Run `terraform plan` and use the AWS Pricing Calculator before applying.

When `alarm_email` is set, Terraform creates one free monitoring-only AWS
Budget. It measures account-wide usage before credits and sends actual-usage
alerts at 50%, 80%, and 100% of `monthly_cost_budget_usd`. Budget data can lag
and an alert is not a hard spending cap. The AWS Free Plan itself prevents
charges unless the account is deliberately upgraded, and it ends after six
months or when its credits are depleted, whichever happens first.

Keep `services_enabled = false` whenever the live reviewer is not being shown.
This stops Fargate compute but does not stop the load balancer or RDS. For a
long pause, take a final sanitized backup if needed and run a reviewed
`terraform destroy` with the showcase profile. Never leave a demonstration
stack running merely because credits remain.

Production keeps load-balancer, Cognito, and RDS deletion protection and a final
RDS snapshot. Showcase disables those controls and allows Terraform to empty
the synthetic-data S3 bucket so a deliberate reviewed teardown can complete.
Do not use the showcase teardown policy for customer data.

## What Is Not Automated Yet

- Production DNS record creation
- Production ACM certificate issuance
- GitHub OIDC deployment
- Terraform apply in CI
- Scheduled retention Fargate task
- Textract integration
- Production load test execution

These omissions are explicit so validation of this directory is not mistaken
for a live enterprise deployment.
