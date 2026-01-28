#!/bin/bash
# Quick Deploy Script for FedRAMP Inventory Workbook
# Usage: ./quick-deploy.sh <management-account-id> <member-account-id> [aws-profile] [region]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
MGMT_ACCOUNT_ID=$1
MEMBER_ACCOUNT_ID=$2
AWS_PROFILE=${3:-default}
AWS_REGION=${4:-us-east-1}

# Validate arguments
if [ -z "$MGMT_ACCOUNT_ID" ] || [ -z "$MEMBER_ACCOUNT_ID" ]; then
    echo -e "${RED}Error: Missing required arguments${NC}"
    echo "Usage: ./quick-deploy.sh <management-account-id> <member-account-id> [aws-profile] [region]"
    echo ""
    echo "Example:"
    echo "  ./quick-deploy.sh 123456789012 987654321098"
    echo "  ./quick-deploy.sh 123456789012 987654321098 my-profile us-west-2"
    exit 1
fi

# Validate account IDs are 12 digits
if ! [[ "$MGMT_ACCOUNT_ID" =~ ^[0-9]{12}$ ]]; then
    echo -e "${RED}Error: Management account ID must be 12 digits${NC}"
    exit 1
fi

if ! [[ "$MEMBER_ACCOUNT_ID" =~ ^[0-9]{12}$ ]]; then
    echo -e "${RED}Error: Member account ID must be 12 digits${NC}"
    exit 1
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}FedRAMP Inventory Quick Deploy${NC}"
echo -e "${GREEN}========================================${NC}"
echo "Management Account: $MGMT_ACCOUNT_ID"
echo "Member Account: $MEMBER_ACCOUNT_ID"
echo "AWS Profile: $AWS_PROFILE"
echo "Region: $AWS_REGION"
echo -e "${GREEN}========================================${NC}"
echo ""

# Step 1: Package Lambda code
echo -e "${YELLOW}[1/4] Packaging Lambda code...${NC}"
if [ ! -d "package" ]; then
    mkdir package
fi

pip install -r requirements.txt -t package/ --quiet
cp -r src/inventory package/
cd package
zip -r -q ../fedramp-inventory-lambda.zip .
cd ..
echo -e "${GREEN}✓ Lambda code packaged${NC}"
echo ""

# Step 2: Create S3 bucket and upload Lambda code
echo -e "${YELLOW}[2/4] Creating S3 bucket and uploading Lambda code...${NC}"
LAMBDA_BUCKET="fedramp-lambda-code-${MGMT_ACCOUNT_ID}"

# Create bucket (ignore error if exists)
aws s3 mb s3://${LAMBDA_BUCKET} --profile ${AWS_PROFILE} --region ${AWS_REGION} 2>/dev/null || true

# Upload Lambda code
if ! aws s3 cp fedramp-inventory-lambda.zip s3://${LAMBDA_BUCKET}/ --profile ${AWS_PROFILE} --region ${AWS_REGION}; then
    echo -e "${RED}Error: Failed to upload Lambda code to S3${NC}"
    echo "Please check:"
    echo "  - AWS credentials for profile '${AWS_PROFILE}'"
    echo "  - S3 bucket permissions"
    echo "  - Network connectivity"
    exit 1
fi
echo -e "${GREEN}✓ Lambda code uploaded to s3://${LAMBDA_BUCKET}/${NC}"
echo ""

# Step 3: Create cross-account role in member account
echo -e "${YELLOW}[3/4] Creating cross-account IAM role in member account...${NC}"
echo -e "${YELLOW}Note: This requires credentials for the member account${NC}"
read -p "Enter AWS profile for member account (or press Enter to skip): " MEMBER_PROFILE

if [ -n "$MEMBER_PROFILE" ]; then
    # Create role
    aws iam create-role \
        --role-name InventoryCollector-for-Lambda \
        --assume-role-policy-document "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":{\"AWS\":\"arn:aws:iam::${MGMT_ACCOUNT_ID}:root\"},\"Action\":\"sts:AssumeRole\"}]}" \
        --profile ${MEMBER_PROFILE} \
        --region ${AWS_REGION} 2>/dev/null || echo "Role may already exist"
    
    # Attach policy
    aws iam attach-role-policy \
        --role-name InventoryCollector-for-Lambda \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSConfigRole \
        --profile ${MEMBER_PROFILE} \
        --region ${AWS_REGION} 2>/dev/null || true
    
    echo -e "${GREEN}✓ Cross-account role created in member account${NC}"
else
    echo -e "${YELLOW}⚠ Skipped cross-account role creation. You must create it manually.${NC}"
fi
echo ""

# Step 4: Deploy CloudFormation stack
echo -e "${YELLOW}[4/4] Deploying CloudFormation stack...${NC}"
if ! aws cloudformation deploy \
    --template-file templates/InventoryCollector.yml \
    --stack-name fedramp-inventory \
    --parameter-overrides \
        MasterAccountName=management \
        DomainAccountId=${MEMBER_ACCOUNT_ID} \
        DomainAccountName=member \
        LambdaPayloadLocation=${LAMBDA_BUCKET} \
        LambdaPayload=fedramp-inventory-lambda.zip \
    --capabilities CAPABILITY_NAMED_IAM \
    --profile ${AWS_PROFILE} \
    --region ${AWS_REGION}; then
    echo -e "${RED}Error: CloudFormation deployment failed${NC}"
    echo "Check the CloudFormation console for details:"
    echo "  https://console.aws.amazon.com/cloudformation/home?region=${AWS_REGION}"
    exit 1
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Stack Name: fedramp-inventory"
echo "Region: ${AWS_REGION}"
echo ""
echo "To view outputs:"
echo "  aws cloudformation describe-stacks --stack-name fedramp-inventory --profile ${AWS_PROFILE} --region ${AWS_REGION} --query 'Stacks[0].Outputs'"
echo ""
echo "To test the Lambda function:"
echo "  aws lambda invoke --function-name InventoryCollector --profile ${AWS_PROFILE} --region ${AWS_REGION} output.json"
echo ""
echo "Reports will be stored in: s3://integrated-inventory-reports-${MGMT_ACCOUNT_ID}/inventory-reports/"
echo ""
