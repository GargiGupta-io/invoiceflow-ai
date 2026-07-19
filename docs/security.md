# Version 2 Security Model

This is a focused threat model for the tenant-isolated document pipeline.

## Protected Assets

- Original invoice and AR documents
- Extracted fields and page text
- Policy evidence and recommendations
- Reviewer notes and decisions
- Audit history
- Cognito tokens
- Database credentials and temporary document URLs

## Main Trust Boundaries

1. Browser to public HTTPS load balancer
2. Load balancer to private FastAPI tasks
3. FastAPI/worker to private PostgreSQL
4. FastAPI/worker to private S3 and SQS through IAM task roles
5. Authenticated tenant context to tenant-filtered repositories

## Threats And Controls

| Threat | Control |
| --- | --- |
| Cross-tenant UUID guessing | Tenant comes from a verified token; every repository query filters organization ID; unknown and foreign resources return the same not-found response. |
| Spoofed upload type | Extension, MIME, signature, parser, size, page-count, encryption, and image-dimension checks. |
| Public document exposure | S3 Block Public Access, bucket-owner-enforced ownership, no public ACLs, TLS-only bucket policy, UUID keys. |
| Leaked document link | Backend ownership check, GET-only five-minute presigned URL, no-store response, URL redaction. |
| Credential leakage | RDS-managed password in Secrets Manager, ECS secret injection, no static AWS keys, recursive log redaction. |
| Overpowered services | Separate API and worker task roles with resource-scoped S3 and SQS actions. |
| Duplicate queue delivery | Tenant-scoped idempotency key and atomic job claim in PostgreSQL. |
| Audit tampering | Append-only audit repository and PostgreSQL update/delete trigger. |
| Retained sensitive data | User deletion, bounded retention worker, page/result/review purge, S3 lifecycle backstops. |
| Plain HTTP | Load balancer redirects HTTP to TLS 1.2/1.3 HTTPS listener. |
| Public database access | RDS has no public address and accepts PostgreSQL only from the task security group. |

## Authentication Versus Authorization

Cognito proves who signed in and signs the access token. FastAPI verifies the
signature, issuer, client, token type, time claims, organization claim, internal
user status, and required OAuth scope. A pre-token Lambda copies the immutable,
admin-managed organization attribute into access tokens because Cognito does
not include custom attributes there automatically. IAM does not authorize end
users; it limits what the API and worker services can do inside AWS.

## Sensitive Logging Rules

Allowed operational fields include request ID, job ID, status, duration, page
count, safe error category, and queue outcome. Logs must not contain document
text, reviewer notes, JWTs, cookies, authorization headers, database URLs,
queue receipt handles, S3 keys, or presigned URLs.

## Residual Risks

- Terraform apply permissions and remote state controls must be reviewed in the
  target AWS account.
- Cognito users must be provisioned together with matching internal tenant rows.
- Local Tesseract quality must be validated against representative scans before
  finance use; managed Textract remains a future adapter.
- The repository's synthetic fixtures are not evidence of production finance
  accuracy.
- A penetration test and cloud-configuration review are still required before
  accepting real customer documents.
