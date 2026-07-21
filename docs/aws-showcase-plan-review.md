# AWS Showcase Plan Review

Reviewed through July 21, 2026 from `feature/version-2-pipeline` with Terraform
1.9.8. The plans used the dedicated `InvoiceFlowTerraformDeployRole` and
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

## Prior Step 20C Application Stack

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

That 91-resource plan used placeholder custom-domain inputs and is now
superseded. It remains useful as historical evidence that the provider access,
dependency graph, and original cost surface were inspectable, but it must not
be applied.

## Step 20D.1 Domain-Free Endpoint Adaptation

The showcase now uses one CloudFront distribution and its AWS-provided
`*.cloudfront.net` certificate. No purchased domain or ACM certificate is
required. Cognito callback and logout URLs are derived from that generated
hostname.

The load balancer is an HTTP origin in this profile. Its security group accepts
port 80 only from the AWS-managed CloudFront origin-facing prefix list. Its
default listener response is `403`; only a request carrying the generated
CloudFront origin header is forwarded to the API target group. Cache behavior
is disabled and all request data except the viewer `Host` header is forwarded,
which preserves authenticated API and reviewer behavior.

This is a synthetic showcase compromise, not the production transport design.
The production profile continues to require a custom domain, an ACM
certificate, and end-to-end HTTPS at the Application Load Balancer.

Local Terraform validation and mocked profile tests pass for both endpoint
modes. The rendered deployment policy is 10,158 characters after JSON
compaction, below AWS's 10,240-character inline-role aggregate limit, and has
no medium-or-higher Parliament findings. Its local and installed policy hashes
match exactly.

The replacement real-provider plan succeeds with 93 additions, 0 changes, 0
deletions, and 5 data reads. Structured inspection of the saved plan confirms:

- exactly one CloudFront distribution using its default HTTPS certificate;
- viewer HTTP requests redirect to HTTPS;
- no custom domain, ACM certificate, custom HTTPS listener, or NAT gateway;
- the load balancer defaults to `403` and forwards only through the generated
  secret-header rule;
- load-balancer ingress uses the AWS-managed CloudFront prefix list, with no
  public `0.0.0.0/0` ingress rule;
- API and worker services both start at desired count zero;
- the endpoint mode is `cloudfront`; and
- the monthly usage budget remains USD 5.

All 16 structural assertions passed. The saved plan is a local ignored review
artifact only; no apply was run.

## Main Cost Drivers

The resources most likely to consume Free Plan credits are RDS PostgreSQL, the
Application Load Balancer, CloudFront, Fargate tasks after services are
enabled, CloudWatch logs and alarms, and stored S3 data. S3 requests, SQS
requests, ECR storage, and DynamoDB on-demand state locking should remain small
for a controlled demo but are still metered.

The budget is an alert, not a hard spending cap. The deployment must still be
torn down after the planned demo window.

## Apply Blockers

No application resources may be applied until all of the following are true:

1. The bootstrap plan is reviewed again and explicitly approved for apply.
2. The main plan is regenerated against the new remote backend.
3. Current AWS pricing and remaining Free Plan credits are checked.
4. The immutable container image, database migration, reviewer provisioning,
   service enablement, and teardown order are ready.

The Step 20C application plan used syntactically valid placeholder certificate
and DNS values. It proves provider access, resource dependencies, security
settings, and cost shape; it is not deployable and must never be applied. The
Step 20D.1 replacement plan supersedes it with
`public_endpoint_mode = "cloudfront"` and contains neither placeholder.
