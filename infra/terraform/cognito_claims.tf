data "archive_file" "pre_token_generation" {
  type        = "zip"
  source_file = "${path.module}/functions/pre_token_generation.py"
  output_path = "${path.module}/.terraform/pre-token-generation.zip"
}

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "pre_token_generation" {
  name               = "${local.name_prefix}-pre-token"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy_attachment" "pre_token_generation_logs" {
  role       = aws_iam_role.pre_token_generation.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_cloudwatch_log_group" "pre_token_generation" {
  name              = "/aws/lambda/${local.name_prefix}-pre-token"
  retention_in_days = var.log_retention_days
}

resource "aws_lambda_function" "pre_token_generation" {
  function_name = "${local.name_prefix}-pre-token"
  description   = "Copies the admin-managed organization ID into Cognito access tokens."
  role          = aws_iam_role.pre_token_generation.arn
  runtime       = "python3.12"
  handler       = "pre_token_generation.handler"
  architectures = ["arm64"]
  timeout       = 5
  memory_size   = 128

  filename         = data.archive_file.pre_token_generation.output_path
  source_code_hash = data.archive_file.pre_token_generation.output_base64sha256

  depends_on = [
    aws_cloudwatch_log_group.pre_token_generation,
    aws_iam_role_policy_attachment.pre_token_generation_logs,
  ]
}

resource "aws_lambda_permission" "cognito_pre_token_generation" {
  statement_id  = "AllowCognitoPreTokenGeneration"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.pre_token_generation.function_name
  principal     = "cognito-idp.amazonaws.com"
  source_arn    = aws_cognito_user_pool.main.arn
}
