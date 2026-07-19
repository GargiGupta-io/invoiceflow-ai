locals {
  name_prefix = "${var.project_name}-${var.environment}"
  azs         = slice(data.aws_availability_zones.available.names, 0, 2)

  common_environment = [
    { name = "APP_ENV", value = var.environment },
    { name = "AWS_REGION", value = var.aws_region },
    { name = "DATABASE_URL", value = "" },
    { name = "DATABASE_HOST", value = aws_db_instance.main.address },
    { name = "DATABASE_PORT", value = tostring(aws_db_instance.main.port) },
    { name = "DATABASE_NAME", value = var.database_name },
    { name = "DATABASE_USER", value = var.database_username },
    { name = "S3_BUCKET_NAME", value = aws_s3_bucket.documents.id },
    { name = "S3_QUARANTINE_PREFIX", value = "quarantine" },
    { name = "S3_VALIDATED_PREFIX", value = "validated" },
    { name = "S3_SSE_ALGORITHM", value = "AES256" },
    { name = "S3_PRESIGNED_URL_TTL_SECONDS", value = "300" },
    { name = "SQS_QUEUE_URL", value = aws_sqs_queue.processing.url },
    { name = "SQS_REDRIVE_MAX_RECEIVE_COUNT", value = "4" },
    { name = "AUTH_ISSUER", value = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.main.id}" },
    { name = "AUTH_CLIENT_ID", value = aws_cognito_user_pool_client.web.id },
    { name = "AUTH_ORGANIZATION_CLAIM", value = "custom:organization_id" },
    { name = "DOCUMENT_RETENTION_DAYS", value = tostring(var.document_retention_days) },
    { name = "CLOUDWATCH_METRIC_NAMESPACE", value = "InvoiceFlow/${var.environment}" },
    { name = "LOG_LEVEL", value = "INFO" },
  ]

  database_password_secret = [{
    name      = "DATABASE_PASSWORD"
    valueFrom = "${aws_db_instance.main.master_user_secret[0].secret_arn}:password::"
  }]
}
