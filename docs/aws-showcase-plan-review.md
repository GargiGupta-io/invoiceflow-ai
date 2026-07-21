# AWS Showcase Plan Review

Reviewed through July 22, 2026 from `feature/version-2-pipeline` with Terraform
1.9.8. The plans used the dedicated `InvoiceFlowTerraformDeployRole` and
short-lived browser-login credentials. Only the state bootstrap was applied;
no InvoiceFlow application resources were applied.

## State Bootstrap

The approved state bootstrap created:

- one private S3 state bucket;
- complete S3 public-access blocking;
- bucket-owner-enforced object ownership;
- AES-256 server-side encryption;
- versioning and 90-day expiry for noncurrent versions;
- a TLS-only bucket policy; and
- one encrypted, on-demand DynamoDB lock table.

The bucket and lock table were independently checked after apply. Public access
is blocked, object ownership is bucket-owner enforced, default encryption and
versioning are enabled, the noncurrent-version lifecycle is active, the bucket
policy denies insecure transport, and the lock table is active with on-demand
billing and server-side encryption.

The main stack is now initialized against that S3 backend with DynamoDB state
locking. Saved plans, local backend metadata, and account-specific variable
files remain ignored local artifacts.

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
modes. The rendered deployment policy is 10,147 characters after JSON
compaction, below AWS's 10,240-character inline-role aggregate limit, and has
no medium-or-higher Parliament findings. Its local and installed policy hashes
match exactly.

The replacement real-provider plan was regenerated after remote-backend
initialization and succeeds with 93 additions, 0 changes, 0 deletions, and 5
data reads. Structured inspection of the saved plan confirms:

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

All 18 plan checks passed. The saved plan is a local ignored review artifact
only; no application apply was run.

## Main Cost Drivers

The resources most likely to consume Free Plan credits are RDS PostgreSQL, the
Application Load Balancer, CloudFront, Fargate tasks after services are
enabled, CloudWatch logs and alarms, and stored S3 data. S3 requests, SQS
requests, ECR storage, and DynamoDB on-demand state locking should remain small
for a controlled demo but are still metered.

The budget is an alert, not a hard spending cap. The deployment must still be
torn down after the planned demo window.

## Step 20D.3 Price Check

The public AWS Price List catalogs were checked on July 22, 2026. The newest
catalog publications used by this estimate range from June 22 through July 21,
2026. The estimate uses 730 hours per month and the `ap-south-1` showcase
configuration in the saved plan.

| Resource | Current rate used | Estimated monthly usage |
| --- | ---: | ---: |
| RDS PostgreSQL `db.t4g.micro`, Single-AZ | USD 0.021/hour | USD 15.33 |
| RDS PostgreSQL GP3 storage, 20 GB | USD 0.131/GB-month | USD 2.62 |
| Application Load Balancer | USD 0.0239/hour | USD 17.45 |
| Two load-balancer public IPv4 addresses | USD 0.005/address-hour | USD 7.30 |
| One RDS-managed Secrets Manager secret | USD 0.40/secret-month | USD 0.40 |
| One active Cognito Plus reviewer | USD 0.020/MAU | USD 0.02 |

The stopped-first foundation is therefore approximately **USD 43.12/month**,
**USD 1.42/day**, or **USD 9.92 for seven days** before credits. This estimate
keeps both ECS services at desired count zero. It assumes negligible demo
traffic and no paid load-balancer capacity usage beyond the load-balancer-hour
charge.

When the one API task and one worker task are enabled continuously, their
configured CPU, memory, and two public IPv4 addresses add approximately **USD
64.10/month**, or **USD 2.11/day**. The complete continuously running showcase
is therefore approximately **USD 107.21/month**, or **USD 3.52/day**, before
credits.

CloudFront should remain inside its monthly free request and data-transfer
allowances for this synthetic demo. The eight standard CloudWatch alarms fit
inside CloudWatch's ten-alarm free allocation. The monitoring-only AWS Budget
is free. Low-volume S3, SQS, DynamoDB, Lambda, SNS, ECR, log-ingestion, API-call,
load-balancer-capacity, and data-transfer usage is not assigned a false zero;
it remains usage-dependent and should be small for the controlled demo.

Official pricing references:

- [AWS Free Tier FAQ](https://aws.amazon.com/free/free-tier-faqs/)
- [RDS for PostgreSQL pricing](https://aws.amazon.com/rds/postgresql/pricing/)
- [Elastic Load Balancing pricing](https://aws.amazon.com/elasticloadbalancing/pricing/)
- [VPC public IPv4 pricing](https://aws.amazon.com/vpc/pricing/)
- [Fargate pricing](https://aws.amazon.com/fargate/pricing/)
- [Amazon Cognito pricing](https://aws.amazon.com/cognito/pricing/)
- [CloudWatch pricing](https://aws.amazon.com/cloudwatch/pricing/)
- [CloudFront pricing](https://aws.amazon.com/cloudfront/pricing/)
- [AWS Budgets pricing](https://aws.amazon.com/aws-cost-management/aws-budgets/pricing/)

## Free Plan Verification Boundary

The account owner confirmed that this is an AWS Free Plan account. AWS states
that a Free Plan ends at the earlier of six months or credit exhaustion and
does not become a paid plan unless the owner deliberately upgrades it or takes
one of AWS's documented automatic-upgrade actions.

The dedicated deployment identity intentionally cannot call
`freetier:GetAccountPlanState` or `pricing:GetProducts`. Those denied read calls
are not a reason to broaden the deployment role. Pricing was obtained from the
public AWS catalogs instead. Immediately before application apply, the account
owner must read the Cost and Usage widget in the AWS console and record:

1. remaining Free Tier credit balance;
2. Free Plan expiration date; and
3. confirmation that the account still says **Free Plan**, not **Paid Plan**.

The controlled seven-day showcase requires at least USD 15 of remaining credit
as a conservative local deployment gate. If the balance is lower, the workload
apply is a no-go. Do not create or join an AWS Organization, enable Control
Tower, or deliberately upgrade the account as part of this deployment.

## Apply Readiness Decision

The infrastructure is **technically ready but financially gated**. The saved
93-resource plan, immutable application source tag, migration task, reviewer
provisioner, zero-count services, second service-enablement plan, and teardown
order are prepared. No workload apply is authorized by this review.

The next step may apply the stopped-first foundation only after both of these
conditions are satisfied:

1. the account owner supplies the three manual Free Plan values above; and
2. the account owner gives a separate explicit approval for the cost-bearing
   93-resource apply.

## Remaining Application Apply Gates

No application resources may be applied until all of the following are true:

1. Remaining Free Plan credits and the expiration date are confirmed manually.
2. Separate explicit approval is given for the cost-bearing application apply.

Current pricing and the immutable image, database migration, reviewer
provisioning, service-enablement, and teardown order have been checked. The
state bootstrap and remote-backend plan regeneration are complete. They do not
authorize application deployment.

The Step 20C application plan used syntactically valid placeholder certificate
and DNS values. It proves provider access, resource dependencies, security
settings, and cost shape; it is not deployable and must never be applied. The
Step 20D.1 replacement plan supersedes it with
`public_endpoint_mode = "cloudfront"` and contains neither placeholder.
