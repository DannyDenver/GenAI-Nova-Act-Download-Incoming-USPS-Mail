# S3 bucket for storing mail images
resource "aws_s3_bucket" "mail_images" {
  bucket        = "${local.name_prefix}-mail-images-${random_id.suffix.hex}"
  force_destroy = true
  tags          = local.common_tags
}

# S3 bucket versioning
resource "aws_s3_bucket_versioning" "mail_images" {
  bucket = aws_s3_bucket.mail_images.id
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 bucket encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "mail_images" {
  bucket = aws_s3_bucket.mail_images.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# S3 bucket lifecycle configuration
resource "aws_s3_bucket_lifecycle_configuration" "mail_images" {
  bucket = aws_s3_bucket.mail_images.id

  rule {
    id     = "mail_images_lifecycle"
    status = "Enabled"

    expiration {
      days = 10
    }
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "mail_images" {
  bucket = aws_s3_bucket.mail_images.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}