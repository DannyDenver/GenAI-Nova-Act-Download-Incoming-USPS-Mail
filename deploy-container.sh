#!/bin/bash

# Deploy USPS Lambda using Container Image (no size limits)

set -e

echo "🐳 Deploying USPS Lambda using container image..."

# Check prerequisites
check_prerequisites() {
    local missing_tools=()
    
    if ! command -v docker &> /dev/null; then
        missing_tools+=("docker")
    fi
    
    if ! command -v aws &> /dev/null; then
        missing_tools+=("aws")
    fi
    
    if ! command -v terraform &> /dev/null; then
        missing_tools+=("terraform")
    fi
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        echo "❌ Missing required tools: ${missing_tools[*]}"
        echo "Please install them first or use ./setup-prerequisites.sh"
        exit 1
    fi
}

check_prerequisites

# Check if terraform.tfvars exists
if [ ! -f "terraform/terraform.tfvars" ]; then
    echo "❌ Error: terraform/terraform.tfvars not found"
    echo "Please copy terraform/terraform.tfvars.example to terraform/terraform.tfvars and fill in your values"
    exit 1
fi

# Get AWS account ID and region
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region || echo "us-east-1")

echo "📋 AWS Account: $AWS_ACCOUNT_ID"
echo "📋 AWS Region: $AWS_REGION"

# ECR repository name
ECR_REPO_NAME="usps-automation"
IMAGE_TAG="latest"
IMAGE_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:$IMAGE_TAG"

echo "🏗️  Building and pushing container image..."

# Create ECR repository if it doesn't exist
aws ecr describe-repositories --repository-names $ECR_REPO_NAME --region $AWS_REGION 2>/dev/null || \
aws ecr create-repository --repository-name $ECR_REPO_NAME --region $AWS_REGION

# Get ECR login token
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build the Docker image with Lambda-compatible format
cd lambda
docker build --platform=linux/amd64 --provenance=false -t $ECR_REPO_NAME:$IMAGE_TAG .

# Tag for ECR
docker tag $ECR_REPO_NAME:$IMAGE_TAG $IMAGE_URI

# Push to ECR
docker push $IMAGE_URI

echo "✅ Container image pushed: $IMAGE_URI"

# Deploy with Terraform (container version)
echo "🏗️  Deploying infrastructure with Terraform..."
cd ../terraform

# Initialize Terraform
terraform init

# Plan deployment
echo "📋 Planning Terraform deployment..."
terraform plan -var="use_container_image=true" -var="container_image_uri=$IMAGE_URI"

# Ask for confirmation
read -p "Do you want to apply these changes? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Apply deployment
    echo "🚀 Applying Terraform configuration..."
    terraform apply -auto-approve -var="use_container_image=true" -var="container_image_uri=$IMAGE_URI"
    
    echo "✅ Container deployment completed successfully!"
    echo ""
    echo "📊 Deployment Summary:"
    terraform output
    
    echo ""
    echo "🎉 Your USPS automation is now deployed using container image!"
    echo "The Lambda function will run daily at 7 AM UTC."
    echo "Check CloudWatch logs for execution details."
else
    echo "❌ Deployment cancelled"
    exit 1
fi