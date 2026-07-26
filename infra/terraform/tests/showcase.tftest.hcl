mock_provider "aws" {}

mock_provider "aws" {
  alias = "billing"
}

mock_provider "random" {}
mock_provider "archive" {}

override_data {
  target = data.aws_availability_zones.available
  values = {
    names = ["ap-south-1a", "ap-south-1b"]
  }
}

override_data {
  target = data.aws_caller_identity.current
  values = {
    account_id = "123456789012"
    arn        = "arn:aws:iam::123456789012:user/terraform-test"
    user_id    = "AIDATESTIDENTITY"
  }
}

override_data {
  target = data.aws_ec2_managed_prefix_list.cloudfront_origin
  values = {
    id   = "pl-12345678"
    name = "com.amazonaws.global.cloudfront.origin-facing"
  }
}

override_data {
  target = data.aws_iam_policy_document.ecs_task_assume
  values = { json = "{}" }
}

override_data {
  target = data.aws_iam_policy_document.execution_secrets
  values = { json = "{}" }
}

override_data {
  target = data.aws_iam_policy_document.api
  values = { json = "{}" }
}

override_data {
  target = data.aws_iam_policy_document.worker
  values = { json = "{}" }
}

override_data {
  target = data.aws_iam_policy_document.provisioner
  values = { json = "{}" }
}

override_data {
  target = data.aws_iam_policy_document.documents_bucket
  values = { json = "{}" }
}

override_data {
  target = data.aws_iam_policy_document.lambda_assume
  values = { json = "{}" }
}

run "showcase_cost_guardrails" {
  command = plan

  variables {
    deployment_profile   = "showcase"
    environment          = "showcase"
    public_endpoint_mode = "api_gateway"
    container_image_tag  = "abcdef123456"
    services_enabled     = true
    api_desired_count    = 1
    worker_desired_count = 1
    alarm_email          = "owner@example.com"
  }

  assert {
    condition = (
      length(aws_cloudfront_distribution.app) == 0 &&
      length(aws_apigatewayv2_api.showcase) == 1 &&
      length(aws_apigatewayv2_vpc_link.showcase) == 1 &&
      length(aws_apigatewayv2_integration.showcase) == 1 &&
      length(aws_apigatewayv2_route.showcase) == 1 &&
      length(aws_apigatewayv2_stage.showcase) == 1 &&
      length(aws_lb_listener.cloudfront_origin) == 1 &&
      length(aws_lb_listener_rule.cloudfront_origin) == 1 &&
      length(aws_lb_listener.https) == 0 &&
      length(aws_vpc_security_group_ingress_rule.alb_cloudfront_http) == 0 &&
      length(aws_vpc_security_group_ingress_rule.alb_api_gateway_http) == 1 &&
      length(aws_vpc_security_group_egress_rule.api_gateway_to_alb) == 1 &&
      length(aws_vpc_security_group_ingress_rule.alb_http) == 0 &&
      length(aws_vpc_security_group_ingress_rule.alb_https) == 0
    )
    error_message = "The domain-free showcase must expose only the API Gateway VPC-link path to the guarded HTTP origin."
  }

  assert {
    condition = (
      !aws_apigatewayv2_api.showcase[0].disable_execute_api_endpoint &&
      aws_apigatewayv2_integration.showcase[0].connection_type == "VPC_LINK" &&
      aws_apigatewayv2_integration.showcase[0].integration_type == "HTTP_PROXY" &&
      aws_apigatewayv2_stage.showcase[0].default_route_settings[0].throttling_burst_limit == 20 &&
      aws_apigatewayv2_stage.showcase[0].default_route_settings[0].throttling_rate_limit == 10 &&
      aws_lb_listener.cloudfront_origin[0].default_action[0].fixed_response[0].status_code == "403"
    )
    error_message = "API Gateway must supply viewer TLS, use the VPC link, preserve the guarded origin, and enforce demo throttles."
  }

  assert {
    condition     = aws_lb.api.internal
    error_message = "The API Gateway VPC link must target an internal load balancer."
  }

  assert {
    condition     = length(aws_nat_gateway.main) == 0 && length(aws_eip.nat) == 0
    error_message = "The showcase profile must not provision NAT gateways or their elastic IPs."
  }

  assert {
    condition     = length(aws_route.app_egress) == 0
    error_message = "The showcase profile must not create private-subnet routes to a NAT gateway."
  }

  assert {
    condition     = aws_ecs_service.api.network_configuration[0].assign_public_ip && aws_ecs_service.worker.network_configuration[0].assign_public_ip
    error_message = "Showcase Fargate services need public egress when NAT gateways are disabled."
  }

  assert {
    condition     = aws_appautoscaling_target.api[0].max_capacity == 1
    error_message = "Showcase API autoscaling must be capped at one task."
  }

  assert {
    condition = (
      !aws_db_instance.main.publicly_accessible &&
      !aws_db_instance.main.multi_az &&
      aws_db_instance.main.backup_retention_period == 1 &&
      aws_db_instance.main.max_allocated_storage == 0 &&
      !aws_db_instance.main.performance_insights_enabled
    )
    error_message = "Showcase RDS must remain private while disabling high-cost production options."
  }

  assert {
    condition     = !aws_lb.api.enable_deletion_protection && aws_cognito_user_pool.main.deletion_protection == "INACTIVE"
    error_message = "Showcase resources must support a deliberate, reviewed teardown."
  }

  assert {
    condition = one([
      for attribute in aws_cognito_user_pool.main.schema : attribute
      if attribute.name == "organization_id"
    ]).required == false
    error_message = "Cognito custom organization attributes must be optional in the pool schema and assigned by the trusted reviewer provisioner."
  }

  assert {
    condition     = aws_s3_bucket.documents.force_destroy
    error_message = "The showcase document bucket must support complete teardown after retention review."
  }

  assert {
    condition     = length(aws_budgets_budget.monthly_usage) == 1 && !aws_budgets_budget.monthly_usage[0].cost_types[0].include_credit
    error_message = "Showcase infrastructure must configure pre-credit cost alerts when alarm_email is set."
  }
}

