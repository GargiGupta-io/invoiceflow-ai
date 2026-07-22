data "aws_ec2_managed_prefix_list" "cloudfront_origin" {
  count = local.uses_cloudfront_endpoint ? 1 : 0
  name  = "com.amazonaws.global.cloudfront.origin-facing"
}

resource "aws_security_group" "alb" {
  name        = "${local.name_prefix}-alb"
  description = "InvoiceFlow public entry or managed HTTPS origin"
  vpc_id      = aws_vpc.main.id

  tags = { Name = "${local.name_prefix}-alb" }
}

resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  for_each = local.uses_managed_endpoint ? toset([]) : toset(var.allowed_ingress_cidrs)

  security_group_id = aws_security_group.alb.id
  cidr_ipv4         = each.value
  from_port         = 80
  to_port           = 80
  ip_protocol       = "tcp"
  description       = "Redirect HTTP to HTTPS"
}

resource "aws_vpc_security_group_ingress_rule" "alb_https" {
  for_each = local.uses_managed_endpoint ? toset([]) : toset(var.allowed_ingress_cidrs)

  security_group_id = aws_security_group.alb.id
  cidr_ipv4         = each.value
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
  description       = "Public HTTPS"
}

resource "aws_vpc_security_group_ingress_rule" "alb_cloudfront_http" {
  count = local.uses_cloudfront_endpoint ? 1 : 0

  security_group_id = aws_security_group.alb.id
  prefix_list_id    = data.aws_ec2_managed_prefix_list.cloudfront_origin[0].id
  from_port         = 80
  to_port           = 80
  ip_protocol       = "tcp"
  description       = "HTTP origin traffic from CloudFront only"
}

resource "aws_security_group" "api_gateway_vpc_link" {
  count = local.uses_api_gateway_endpoint ? 1 : 0

  name        = "${local.name_prefix}-api-gateway-link"
  description = "API Gateway VPC link to the InvoiceFlow load balancer"
  vpc_id      = aws_vpc.main.id

  tags = { Name = "${local.name_prefix}-api-gateway-link" }
}

resource "aws_vpc_security_group_ingress_rule" "alb_api_gateway_http" {
  count = local.uses_api_gateway_endpoint ? 1 : 0

  security_group_id            = aws_security_group.alb.id
  referenced_security_group_id = aws_security_group.api_gateway_vpc_link[0].id
  from_port                    = 80
  to_port                      = 80
  ip_protocol                  = "tcp"
  description                  = "HTTP origin traffic from the API Gateway VPC link only"
}

resource "aws_vpc_security_group_egress_rule" "api_gateway_to_alb" {
  count = local.uses_api_gateway_endpoint ? 1 : 0

  security_group_id            = aws_security_group.api_gateway_vpc_link[0].id
  referenced_security_group_id = aws_security_group.alb.id
  from_port                    = 80
  to_port                      = 80
  ip_protocol                  = "tcp"
  description                  = "Forward API Gateway requests to the load balancer"
}

resource "aws_security_group" "tasks" {
  name        = "${local.name_prefix}-tasks"
  description = "API, worker, migration, and provisioner tasks"
  vpc_id      = aws_vpc.main.id

  tags = { Name = "${local.name_prefix}-tasks" }
}

resource "aws_vpc_security_group_ingress_rule" "api_from_alb" {
  security_group_id            = aws_security_group.tasks.id
  referenced_security_group_id = aws_security_group.alb.id
  from_port                    = 8000
  to_port                      = 8000
  ip_protocol                  = "tcp"
  description                  = "API traffic from the load balancer"
}

resource "aws_vpc_security_group_egress_rule" "alb_to_api" {
  security_group_id            = aws_security_group.alb.id
  referenced_security_group_id = aws_security_group.tasks.id
  from_port                    = 8000
  to_port                      = 8000
  ip_protocol                  = "tcp"
  description                  = "Forward requests to API tasks"
}

resource "aws_vpc_security_group_egress_rule" "tasks_https" {
  security_group_id = aws_security_group.tasks.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
  description       = "AWS APIs, Cognito JWKS, and package endpoints"
}

resource "aws_vpc_security_group_egress_rule" "tasks_dns_udp" {
  security_group_id = aws_security_group.tasks.id
  cidr_ipv4         = var.vpc_cidr
  from_port         = 53
  to_port           = 53
  ip_protocol       = "udp"
  description       = "VPC DNS"
}

resource "aws_vpc_security_group_egress_rule" "tasks_dns_tcp" {
  security_group_id = aws_security_group.tasks.id
  cidr_ipv4         = var.vpc_cidr
  from_port         = 53
  to_port           = 53
  ip_protocol       = "tcp"
  description       = "VPC DNS fallback"
}

resource "aws_security_group" "database" {
  name        = "${local.name_prefix}-database"
  description = "PostgreSQL access from InvoiceFlow tasks only"
  vpc_id      = aws_vpc.main.id

  tags = { Name = "${local.name_prefix}-database" }
}

resource "aws_vpc_security_group_ingress_rule" "database_from_tasks" {
  security_group_id            = aws_security_group.database.id
  referenced_security_group_id = aws_security_group.tasks.id
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
  description                  = "PostgreSQL from API, worker, and migration tasks"
}

resource "aws_vpc_security_group_egress_rule" "tasks_to_database" {
  security_group_id            = aws_security_group.tasks.id
  referenced_security_group_id = aws_security_group.database.id
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
  description                  = "PostgreSQL"
}
