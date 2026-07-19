provider "aws" {
  region = var.aws_region

  default_tags {
    tags = merge(var.tags, {
      Application = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
    })
  }
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
data "aws_availability_zones" "available" {
  state = "available"
}
