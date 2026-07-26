resource "aws_cognito_user_pool" "main" {
  name                     = "${local.name_prefix}-users"
  user_pool_tier           = "PLUS"
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]
  deletion_protection      = local.cognito_deletion_protection

  admin_create_user_config {
    allow_admin_create_user_only = true
  }

  password_policy {
    minimum_length                   = 12
    require_lowercase                = true
    require_numbers                  = true
    require_symbols                  = true
    require_uppercase                = true
    temporary_password_validity_days = 7
  }

  schema {
    attribute_data_type      = "String"
    developer_only_attribute = false
    mutable                  = false
    name                     = "organization_id"
    required                 = false

    string_attribute_constraints {
      min_length = 36
      max_length = 36
    }
  }

  user_attribute_update_settings {
    attributes_require_verification_before_update = ["email"]
  }

  user_pool_add_ons {
    advanced_security_mode = "ENFORCED"
  }

  lambda_config {
    pre_token_generation_config {
      lambda_arn     = aws_lambda_function.pre_token_generation.arn
      lambda_version = "V2_0"
    }
  }
}

resource "aws_cognito_resource_server" "invoiceflow" {
  identifier   = "invoiceflow"
  name         = "InvoiceFlow API"
  user_pool_id = aws_cognito_user_pool.main.id

  scope {
    scope_name        = "read"
    scope_description = "Read tenant documents and evidence"
  }

  scope {
    scope_name        = "upload"
    scope_description = "Upload tenant documents"
  }

  scope {
    scope_name        = "process"
    scope_description = "Dispatch document processing"
  }

  scope {
    scope_name        = "review"
    scope_description = "Create tenant review decisions"
  }

  scope {
    scope_name        = "delete"
    scope_description = "Delete tenant documents"
  }
}

resource "aws_cognito_user_pool_client" "web" {
  name         = "${local.name_prefix}-web"
  user_pool_id = aws_cognito_user_pool.main.id

  generate_secret                      = false
  prevent_user_existence_errors        = "ENABLED"
  enable_token_revocation              = true
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  supported_identity_providers         = ["COGNITO"]
  callback_urls                        = local.oauth_callback_urls
  logout_urls                          = local.oauth_logout_urls
  allowed_oauth_scopes = [
    "openid",
    "email",
    "invoiceflow/read",
    "invoiceflow/upload",
    "invoiceflow/process",
    "invoiceflow/review",
    "invoiceflow/delete",
  ]

  access_token_validity  = 15
  id_token_validity      = 15
  refresh_token_validity = 1

  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "days"
  }

  depends_on = [aws_cognito_resource_server.invoiceflow]
}

resource "random_id" "cognito_domain" {
  byte_length = 4
}

resource "aws_cognito_user_pool_domain" "main" {
  domain       = "${local.name_prefix}-${random_id.cognito_domain.hex}"
  user_pool_id = aws_cognito_user_pool.main.id
}
