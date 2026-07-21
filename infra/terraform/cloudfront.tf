resource "random_id" "cloudfront_origin_header_name" {
  count       = local.uses_cloudfront_endpoint ? 1 : 0
  byte_length = 8
}

resource "random_password" "cloudfront_origin_header_value" {
  count   = local.uses_cloudfront_endpoint ? 1 : 0
  length  = 48
  special = false
}

resource "aws_cloudfront_distribution" "app" {
  count = local.uses_cloudfront_endpoint ? 1 : 0

  enabled         = true
  is_ipv6_enabled = true
  comment         = "InvoiceFlow ${var.environment} reviewer and API"
  price_class     = "PriceClass_100"
  http_version    = "http2and3"

  origin {
    domain_name = aws_lb.api.dns_name
    origin_id   = "invoiceflow-alb"

    custom_header {
      name  = "X-InvoiceFlow-${random_id.cloudfront_origin_header_name[0].hex}"
      value = random_password.cloudfront_origin_header_value[0].result
    }

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    target_origin_id       = "invoiceflow-alb"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    cache_policy_id          = local.cloudfront_caching_disabled_policy_id
    origin_request_policy_id = local.cloudfront_all_viewer_except_host_policy_id
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  lifecycle {
    precondition {
      condition     = local.is_showcase
      error_message = "The domain-free CloudFront endpoint is limited to the synthetic showcase profile. Production requires custom_domain mode with end-to-end HTTPS."
    }
  }

  depends_on = [aws_lb_listener_rule.cloudfront_origin]
}
