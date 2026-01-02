# Secrets Manager secret for USPS credentials
resource "aws_secretsmanager_secret" "usps_credentials" {
  name        = "${local.name_prefix}-credentials-${random_id.suffix.hex}"
  description = "USPS account credentials for automation"
  tags        = local.common_tags
}

# Store the credentials
resource "aws_secretsmanager_secret_version" "usps_credentials" {
  secret_id = aws_secretsmanager_secret.usps_credentials.id
  secret_string = jsonencode({
    username = var.usps_username
    password = var.usps_password
  })
}