# AWS Showcase Plan Review

Reviewed on July 20, 2026 from `feature/version-2-pipeline` with Terraform
1.9.8. Both plans used the dedicated `InvoiceFlowTerraformDeployRole` and
short-lived browser-login credentials. No `terraform apply` command was run.

## State Bootstrap

The state bootstrap plan contains 8 additions, 0 changes, and 0 deletions:

- one private S3 state bucket;
- complete S3 public-access blocking;
- bucket-owner-enforced object ownership;
- AES-256 server-side encryption;
- versioning and 90-day expiry for noncurrent versions;
- a TLS-only bucket policy; and
- one encrypted, on-demand DynamoDB lock table.

The saved bootstrap plan and account-specific variable file are local ignored
artifacts. The state bucket and lock table do not exist until Step 20D receives
explicit apply approval.

## Application Stack

The showcase application plan contains 91 additions, 0 changes, 0 deletions,
and 5 data reads. Important planned controls are:

- no NAT gateway and no elastic IP;
- API and worker ECS services created with desired count zero;
- a private, encrypted, single-AZ `db.t4g.micro` PostgreSQL instance;
- a private, encrypted, versioned document bucket with all public access
  blocked;
- one processing queue and one dead-letter queue;
- five runtime IAM roles using `InvoiceFlowTaskBoundary`;
- one internet-facing Application Load Balancer for eventual HTTPS access; and
- a USD 5 monthly usage budget measured before Free Plan credits.

The plan uses the lower-cost showcase profile. It intentionally trades away
Multi-AZ database availability, deletion protection, and private Fargate
egress. These are restored by the production profile.

## Main Cost Drivers

The resources most likely to consume Free Plan credits are RDS PostgreSQL, the
Application Load Balancer, Fargate tasks after services are enabled, CloudWatch
logs and alarms, and stored S3 data. S3 requests, SQS requests, ECR storage, and
DynamoDB on-demand state locking should remain small for a controlled demo but
are still metered.

The budget is an alert, not a hard spending cap. The deployment must still be
torn down after the planned demo window.

## Apply Blockers

Step 20D must not begin until all of the following are true:

1. A real DNS name is available.
2. A matching ACM certificate exists in `ap-south-1`.
3. The bootstrap plan is reviewed again and explicitly approved for apply.
4. The main plan is regenerated against the new remote backend.
5. Current AWS pricing and remaining Free Plan credits are checked.
6. The immutable container image, database migration, reviewer provisioning,
   service enablement, and teardown order are ready.

The Step 20C application plan used syntactically valid placeholder certificate
and DNS values. It proves provider access, resource dependencies, security
settings, and cost shape; it is not deployable and must never be applied.
