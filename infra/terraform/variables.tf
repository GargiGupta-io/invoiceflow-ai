variable "project_name" {
  description = "Short name used in AWS resource names."
  type        = string
  default     = "invoiceflow"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,20}$", var.project_name))
    error_message = "project_name must be 3-21 lowercase letters, numbers, or hyphens."
  }
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "production"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,15}$", var.environment))
    error_message = "environment must be 2-16 lowercase letters, numbers, or hyphens."
  }
}

variable "aws_region" {
  description = "AWS region for the complete stack."
  type        = string
  default     = "ap-south-1"
}

variable "vpc_cidr" {
  description = "CIDR range for the InvoiceFlow VPC."
  type        = string
  default     = "10.42.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "Two public subnet CIDRs for the load balancer and NAT gateways."
  type        = list(string)
  default     = ["10.42.0.0/24", "10.42.1.0/24"]

  validation {
    condition     = length(var.public_subnet_cidrs) == 2
    error_message = "Exactly two public subnet CIDRs are required."
  }
}

variable "app_subnet_cidrs" {
  description = "Two private subnet CIDRs for Fargate tasks."
  type        = list(string)
  default     = ["10.42.10.0/24", "10.42.11.0/24"]

  validation {
    condition     = length(var.app_subnet_cidrs) == 2
    error_message = "Exactly two application subnet CIDRs are required."
  }
}

variable "database_subnet_cidrs" {
  description = "Two isolated subnet CIDRs for PostgreSQL."
  type        = list(string)
  default     = ["10.42.20.0/24", "10.42.21.0/24"]

  validation {
    condition     = length(var.database_subnet_cidrs) == 2
    error_message = "Exactly two database subnet CIDRs are required."
  }
}

variable "single_nat_gateway" {
  description = "Use one NAT gateway to reduce demo cost. Disable for one NAT gateway per AZ."
  type        = bool
  default     = true
}

variable "certificate_arn" {
  description = "ACM certificate ARN for the public HTTPS listener."
  type        = string

  validation {
    condition     = can(regex("^arn:aws:acm:", var.certificate_arn))
    error_message = "certificate_arn must be an ACM certificate ARN."
  }
}

variable "application_domain_name" {
  description = "Public DNS name covered by the ACM certificate. Create its DNS record after apply."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9.-]+[a-z0-9]$", var.application_domain_name))
    error_message = "application_domain_name must be a valid lowercase DNS name."
  }
}

variable "allowed_ingress_cidrs" {
  description = "IPv4 CIDRs allowed to reach the public HTTPS load balancer."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "container_image_tag" {
  description = "Immutable image tag deployed to API, worker, and migration tasks."
  type        = string

  validation {
    condition     = var.container_image_tag != "latest" && can(regex("^[A-Za-z0-9_.-]{7,128}$", var.container_image_tag))
    error_message = "container_image_tag must be an immutable tag of at least 7 characters and cannot be latest."
  }
}

variable "api_desired_count" {
  description = "Number of API tasks."
  type        = number
  default     = 2

  validation {
    condition     = var.api_desired_count >= 1
    error_message = "api_desired_count must be at least 1."
  }
}

variable "worker_desired_count" {
  description = "Number of document worker tasks."
  type        = number
  default     = 1

  validation {
    condition     = var.worker_desired_count >= 1
    error_message = "worker_desired_count must be at least 1."
  }
}

variable "database_name" {
  description = "Initial PostgreSQL database name."
  type        = string
  default     = "invoiceflow"
}

variable "database_username" {
  description = "PostgreSQL master/application username."
  type        = string
  default     = "invoiceflow_app"
}

variable "database_instance_class" {
  description = "RDS instance class."
  type        = string
  default     = "db.t4g.micro"
}

variable "database_multi_az" {
  description = "Run a standby RDS instance in another availability zone."
  type        = bool
  default     = true
}

variable "database_allocated_storage" {
  description = "Initial encrypted RDS storage in GiB."
  type        = number
  default     = 20
}

variable "database_max_allocated_storage" {
  description = "RDS storage autoscaling limit in GiB."
  type        = number
  default     = 100
}

variable "database_deletion_protection" {
  description = "Protect the database from accidental Terraform deletion."
  type        = bool
  default     = true
}

variable "database_skip_final_snapshot" {
  description = "Skip the final RDS snapshot. Use false for production."
  type        = bool
  default     = false
}

variable "log_retention_days" {
  description = "CloudWatch log retention."
  type        = number
  default     = 30
}

variable "document_retention_days" {
  description = "Application and S3 document retention period."
  type        = number
  default     = 90
}

variable "alarm_email" {
  description = "Optional email subscription for the CloudWatch alarm topic."
  type        = string
  default     = ""
}

variable "oauth_callback_urls" {
  description = "Allowed Cognito authorization-code callback URLs."
  type        = list(string)
}

variable "oauth_logout_urls" {
  description = "Allowed Cognito logout return URLs."
  type        = list(string)
}

variable "tags" {
  description = "Additional tags applied to all supported resources."
  type        = map(string)
  default     = {}
}
