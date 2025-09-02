#!/bin/bash

# eCommerce Order Processing System - Deployment Script

set -e

echo "🚀 Starting deployment of eCommerce Order Processing System"
echo "============================================================"

# Check if AWS CLI is installed and configured
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install and configure AWS CLI first."
    exit 1
fi

# Check if CDK is installed
if ! command -v cdk &> /dev/null; then
    echo "❌ AWS CDK not found. Installing..."
    npm install -g aws-cdk
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python 3.8 or later."
    exit 1
fi

echo "✅ Prerequisites check passed"

# Create and activate virtual environment
echo "📦 Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Set CDK app path
export CDK_APP="./venv/bin/python infrastructure/cdk-app.py"

# Bootstrap CDK (if needed)
echo "🏗️  Bootstrapping CDK..."
cdk bootstrap

# Synthesize CloudFormation template
echo "🔧 Synthesizing CloudFormation template..."
cdk synth

# Deploy the stack
echo "🚀 Deploying the stack..."
cdk deploy --require-approval never

# Get the outputs
echo "📋 Deployment completed! Getting outputs..."
API_ENDPOINT=$(aws cloudformation describe-stacks --stack-name ECommerceOrderProcessingStack --query 'Stacks[0].Outputs[?OutputKey==`APIEndpoint`].OutputValue' --output text)
echo "🌐 API Endpoint: $API_ENDPOINT"

# Get API Key
API_KEY_ID=$(aws apigateway get-api-keys --query 'items[?name==`ECommerceAPIKey`].id' --output text)
API_KEY=$(aws apigateway get-api-key --api-key $API_KEY_ID --include-value --query 'value' --output text)

echo "🔑 API Key: $API_KEY"

# Update demo script
echo "🛠️  Updating demo script with deployment values..."
sed -i.bak "s|https://your-api-gateway-url.execute-api.region.amazonaws.com/prod|$API_ENDPOINT|g" demo/test-api.py
sed -i.bak "s|your-api-key-here|$API_KEY|g" demo/test-api.py

echo "🎉 Deployment completed successfully!"
echo ""
echo "📝 Next Steps:"
echo "1. Test the API using: python demo/test-api.py"
echo "2. Access the API endpoint: $API_ENDPOINT"
echo "3. Use API Key in requests: $API_KEY"
echo ""
echo "🔗 Useful Commands:"
echo "- View logs: aws logs describe-log-groups --log-group-name-prefix /aws/lambda"
echo "- Monitor metrics: aws cloudwatch list-metrics --namespace ECommerce/OrderProcessing"
echo "- Clean up: cdk destroy"