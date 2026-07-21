output "api_url" {
  description = "Public HTTPS endpoint for the reviewer and API."
  value       = local.public_base_url
}

output "public_endpoint_mode" {
  description = "Whether this stack uses the generated CloudFront URL or a custom-domain ALB certificate."
  value       = var.public_endpoint_mode
}

output "cloudfront_distribution_id" {
  description = "Domain-free showcase distribution ID, or null in custom-domain mode."
  value       = try(aws_cloudfront_distribution.app[0].id, null)
}

output "load_balancer_dns_name" {
  description = "Origin DNS name. Direct access is blocked when CloudFront mode is active."
  value       = aws_lb.api.dns_name
}

output "ecr_repository_url" {
  description = "Repository that receives the immutable InvoiceFlow image."
  value       = aws_ecr_repository.app.repository_url
}

output "ecs_cluster_name" {
  description = "Cluster containing API and worker services."
  value       = aws_ecs_cluster.main.name
}

output "migration_task_definition_arn" {
  description = "Run this task once after pushing a new image and before updating services."
  value       = aws_ecs_task_definition.migration.arn
}

output "provisioner_task_definition_arn" {
  description = "Run this task to create a Cognito reviewer and matching tenant database rows."
  value       = aws_ecs_task_definition.provisioner.arn
}

output "api_service_name" {
  description = "ECS API service enabled only after a successful migration."
  value       = aws_ecs_service.api.name
}

output "worker_service_name" {
  description = "ECS worker service enabled only after a successful migration."
  value       = aws_ecs_service.worker.name
}

output "private_app_subnet_ids" {
  description = "Private application subnets used by the production profile."
  value       = aws_subnet.app[*].id
}

output "runtime_subnet_ids" {
  description = "Subnets used by API, worker, migration, and provisioner tasks for the selected deployment profile."
  value       = local.runtime_subnet_ids
}

output "runtime_assign_public_ip" {
  description = "Whether one-off Fargate tasks must request a public IP in the selected deployment profile."
  value       = local.runtime_assign_public_ip
}

output "task_security_group_id" {
  description = "Security group for API, worker, and migration tasks."
  value       = aws_security_group.tasks.id
}

output "document_bucket_name" {
  description = "Private document bucket."
  value       = aws_s3_bucket.documents.id
}

output "processing_queue_url" {
  description = "SQS queue consumed by the document worker."
  value       = aws_sqs_queue.processing.url
}

output "dead_letter_queue_url" {
  description = "Queue containing repeatedly failing document jobs."
  value       = aws_sqs_queue.dead_letter.url
}

output "database_endpoint" {
  description = "Private RDS endpoint; reachable only from task subnets."
  value       = aws_db_instance.main.endpoint
  sensitive   = true
}

output "cognito_user_pool_id" {
  description = "Cognito user pool used by InvoiceFlow."
  value       = aws_cognito_user_pool.main.id
}

output "cognito_client_id" {
  description = "Public browser client ID."
  value       = aws_cognito_user_pool_client.web.id
}

output "cognito_hosted_ui_domain" {
  description = "Hosted UI domain for the authorization-code flow."
  value       = "https://${aws_cognito_user_pool_domain.main.domain}.auth.${var.aws_region}.amazoncognito.com"
}

output "alarm_topic_arn" {
  description = "SNS topic receiving operational alarms."
  value       = aws_sns_topic.alarms.arn
}

output "monthly_cost_budget_name" {
  description = "Account-wide pre-credit usage budget name when alarm_email is configured."
  value       = try(aws_budgets_budget.monthly_usage[0].name, null)
}
