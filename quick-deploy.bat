@echo off
REM Quick Deploy Script for FedRAMP Inventory Workbook
REM Usage: quick-deploy.bat <management-account-id> <member-account-id> [aws-profile] [region]

setlocal enabledelayedexpansion

REM Parse arguments
set MGMT_ACCOUNT_ID=%1
set MEMBER_ACCOUNT_ID=%2
set AWS_PROFILE=%3
set AWS_REGION=%4

if "%AWS_PROFILE%"=="" set AWS_PROFILE=default
if "%AWS_REGION%"=="" set AWS_REGION=us-east-1

REM Validate arguments
if "%MGMT_ACCOUNT_ID%"=="" (
    echo Error: Missing required arguments
    echo Usage: quick-deploy.bat ^<management-account-id^> ^<member-account-id^> [aws-profile] [region]
    echo.
    echo Example:
    echo   quick-deploy.bat 123456789012 987654321098
    echo   quick-deploy.bat 123456789012 987654321098 my-profile us-west-2
    exit /b 1
)

if "%MEMBER_ACCOUNT_ID%"=="" (
    echo Error: Missing member account ID
    exit /b 1
)

echo ========================================
echo FedRAMP Inventory Quick Deploy
echo ========================================
echo Management Account: %MGMT_ACCOUNT_ID%
echo Member Account: %MEMBER_ACCOUNT_ID%
echo AWS Profile: %AWS_PROFILE%
echo Region: %AWS_REGION%
echo ========================================
echo.

REM Step 1: Package Lambda code
echo [1/4] Packaging Lambda code...
if not exist "package" mkdir package
pip install -r requirements.txt -t package/ --quiet
xcopy /E /I /Y src\inventory package\inventory >nul
cd package
powershell Compress-Archive -Path * -DestinationPath ..\fedramp-inventory-lambda.zip -Force
cd ..
echo [OK] Lambda code packaged
echo.

REM Step 2: Create S3 bucket and upload Lambda code
echo [2/4] Creating S3 bucket and uploading Lambda code...
set LAMBDA_BUCKET=fedramp-lambda-code-%MGMT_ACCOUNT_ID%

REM Create bucket (ignore error if exists)
aws s3 mb s3://%LAMBDA_BUCKET% --profile %AWS_PROFILE% --region %AWS_REGION% 2>nul

REM Upload Lambda code
aws s3 cp fedramp-inventory-lambda.zip s3://%LAMBDA_BUCKET%/ --profile %AWS_PROFILE% --region %AWS_REGION%
echo [OK] Lambda code uploaded to s3://%LAMBDA_BUCKET%/
echo.

REM Step 3: Create cross-account role in member account
echo [3/4] Creating cross-account IAM role in member account...
echo Note: This requires credentials for the member account
set /p MEMBER_PROFILE="Enter AWS profile for member account (or press Enter to skip): "

if not "%MEMBER_PROFILE%"=="" (
    REM Create role
    aws iam create-role --role-name InventoryCollector-for-Lambda --assume-role-policy-document "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":{\"AWS\":\"arn:aws:iam::%MGMT_ACCOUNT_ID%:root\"},\"Action\":\"sts:AssumeRole\"}]}" --profile %MEMBER_PROFILE% --region %AWS_REGION% 2>nul
    
    REM Attach policy
    aws iam attach-role-policy --role-name InventoryCollector-for-Lambda --policy-arn arn:aws:iam::aws:policy/service-role/ConfigRole --profile %MEMBER_PROFILE% --region %AWS_REGION% 2>nul
    
    echo [OK] Cross-account role created in member account
) else (
    echo [WARNING] Skipped cross-account role creation. You must create it manually.
)
echo.

REM Step 4: Deploy CloudFormation stack
echo [4/4] Deploying CloudFormation stack...
aws cloudformation deploy --template-file templates/InventoryCollector.yml --stack-name fedramp-inventory --parameter-overrides MasterAccountName=management DomainAccountId=%MEMBER_ACCOUNT_ID% DomainAccountName=member LambdaPayloadLocation=%LAMBDA_BUCKET% LambdaPayload=fedramp-inventory-lambda.zip --capabilities CAPABILITY_NAMED_IAM --profile %AWS_PROFILE% --region %AWS_REGION%

echo.
echo ========================================
echo Deployment Complete!
echo ========================================
echo.
echo Stack Name: fedramp-inventory
echo Region: %AWS_REGION%
echo.
echo To view outputs:
echo   aws cloudformation describe-stacks --stack-name fedramp-inventory --profile %AWS_PROFILE% --region %AWS_REGION% --query "Stacks[0].Outputs"
echo.
echo To test the Lambda function:
echo   aws lambda invoke --function-name InventoryCollector --profile %AWS_PROFILE% --region %AWS_REGION% output.json
echo.
echo Reports will be stored in: s3://integrated-inventory-reports-%MGMT_ACCOUNT_ID%/inventory-reports/
echo.