run "production_security_defaults" {
  command = plan

  variables {
    deployment_profile      = "production"
    environment             = "production"
    public_endpoint_mode    = "custom_domain"
    certificate_arn         = "arn:aws:acm:ap-south-1:123456789012:certificate/00000000-0000-0000-0000-000000000000"
    application_domain_name = "invoiceflow.example.com"
    oauth_callback_urls     = ["https://invoiceflow.example.com/reviewer/callback"]
    oauth_logout_urls       = ["https://invoiceflow.example.com/reviewer/"]
    container_image_tag     = "abcdef123456"
    services_enabled        = true
    api_desired_count       = 2
    worker_desired_count    = 1
    alarm_email             = ""
  }

  assert {
    condition = (
      length(aws_cloudfront_distribution.app) == 0 &&
      length(aws_apigatewayv2_api.showcase) == 0 &&
      length(aws_apigatewayv2_vpc_link.showcase) == 0 &&
      length(aws_lb_listener.cloudfront_origin) == 0 &&
      length(aws_lb_listener.https) == 1 &&
      length(aws_vpc_security_group_ingress_rule.alb_cloudfront_http) == 0 &&
      length(aws_vpc_security_group_ingress_rule.alb_api_gateway_http) == 0 &&
      length(aws_vpc_security_group_ingress_rule.alb_http) == 1 &&
      length(aws_vpc_security_group_ingress_rule.alb_https) == 1
    )
    error_message = "Production must retain the custom-domain HTTPS load balancer path."
  }

  assert {
    condition     = !aws_lb.api.internal
    error_message = "Production custom-domain mode must retain an internet-facing load balancer."
  }

  assert {
    condition     = length(aws_nat_gateway.main) == 1 && length(aws_route.app_egress) == 2
    error_message = "Production must retain NAT-backed private application subnets by default."
  }

  assert {
    condition     = !aws_ecs_service.api.network_configuration[0].assign_public_ip && !aws_ecs_service.worker.network_configuration[0].assign_public_ip
    error_message = "Production Fargate services must not receive public IP addresses."
  }

  assert {
    condition = (
      !aws_db_instance.main.publicly_accessible &&
      aws_db_instance.main.multi_az &&
      aws_db_instance.main.backup_retention_period == 7 &&
      aws_db_instance.main.performance_insights_enabled &&
      aws_db_instance.main.deletion_protection &&
      !aws_db_instance.main.skip_final_snapshot
    )
    error_message = "Production RDS security, availability, and recovery defaults must remain enabled."
  }

  assert {
    condition = (
      aws_lb.api.enable_deletion_protection &&
      aws_cognito_user_pool.main.deletion_protection == "ACTIVE" &&
      !aws_s3_bucket.documents.force_destroy
    )
    error_message = "Production deletion protections must remain enabled."
  }

  assert {
    condition     = length(aws_budgets_budget.monthly_usage) == 0
    error_message = "No email means Terraform must not create an unusable budget notification."
  }
}
