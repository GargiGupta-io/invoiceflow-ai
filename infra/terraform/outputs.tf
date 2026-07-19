output "api_url" {
  description = "Public HTTPS endpoint after this DNS name is pointed at the load balancer."
  value       = "https://${var.application_domain_name}"
}

output "load_balancer_dns_name" {
  description = "DNS name to use when creating the application DNS record."
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
  description = "Subnets used by API, worker, and one-off migration tasks."
  value       = aws_subnet.app[*].id
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
