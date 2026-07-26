# Version 2 Architecture

InvoiceFlow Version 2 separates fast user requests from slow document work and
keeps every persistent resource inside an authenticated organization boundary.

## Runtime Flow

```text
Reviewer browser
  -> Cognito authorization-code login
  -> API Gateway HTTPS endpoint
  -> VPC link
  -> internal Application Load Balancer
  -> FastAPI on Fargate
       -> validate tenant and scope
       -> validate upload
       -> private S3 quarantine object
       -> PostgreSQL document and idempotent job
       -> SQS message

SQS message
  -> worker on private Fargate
       -> claim job in PostgreSQL
       -> bounded S3 read
       -> native PDF extraction or local OCR fallback
       -> policy-grounded AP/AR workflow
       -> page evidence, result, and audit in PostgreSQL
       -> promote S3 object
       -> acknowledge message only after commit

Reviewer browser
  -> protected history/search/review APIs
  -> short-lived document access after ownership check
```

## Protected Reviewer Flow

The React reviewer workspace uses separate tenant-authorized requests instead
of receiving one unrestricted payload:

```text
Open history
  -> select owned document
  -> load safe case result + extracted pages + audit events
  -> request five-minute document link only when needed
  -> submit attributed review decision
  -> reload review and append-only audit history
```

The case result exposes the latest completed workflow output and policy
evidence, but processing-job responses continue to omit raw result storage.
The browser never receives an S3 key, AWS credential, organization selector,
or presigned URL until the reviewer explicitly requests document access.

## Data Ownership

PostgreSQL stores organizations, users, document metadata, jobs, extracted
page text, decisions, reviews, and append-only audit events. Composite tenant
foreign keys prevent a child row from referring to a document in another
organization.

S3 stores original binary documents under UUID-only tenant/document keys:

```text
quarantine/<organization UUID>/<document UUID>
validated/<organization UUID>/<document UUID>
```

SQS messages carry identifiers, not document contents or credentials.

## Deployment Shape

- Showcase public edge: API Gateway HTTPS endpoint only
- Showcase private ingress: VPC link to an internal load balancer in the
  application subnets
- Showcase runtime: one API and one worker Fargate task in public subnets for
  outbound access without NAT; inbound traffic remains security-group-limited
  to the internal load balancer
- Production public edge: custom-domain HTTPS Application Load Balancer
- Production runtime: API, worker, and migration Fargate tasks in private
  application subnets with outbound NAT
- Isolated: RDS PostgreSQL subnets with no internet route
- Managed identity: Cognito users and scoped access tokens
- Service identity: separate API, worker, and execution IAM roles
- Operations: CloudWatch logs, Embedded Metric Format, queue/RDS/ALB alarms
- Delivery: one immutable ECR image, used with different commands

## Migration Contract

The migration task uses the release image and runs `alembic upgrade head`.
Deployment must stop if this task fails. API and worker services are updated
only after the migration exits successfully.

## Current Status

The synthetic Version 2 showcase is deployed in `ap-south-1` from the
`feature/version-2-pipeline` branch:

- API Gateway base URL:
  `https://rwudt83b2h.execute-api.ap-south-1.amazonaws.com`
- internal load balancer target health: healthy
- API and worker services: one desired and one running task each
- PostgreSQL, S3, and SQS readiness: ready
- Terraform post-apply plan: no changes

The Render site remains the lighter Version 1 deterministic portfolio demo.
The AWS deployment uses synthetic data and proves the architecture and
operational path; it does not claim production finance accuracy or connected
customer use.
