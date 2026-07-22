resource "aws_apigatewayv2_api" "showcase" {
  count = local.uses_api_gateway_endpoint ? 1 : 0

  name                         = "${local.name_prefix}-http"
  protocol_type                = "HTTP"
  disable_execute_api_endpoint = false

  lifecycle {
    precondition {
      condition     = local.is_showcase
      error_message = "The API Gateway default endpoint is limited to the synthetic showcase profile. Production requires custom_domain mode with end-to-end HTTPS."
    }
  }
}

resource "aws_apigatewayv2_vpc_link" "showcase" {
  count = local.uses_api_gateway_endpoint ? 1 : 0

  name               = "${local.name_prefix}-link"
  security_group_ids = [aws_security_group.api_gateway_vpc_link[0].id]
  subnet_ids         = aws_subnet.app[*].id

  depends_on = [
    aws_vpc_security_group_egress_rule.api_gateway_to_alb,
    aws_vpc_security_group_ingress_rule.alb_api_gateway_http,
  ]
}

resource "aws_apigatewayv2_integration" "showcase" {
  count = local.uses_api_gateway_endpoint ? 1 : 0

  api_id                 = aws_apigatewayv2_api.showcase[0].id
  integration_type       = "HTTP_PROXY"
  integration_method     = "ANY"
  integration_uri        = aws_lb_listener.cloudfront_origin[0].arn
  connection_type        = "VPC_LINK"
  connection_id          = aws_apigatewayv2_vpc_link.showcase[0].id
  payload_format_version = "1.0"
  timeout_milliseconds   = 30000

  request_parameters = {
    "overwrite:header.X-InvoiceFlow-${random_id.cloudfront_origin_header_name[0].hex}" = random_password.cloudfront_origin_header_value[0].result
  }
}

resource "aws_apigatewayv2_route" "showcase" {
  count = local.uses_api_gateway_endpoint ? 1 : 0

  api_id    = aws_apigatewayv2_api.showcase[0].id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.showcase[0].id}"
}

resource "aws_apigatewayv2_stage" "showcase" {
  count = local.uses_api_gateway_endpoint ? 1 : 0

  api_id      = aws_apigatewayv2_api.showcase[0].id
  name        = "$default"
  auto_deploy = true

  default_route_settings {
    throttling_burst_limit = 20
    throttling_rate_limit  = 10
  }
}
