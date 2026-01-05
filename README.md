# USPS Informed Delivery Lambda Automation

This project deploys the USPS Informed Delivery automation to AWS Lambda using Terraform, transforming the local Nova Act automation into a serverless, scheduled service.

## Architecture

- **AWS Lambda**: Runs the USPS automation script daily using Nova Act browser automation
- **S3 Bucket**: Stores downloaded mail images and Nova Act automation logs
- **EventBridge**: Schedules daily execution at 7 AM UTC
- **Secrets Manager**: Securely stores USPS credentials and Nova Act API key
- **CloudWatch**: Logging and monitoring
- **IAM**: Secure access controls
- **ECR**: Container registry for Lambda container images

## Prerequisites

1. **macOS/Linux** system
2. **AWS Account** with appropriate permissions
3. **USPS Account** with Informed Delivery enabled
4. **Docker** installed and running
5. **Nova Act API Key** from [Nova Act](https://novaact.ai)

### Quick Setup

Run the setup script to install all prerequisites:
```bash
./setup-prerequisites.sh
```

This will install:
- **Terraform** (>= 1.0)
- **AWS CLI** (v2)
- **Docker** (if not already installed)

### Manual Installation

If you prefer manual installation:

**macOS (using Homebrew):**
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install prerequisites
brew install terraform awscli docker
```

**Linux (Ubuntu/Debian):**
```bash
# Install Docker
sudo apt update
sudo apt install docker.io
sudo systemctl start docker
sudo systemctl enable docker

# Install Terraform
wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor | sudo tee /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform

# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

### AWS Configuration

After installing AWS CLI, configure your credentials:
```bash
aws configure
```

You'll need:
- AWS Access Key ID
- AWS Secret Access Key
- Default region (e.g., us-east-1)
- Output format (json)

## Features

### Automated Mail Retrieval
- **Daily scheduled execution** via EventBridge (7 AM UTC by default)
- **Browser automation** using Nova Act for reliable USPS website interaction
- **Intelligent image detection** and download from Informed Delivery
- **Fallback screenshot** capture if no mail images are found

### Comprehensive Logging
- **Nova Act automation logs** automatically uploaded to S3
- **Complete audit trail** of all browser automation steps
- **HTML traces** showing each action taken during automation
- **Screenshot captures** of automation steps for debugging
- **Configurable log upload** via `UPLOAD_LOGS_TO_S3` environment variable

### Secure Credential Management
- **AWS Secrets Manager** integration for USPS credentials
- **Nova Act API key** stored securely in environment variables
- **No hardcoded credentials** in code or containers

### Cost-Optimized Storage
- **S3 lifecycle policies** automatically delete files after 10 days
- **Organized folder structure** by date for easy navigation
- **Separate logs folder** for automation traces and debugging

## Quick Start

### 1. Configure Credentials
```bash
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
```

Edit `terraform/terraform.tfvars` with your values:
```hcl
aws_region = "us-east-1"
environment = "prod"
usps_username = "your-usps-username@example.com"
usps_password = "your-secure-password"
nova_act_api_key = "your-nova-act-api-key"

# Optional: Control log uploads (default: true)
upload_logs_to_s3 = "true"
```

### 2. Deploy with Docker Container

Deploy using the container image method:
```bash
./deploy-container.sh
```

This will:
- Build a Docker container with all dependencies including Nova Act and Playwright
- Push the container to Amazon ECR
- Deploy the Lambda function using the container image
- Set up all AWS infrastructure with Terraform
- Configure automatic log uploads to S3 for debugging and audit trails

### 3. Monitor

After deployment, you can:
- Check CloudWatch logs: `/aws/lambda/usps-automation-function-*`
- View S3 bucket contents for downloaded images and automation logs
- Monitor Lambda execution in the AWS Console
- Review Nova Act automation traces in S3 for debugging

## Deployment

### Container Image Deployment

This project uses Docker containers for deployment, providing:
- **No size limitations** for Nova Act and browser dependencies
- **Consistent environment** across development and production
- **Better dependency management** for complex browser automation
- **Playwright browser binaries** included in the container

Deploy the complete solution:
```bash
./deploy-container.sh
```

The deployment script will:
1. **Build Docker container** with Nova Act, Playwright, and all dependencies
2. **Create ECR repository** and push the container image
3. **Deploy infrastructure** using Terraform
4. **Configure Lambda function** to use the container image
5. **Set up log uploads** to S3 for complete automation tracing

## Manual Deployment

If you prefer manual steps:

### 1. Build and Push Container
```bash
# Build the container
docker build -t usps-automation lambda/

# Create ECR repository and push (handled by deploy-container.sh)
```

### 2. Deploy Infrastructure
```bash
cd terraform
terraform init
terraform plan
terraform apply
```

## Configuration

### Environment Variables (Lambda)
- `S3_BUCKET_NAME`: S3 bucket for storing images and logs
- `SECRET_NAME`: Secrets Manager secret name containing USPS credentials
- `NOVA_ACT_API_KEY`: Nova Act API key for browser automation
- `UPLOAD_LOGS_TO_S3`: Whether to upload Nova Act logs to S3 (default: "true")
- `AWS_REGION`: AWS region (automatically provided by Lambda)

### Terraform Variables
- `aws_region`: AWS region (default: us-east-1)
- `environment`: Environment name (default: prod)
- `schedule_expression`: Cron expression for scheduling (default: 7 AM UTC daily)
- `lambda_timeout`: Function timeout in seconds (default: 900)
- `lambda_memory_size`: Memory allocation in MB (default: 3008)
- `usps_username`: USPS account username
- `usps_password`: USPS account password
- `nova_act_api_key`: Nova Act API key for browser automation
- `upload_logs_to_s3`: Whether to upload Nova Act logs to S3 (default: true)

### Scheduling

The default schedule runs at 7 AM UTC daily. To change:
```hcl
schedule_expression = "cron(0 12 * * ? *)"  # 12 PM UTC daily
```

### Log Upload Configuration

Nova Act automation logs are automatically uploaded to S3 by default, providing:
- **Complete automation traces** in HTML format showing each step
- **Screenshot captures** of browser interactions
- **JSON logs** with detailed execution data
- **Error debugging** information for failed runs

To disable log uploads (reduce S3 costs):
```hcl
upload_logs_to_s3 = "false"
```

**Note**: Disabling log uploads will make debugging automation issues more difficult.

## S3 Storage Structure

Images are stored with the following structure:
```
s3://usps-mail-images-{suffix}/
├── 2024-12-28/
│   ├── mail_image_1_20241228_070123.png
│   ├── mail_image_2_20241228_070124.png
│   └── logs/
│       ├── session_log.json
│       ├── action_trace.html
│       └── screenshots/
└── 2024-12-29/
    └── ...
```

### Lifecycle Policies
- **10 days**: Objects are automatically deleted to manage costs

## Monitoring

### CloudWatch Logs
- Log Group: `/aws/lambda/usps-automation-function-*`
- Retention: 14 days
- Contains execution details, errors, and success metrics

### Lambda Metrics
The function returns structured data:
```json
{
  "success": true,
  "images_downloaded": 5,
  "s3_uploads": 5,
  "uploaded_files": ["s3://bucket/2024-12-28/mail_image_1.png"],
  "uploaded_logs": ["s3://bucket/2024-12-28/logs/session_log.json"],
  "logs_uploaded": 3,
  "execution_time": 245.67,
  "date": "2024-12-28"
}
```

## Troubleshooting

### Common Issues

1. **Login Failures**
   - Verify USPS credentials in Secrets Manager
   - Check if USPS account has Informed Delivery enabled
   - Review CloudWatch logs for specific error messages

2. **Timeout Issues**
   - Lambda has a 15-minute maximum timeout
   - Browser automation can be slow; consider optimizing selectors

3. **Memory Issues**
   - Function uses maximum Lambda memory (3008MB)
   - Browser automation is memory-intensive

4. **S3 Upload Failures**
   - Check IAM permissions for S3 bucket access
   - Verify bucket exists and is accessible

5. **Container Build Issues**
   - Ensure Docker is running
   - Check Nova Act API key is valid
   - Verify ECR permissions for pushing images

6. **Nova Act Issues**
   - Check Nova Act API key in Secrets Manager
   - Review Nova Act logs in S3 for detailed automation traces
   - Verify browser automation steps in uploaded HTML traces

### Debugging

Enable detailed logging by checking CloudWatch logs:
```bash
aws logs tail /aws/lambda/usps-automation-function-{suffix} --follow
```

## Security

- **Credentials**: Stored securely in AWS Secrets Manager
- **S3 Bucket**: Private with encryption enabled
- **IAM**: Least-privilege access policies
- **VPC**: Not required for this use case

## Cost Optimization

- **Lambda**: Pay per execution (daily = ~30 executions/month)
- **S3**: Lifecycle policies automatically delete files after 10 days
- **CloudWatch**: 14-day log retention reduces storage costs
- **Secrets Manager**: Minimal cost for credential storage
- **ECR**: Container image storage (minimal cost for single image)

### Managing Log Upload Costs

Nova Act logs provide valuable debugging information but consume S3 storage:
- **Enable logs** (default): Complete automation traces for debugging
- **Disable logs**: Set `upload_logs_to_s3 = "false"` to reduce S3 costs
- **Automatic cleanup**: 10-day lifecycle policy applies to all S3 objects

## Cleanup

To destroy all resources:
```bash
cd terraform
terraform destroy
```

**Note**: S3 bucket contents are not automatically deleted. Empty the bucket manually if needed.

## Development

### Local Testing

The Lambda function is designed for container deployment. For local development:

```bash
# Build container locally
docker build -t usps-automation lambda/

# Run container locally (requires environment variables)
docker run -e USPS_USERNAME="your-username" \
           -e USPS_PASSWORD="your-password" \
           -e NOVA_ACT_API_KEY="your-api-key" \
           usps-automation
```

### Container Testing

Test the container image before deployment:
```bash
# Build and test locally
docker build -t usps-automation lambda/
docker run --rm usps-automation
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes
4. Test thoroughly
5. Submit a pull request

## License

This project is for personal use only. Ensure compliance with USPS terms of service.