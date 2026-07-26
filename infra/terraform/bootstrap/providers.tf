provider "aws" {
  region = var.aws_region

  default_tags {
    tags = merge(var.tags, {
      Application = "invoiceflow"
      Environment = var.environment
      ManagedBy   = "Terraform"
    })
  }
}
