# Lambda function
resource "aws_lambda_function" "usps_automation" {
  image_uri        = var.container_image_uri
  package_type     = "Image"
  
  function_name    = "${local.name_prefix}-function-${random_id.suffix.hex}"
  role            = aws_iam_role.lambda_role.arn
  timeout         = var.lambda_timeout
  memory_size     = var.lambda_memory_size
  tags            = local.common_tags

  environment {
    variables = {
      S3_BUCKET_NAME = aws_s3_bucket.mail_images.bucket
      SECRET_NAME    = aws_secretsmanager_secret.usps_credentials.name
      NOVA_ACT_API_KEY = var.nova_act_api_key
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic,
    aws_iam_role_policy.lambda_custom,
    aws_cloudwatch_log_group.lambda_logs
  ]
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${local.name_prefix}-function-${random_id.suffix.hex}"
  retention_in_days = 14
  tags              = local.common_tags
}

# EventBridge rule for scheduling
resource "aws_cloudwatch_event_rule" "schedule" {
  name                = "${local.name_prefix}-schedule-${random_id.suffix.hex}"
  description         = "Schedule for USPS automation Lambda"
  schedule_expression = var.schedule_expression
  tags                = local.common_tags
}

# EventBridge target
resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.schedule.name
  target_id = "USPSAutomationTarget"
  arn       = aws_lambda_function.usps_automation.arn
}

# Permission for EventBridge to invoke Lambda
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.usps_automation.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.schedule.arn
}