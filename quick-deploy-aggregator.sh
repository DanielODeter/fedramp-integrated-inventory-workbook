#!/bin/bash
# Quick Deploy Script for FedRAMP Inventory Workbook - Config Aggregator Version
# Usage: ./quick-deploy-aggregator.sh <management-account-id> [aws-profile] [region] [aggregator-name]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
MGMT_ACCOUNT_ID=$1
AWS_PROFILE=${2:-default}
AWS_REGION=${3:-us-east-1}
AGGREGATOR_NAME=${4:-OrganizationConfigAggregator}

# Validate arguments
if [ -z "$MGMT_ACCOUNT_ID" ]; then
    echo -e "${RED}Error: Missing required argument${NC}"
    echo "Usage: ./quick-deploy-aggregator.sh <management-account-id> [aws-profile] [region] [aggregator-name]"
    echo ""
    echo "Example:"
    echo "  ./quick-deploy-aggregator.sh 123456789012"
    echo "  ./quick-deploy-aggregator.sh 123456789012 my-profile us-west-2 MyAggregator"
    exit 1
fi

# Validate account ID is 12 digits
if ! [[ "$MGMT_ACCOUNT_ID" =~ ^[0-9]{12}$ ]]; then
    echo -e "${RED}Error: Management account ID must be 12 digits${NC}"
    exit 1
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}FedRAMP Inventory - Aggregator Deploy${NC}"
echo -e "${GREEN}========================================${NC}"
echo "Management Account: $MGMT_ACCOUNT_ID"
echo "AWS Profile: $AWS_PROFILE"
echo "Region: $AWS_REGION"
echo "Config Aggregator: $AGGREGATOR_NAME"
echo -e "${GREEN}========================================${NC}"
echo ""

# Step 1: Verify Config Aggregator exists
echo -e "${YELLOW}[1/4] Verifying Config Aggregator exists...${NC}"
if ! aws configservice describe-configuration-aggregators \
    --configuration-aggregator-names ${AGGREGATOR_NAME} \
    --profile ${AWS_PROFILE} \
    --region ${AWS_REGION} \
    --output json > /dev/null 2>&1; then
    echo -e "${RED}Error: Config Aggregator '${AGGREGATOR_NAME}' not found${NC}"
    echo ""
    echo "Please create a Config Aggregator first:"
    echo "  1. Go to AWS Config console"
    echo "  2. Navigate to 'Aggregators' in the left menu"
    echo "  3. Click 'Add aggregator'"
    echo "  4. Choose 'Add an aggregator for my organization'"
    echo "  5. Name it '${AGGREGATOR_NAME}' (or use a different name and pass it as 4th argument)"
    echo ""
    echo "Or create via CLI:"
    echo "  aws configservice put-configuration-aggregator \\"
    echo "    --configuration-aggregator-name ${AGGREGATOR_NAME} \\"
    echo "    --organization-aggregation-source '{\"RoleArn\":\"arn:aws:iam::${MGMT_ACCOUNT_ID}:role/aws-service-role/organizations.amazonaws.com/AWSServiceRoleForOrganizations\",\"AllAwsRegions\":true}' \\"
    echo "    --profile ${AWS_PROFILE} --region ${AWS_REGION}"
    exit 1
fi
echo -e "${GREEN}✓ Config Aggregator '${AGGREGATOR_NAME}' found${NC}"
echo ""

# Step 2: Package Lambda code
echo -e "${YELLOW}[2/4] Packaging Lambda code...${NC}"
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

# Step 3: Create S3 bucket and upload Lambda code
echo -e "${YELLOW}[3/4] Creating S3 bucket and uploading Lambda code...${NC}"
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

# Step 4: Deploy CloudFormation stack
echo -e "${YELLOW}[4/4] Deploying CloudFormation stack...${NC}"
if ! aws cloudformation deploy \
    --template-file templates/InventoryCollector-Aggregator.yml \
    --stack-name fedramp-inventory-aggregator \
    --parameter-overrides \
        MasterAccountName=management \
        ConfigAggregatorName=${AGGREGATOR_NAME} \
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
echo "Stack Name: fedramp-inventory-aggregator"
echo "Region: ${AWS_REGION}"
echo "Config Aggregator: ${AGGREGATOR_NAME}"
echo ""
echo "To view outputs:"
echo "  aws cloudformation describe-stacks --stack-name fedramp-inventory-aggregator --profile ${AWS_PROFILE} --region ${AWS_REGION} --query 'Stacks[0].Outputs'"
echo ""
echo "To test the Lambda function:"
echo "  aws lambda invoke --function-name InventoryCollector-Aggregator-fedramp-inventory-aggregator --profile ${AWS_PROFILE} --region ${AWS_REGION} output.json"
echo ""
echo "Reports will be stored in: s3://integrated-inventory-reports-${MGMT_ACCOUNT_ID}/inventory-reports/"
echo ""
echo -e "${GREEN}Note: This deployment uses Config Aggregator - no member account setup required!${NC}"
echo ""
