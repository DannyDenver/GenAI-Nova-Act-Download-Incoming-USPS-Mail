# USPS Informed Delivery Lambda Automation

This project deploys the USPS Informed Delivery automation to AWS Lambda using Terraform, transforming the local Nova Act automation into a serverless, scheduled service.

## Architecture

- **AWS Lambda**: Runs the USPS automation script daily
- **S3 Bucket**: Stores downloaded mail images with lifecycle policies
- **EventBridge**: Schedules daily execution at 7 AM UTC
- **Secrets Manager**: Securely stores USPS credentials
- **CloudWatch**: Logging and monitoring
- **IAM**: Secure access controls

## Prerequisites

1. **macOS/Linux** system
2. **AWS Account** with appropriate permissions
3. **USPS Account** with Informed Delivery enabled

### Quick Setup

Run the setup script to install all prerequisites:
```bash
./setup-prerequisites.sh
```

This will install:
- **Terraform** (>= 1.0)
- **AWS CLI** (v2)
- **Python 3** and pip3

### Manual Installation

If you prefer manual installation:

**macOS (using Homebrew):**
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install prerequisites
brew install terraform awscli python
```

**Linux (Ubuntu/Debian):**
```bash
# Install Python
sudo apt update
sudo apt install python3 python3-pip

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

## Quick Start

### 1. Configure Credentials

Copy the example configuration:
```bash
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
```

Edit `terraform/terraform.tfvars` with your values:
```hcl
aws_region = "us-east-1"
environment = "prod"
usps_username = "your-usps-username@example.com"
usps_password = "your-secure-password"
```

### 2. Choose Deployment Method

Run the deployment choice script:
```bash
./deploy-choice.sh
```

**Option 1: ZIP Package with Lambda Layer (Recommended)**
- Faster deployment and cold starts
- Uses Lambda layers for heavy dependencies
- Suitable for most use cases

**Option 2: Container Image**
- No size limitations (Nova Act can be large)
- Requires Docker
- Better for complex dependencies

### 3. Monitor

After deployment, you can:
- Check CloudWatch logs: `/aws/lambda/usps-automation-function-*`
- View S3 bucket contents for downloaded images
- Monitor Lambda execution in the AWS Console

## Deployment Methods

### Method 1: ZIP Package with Lambda Layer

```bash
./deploy.sh
```

This method:
- Creates a Lambda layer with Nova Act dependencies
- Packages only your function code in the ZIP
- Faster deployment and execution
- Recommended for most users

### Method 2: Container Image

```bash
./deploy-container.sh
```

This method:
- Builds a Docker container with all dependencies
- Pushes to Amazon ECR
- No size limitations
- Requires Docker to be installed

### Method 3: Manual Choice

```bash
./deploy-choice.sh
```

Interactive script that lets you choose between the two methods.

## Manual Deployment

If you prefer manual steps:

### 1. Create Lambda Package
```bash
cd lambda
pip install -r requirements.txt -t package/
cp lambda_function.py package/
cd package && zip -r ../usps_automation.zip . && cd ..
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
- `S3_BUCKET_NAME`: S3 bucket for storing images
- `SECRET_NAME`: Secrets Manager secret name
- `AWS_REGION`: AWS region

### Terraform Variables
- `aws_region`: AWS region (default: us-east-1)
- `environment`: Environment name (default: prod)
- `schedule_expression`: Cron expression for scheduling (default: 7 AM UTC daily)
- `lambda_timeout`: Function timeout in seconds (default: 900)
- `lambda_memory_size`: Memory allocation in MB (default: 3008)
- `usps_username`: USPS account username
- `usps_password`: USPS account password

### Scheduling

The default schedule runs at 7 AM UTC daily. To change:
```hcl
schedule_expression = "cron(0 12 * * ? *)"  # 12 PM UTC daily
```

## S3 Storage Structure

Images are stored with the following structure:
```
s3://usps-mail-images-{suffix}/
├── 2024-12-28/
│   ├── mail_image_1_20241228_070123.png
│   ├── mail_image_2_20241228_070124.png
│   └── ...
├── 2024-12-29/
│   └── ...
```

### Lifecycle Policies
- **30 days**: Transition to Standard-IA
- **90 days**: Transition to Glacier
- **365 days**: Transition to Deep Archive

## Monitoring

### CloudWatch Logs
- Log Group: `/aws/lambda/usps-automation-function-*`
- Retention: 30 days
- Contains execution details, errors, and success metrics

### Lambda Metrics
The function returns structured data:
```json
{
  "success": true,
  "images_downloaded": 5,
  "s3_uploads": 5,
  "execution_time": 245.67,
  "date": "2024-12-28",
  "uploaded_files": ["s3://bucket/2024-12-28/mail_image_1.png"]
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
- **S3**: Lifecycle policies reduce storage costs
- **CloudWatch**: 30-day log retention
- **Secrets Manager**: Minimal cost for credential storage

## Cleanup

To destroy all resources:
```bash
cd terraform
terraform destroy
```

**Note**: S3 bucket contents are not automatically deleted. Empty the bucket manually if needed.

## Development

### Local Testing

Test the original script locally:
```bash
cd NovaAct-USPS-Incoming-Mail
export USPS_USERNAME="your-username"
export USPS_PASSWORD="your-password"
python usps_conservative.py --debug
```

### Lambda Testing

Test the Lambda function locally using AWS SAM or similar tools.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes
4. Test thoroughly
5. Submit a pull request

## License

This project is for personal use only. Ensure compliance with USPS terms of service.