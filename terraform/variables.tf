variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "schedule_expression" {
  description = "EventBridge schedule expression for Lambda execution"
  type        = string
  default     = "cron(0 7 * * ? *)"  # 7 AM UTC daily
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 900  # 15 minutes
}

variable "lambda_memory_size" {
  description = "Lambda function memory size in MB"
  type        = number
  default     = 3008  # Maximum for browser automation
}

variable "usps_username" {
  description = "USPS account username"
  type        = string
  sensitive   = true
}

variable "usps_password" {
  description = "USPS account password"
  type        = string
  sensitive   = true
}

variable "use_container_image" {
  description = "Use container image instead of ZIP package"
  type        = bool
  default     = false
}

variable "container_image_uri" {
  description = "ECR container image URI (required when use_container_image is true)"
  type        = string
  default     = ""
}

variable "use_minimal_approach" {
  description = "Use minimal HTTP-based approach instead of browser automation"
  type        = bool
  default     = false
}

variable "nova_act_api_key" {
  description = "API Key for nova act"
  type = string
}

variable "upload_logs_to_s3" {
  description = "Whether to upload Nova Act logs to S3 bucket"
  type        = string
  default     = "true"
}

