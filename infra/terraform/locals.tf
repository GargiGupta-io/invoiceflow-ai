locals {
  name_prefix = "${var.project_name}-${var.environment}"
  azs         = slice(data.aws_availability_zones.available.names, 0, 2)
  is_showcase = var.deployment_profile == "showcase"

  nat_gateway_count        = local.is_showcase ? 0 : (var.single_nat_gateway ? 1 : 2)
  runtime_subnet_ids       = local.is_showcase ? aws_subnet.public[*].id : aws_subnet.app[*].id
  runtime_assign_public_ip = local.is_showcase
  runtime_s3_route_tables  = local.is_showcase ? [aws_route_table.public.id] : aws_route_table.app[*].id

  database_multi_az                 = local.is_showcase ? false : var.database_multi_az
  database_max_allocated_storage    = local.is_showcase ? 0 : var.database_max_allocated_storage
  database_backup_retention_days    = local.is_showcase ? 1 : 7
  database_deletion_protection      = local.is_showcase ? false : var.database_deletion_protection
  database_skip_final_snapshot      = local.is_showcase ? true : var.database_skip_final_snapshot
  database_performance_insights     = local.is_showcase ? false : true
  load_balancer_deletion_protection = local.is_showcase ? false : true
  cognito_deletion_protection       = local.is_showcase ? "INACTIVE" : "ACTIVE"
  container_insights                = local.is_showcase ? "disabled" : "enabled"
  api_max_capacity                  = local.is_showcase ? var.api_desired_count : 6
  document_bucket_force_destroy     = local.is_showcase

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
    { name = "AUTH_BROWSER_DOMAIN", value = "https://${aws_cognito_user_pool_domain.main.domain}.auth.${var.aws_region}.amazoncognito.com" },
    { name = "AUTH_REDIRECT_URI", value = var.oauth_callback_urls[0] },
    { name = "AUTH_LOGOUT_URI", value = var.oauth_logout_urls[0] },
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
