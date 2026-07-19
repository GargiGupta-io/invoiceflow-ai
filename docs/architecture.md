# Version 2 Architecture

InvoiceFlow Version 2 separates fast user requests from slow document work and
keeps every persistent resource inside an authenticated organization boundary.

## Runtime Flow

```text
Reviewer browser
  -> Cognito authorization-code login
  -> HTTPS load balancer
  -> FastAPI on private Fargate
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

- Public: HTTPS Application Load Balancer only
- Private with outbound NAT: API, worker, and migration Fargate tasks
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

The application contracts and Terraform definition exist on the
`feature/version-2-pipeline` branch. The existing Render site remains the
Version 1 deterministic portfolio demo. This document does not claim that the
AWS stack has been applied or that production users are connected.
