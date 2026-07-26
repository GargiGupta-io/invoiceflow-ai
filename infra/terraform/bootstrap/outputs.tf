output "state_bucket_name" {
  description = "Private bucket to pass to the application stack backend configuration."
  value       = aws_s3_bucket.state.id
}

output "lock_table_name" {
  description = "DynamoDB lock table to pass to the application stack backend configuration."
  value       = aws_dynamodb_table.locks.name
}

output "backend_key" {
  description = "Recommended state object key for this environment."
  value       = "invoiceflow/${var.environment}.tfstate"
}
