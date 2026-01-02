#!/bin/bash

# Setup script for USPS Lambda deployment prerequisites

set -e

echo "🛠️  Setting up prerequisites for USPS Lambda deployment..."

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macOS"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="Linux"
else
    echo "❌ Unsupported OS: $OSTYPE"
    exit 1
fi

echo "📱 Detected OS: $OS"

# Check if Homebrew is available on macOS
if [[ "$OS" == "macOS" ]]; then
    if ! command -v brew &> /dev/null; then
        echo "❌ Homebrew not found. Installing Homebrew first..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    else
        echo "✅ Homebrew found"
    fi
fi

# Install Terraform
install_terraform() {
    echo "📦 Installing Terraform..."
    
    if [[ "$OS" == "macOS" ]]; then
        brew tap hashicorp/tap
        brew install hashicorp/tap/terraform
    else
        # Linux installation
        wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor | sudo tee /usr/share/keyrings/hashicorp-archive-keyring.gpg
        echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
        sudo apt update && sudo apt install terraform
    fi
    
    echo "✅ Terraform installed: $(terraform version | head -n1)"
}

# Install AWS CLI
install_aws_cli() {
    echo "📦 Installing AWS CLI..."
    
    if [[ "$OS" == "macOS" ]]; then
        brew install awscli
    else
        # Linux installation
        curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
        unzip awscliv2.zip
        sudo ./aws/install
        rm -rf aws awscliv2.zip
    fi
    
    echo "✅ AWS CLI installed: $(aws --version)"
}

# Install Python and pip if needed
install_python() {
    if ! command -v python3 &> /dev/null || ! command -v pip3 &> /dev/null; then
        echo "📦 Installing Python 3..."
        
        if [[ "$OS" == "macOS" ]]; then
            brew install python
        else
            sudo apt update
            sudo apt install python3 python3-pip
        fi
        
        echo "✅ Python installed: $(python3 --version)"
    else
        echo "✅ Python already installed: $(python3 --version)"
    fi
}

# Main installation
main() {
    local install_terraform_flag=false
    local install_aws_flag=false
    local install_python_flag=false
    
    # Check what's missing
    if ! command -v terraform &> /dev/null; then
        install_terraform_flag=true
    fi
    
    if ! command -v aws &> /dev/null; then
        install_aws_flag=true
    fi
    
    if ! command -v python3 &> /dev/null || ! command -v pip3 &> /dev/null; then
        install_python_flag=true
    fi
    
    # Show what will be installed
    echo ""
    echo "📋 Installation plan:"
    [ "$install_terraform_flag" = true ] && echo "  - Terraform"
    [ "$install_aws_flag" = true ] && echo "  - AWS CLI"
    [ "$install_python_flag" = true ] && echo "  - Python 3"
    
    if [ "$install_terraform_flag" = false ] && [ "$install_aws_flag" = false ] && [ "$install_python_flag" = false ]; then
        echo "  - All prerequisites already installed! ✅"
        exit 0
    fi
    
    echo ""
    read -p "Continue with installation? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Installation cancelled"
        exit 1
    fi
    
    # Install missing tools
    [ "$install_python_flag" = true ] && install_python
    [ "$install_terraform_flag" = true ] && install_terraform
    [ "$install_aws_flag" = true ] && install_aws_cli
    
    echo ""
    echo "🎉 All prerequisites installed successfully!"
    echo ""
    echo "📝 Next steps:"
    echo "1. Configure AWS CLI: aws configure"
    echo "2. Run deployment: ./deploy.sh"
}

main "$@"