# InvoiceFlow AWS Infrastructure

This directory defines the production-shaped Version 2 AWS foundation. It is
validated infrastructure code, not proof that the resources are currently
provisioned.

## What It Creates

- A two-availability-zone VPC
- Public subnets for an HTTPS Application Load Balancer
- Private application subnets for API, worker, and migration Fargate tasks
- Isolated database subnets for RDS PostgreSQL
- One or two NAT gateways, depending on the cost/availability setting
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
- CloudWatch log groups, Container Insights, metrics, and alarms
- An SNS alarm topic with an optional email subscription

## Trust Boundary

```text
Internet
   -> HTTPS Application Load Balancer (public subnets)
      -> FastAPI tasks (private application subnets)
         -> RDS PostgreSQL (isolated database subnets)
         -> private S3 bucket
         -> SQS processing queue

SQS
   -> worker tasks (private application subnets)
      -> private S3 bucket
      -> RDS PostgreSQL
```

RDS and Fargate tasks receive no public IP addresses. PostgreSQL accepts port
5432 only from the Fargate task security group. HTTP is redirected to HTTPS.

## Prerequisites

1. An AWS account and an IAM deployment role with permission to create the
   resources in this directory.
2. Terraform 1.7 or newer.
3. An ACM certificate in the selected AWS region.
4. A DNS name that can point to the load balancer after creation.
5. A separately bootstrapped S3 state bucket and DynamoDB lock table.
6. Docker and the AWS CLI for building and pushing the application image.

Do not use a personal long-lived AWS access key in CI. Use GitHub Actions OIDC
to assume a narrowly scoped deployment role when deployment automation is
added.

## Remote State Bootstrap

Terraform cannot create the bucket that holds its own state in the same state
file. Create the encrypted versioned state bucket and lock table once in a
small bootstrap stack or through an approved platform account process.

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

```bash
cp terraform.tfvars.example terraform.tfvars
# Replace the certificate, application domain, URLs, image tag, email, and
# account-specific values.

terraform fmt -check
terraform validate
terraform plan -out=invoiceflow.tfplan
```

Review the plan before applying it. Terraform variable files and plan files may
contain environment details and are ignored by Git.

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
3. Run the one-off migration task in the private application subnets.
4. Wait for the task to stop and verify container exit code zero.
5. Run the one-off reviewer provisioner for each approved sample reviewer.
6. Set `services_enabled = true`, review a second plan, and apply it.
7. Wait for the API and worker services to stabilize.
8. Create the application DNS record for the load balancer.
9. Verify `/health/live`, `/health/ready`, `/reviewer`, and Cognito login.

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

Run the Terraform output `provisioner_task_definition_arn` in the private app
subnets with the `task_security_group_id`. Override its command as follows:

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

The default uses two API tasks and Multi-AZ RDS, but only one NAT gateway to
limit portfolio cost. One NAT gateway is a network availability compromise.
Set `single_nat_gateway = false` for one gateway per availability zone.

The main recurring costs are NAT gateways, Fargate tasks, the load balancer,
RDS, the Cognito Plus tier used for access-token customization and advanced
security, CloudWatch logs, and data transfer. Run `terraform plan` and use the
AWS Pricing Calculator before applying.

S3 and the load balancer have deletion protection in this configuration.
RDS deletion protection and final snapshots are enabled by default. Deliberate
teardown therefore requires explicit configuration changes and a reviewed plan.

## What Is Not Automated Yet

- DNS record creation
- ACM certificate issuance
- GitHub OIDC deployment
- Terraform apply in CI
- Scheduled retention Fargate task
- Textract integration
- Production load test execution

These omissions are explicit so validation of this directory is not mistaken
for a live enterprise deployment.
