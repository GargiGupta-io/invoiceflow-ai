variable "aws_region" {
  description = "AWS region containing the state bucket and lock table."
  type        = string
  default     = "ap-south-1"
}

variable "environment" {
  description = "Environment whose Terraform state this backend protects."
  type        = string
  default     = "showcase"

  validation {
    condition     = contains(["showcase", "production"], var.environment)
    error_message = "environment must be showcase or production."
  }
}

variable "state_bucket_name" {
  description = "Globally unique private S3 bucket name for Terraform state."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$", var.state_bucket_name))
    error_message = "state_bucket_name must be a valid lowercase S3 bucket name."
  }
}

variable "lock_table_name" {
  description = "DynamoDB table used for Terraform state locking."
  type        = string
  default     = "invoiceflow-terraform-locks"
}

variable "tags" {
  description = "Additional tags applied to the backend resources."
  type        = map(string)
  default     = {}
}
