# Version 2 Reliability Model

InvoiceFlow treats PostgreSQL as the durable source of job truth and SQS as an
at-least-once delivery mechanism.

## Processing Guarantees

```text
API saves unique tenant job
  -> API sends identifier-only SQS message
  -> worker atomically claims job
  -> duplicate delivery sees existing state
  -> worker saves result/pages/audit in one transaction
  -> worker deletes SQS message only after commit
```

This is idempotent processing, not exactly-once queue delivery.

## Retry And Dead-Letter Behavior

- Validation and malformed-message failures are permanent.
- Temporary S3, PostgreSQL, OCR, and provider failures return to the queue.
- Visibility delay increases exponentially and is capped.
- A heartbeat extends visibility during long processing.
- Stale PostgreSQL processing claims can be recovered.
- SQS moves a repeatedly received message to the DLQ after four receives.
- A completed duplicate message is acknowledged without repeating extraction.

## Health Contracts

- `/health/live` proves only that the API process can answer HTTP.
- `/health/ready` checks PostgreSQL, S3, and SQS without exposing infrastructure
  identifiers or provider errors.
- The internal showcase load balancer uses liveness so a temporary dependency
  outage does not create a container restart loop; API Gateway reaches it only
  through the VPC link.
- Deployment verification must check readiness before directing reviewers to a
  new release.

## Observability

Worker events are one-line redacted JSON with request/job correlation and
CloudWatch Embedded Metric Format values. Terraform adds alarms for:

- ALB target 5xx responses
- p95 API target latency
- SQS backlog
- oldest queued-message age
- any DLQ message
- worker failure metrics
- sustained RDS CPU
- low RDS free storage

The queue also publishes standard SQS metrics automatically.

## Deployment Safety

- ECR tags are immutable and scanned on push.
- ECS services use deployment circuit breakers with rollback.
- Database migrations run as a separate one-off task before services update.
- Production RDS uses encryption, Multi-AZ, seven-day backups, deletion
  protection, and a final snapshot by default.
- The Free Plan showcase keeps RDS private but uses single-AZ deployment,
  one-day backups, and teardown-friendly protection settings.
- S3 is private, encrypted, versioned, and non-public in both profiles.
- Production uses one NAT gateway by default; showcase uses no NAT gateway and
  gives tightly firewalled Fargate tasks public egress instead.
- The showcase profile fixes API and worker capacity at one task each and does
  not create autoscaling resources.
- The showcase profile creates pre-credit AWS Budget alerts when an alarm email
  is configured.

## Verified Showcase State

The July 26, 2026 deployment verification established:

- API Gateway uses a VPC-link integration to an active internal load balancer.
- The API target is healthy, and both ECS services report completed rollouts
  with one desired and one running task.
- `/health/live`, `/health/ready`, `/ui`, and `/reviewer/` respond through the
  public API Gateway endpoint.
- PostgreSQL, S3, and SQS report ready.
- The processing queue and DLQ are empty.
- The pushed ECR image scan completed with zero findings.
- A post-apply Terraform plan reports no changes.
- 188 backend tests, 21 reviewer tests, seven deterministic evaluation cases,
  the reviewer production build, and both Terraform tests pass.

## Evidence Still Required

Before calling the pipeline production-proven, run and publish sanitized results
for:

1. PostgreSQL integration tests against the deployed schema.
2. Cross-user authorization tests using two real Cognito tenants.
3. Ten, 25, and 50 concurrent upload workflows.
4. Queue-drain and retry/DLQ tests.
5. OCR/extraction evaluation using an approved real policy pack and historical
   cases with sensitive data removed.
6. Restore, migration rollback, retention, and incident-response exercises.

The current deterministic seven-case evaluation is a reproducible development
proof, not a production reliability claim.
