# FedRAMP Integrated Inventory Workbook Generator - Enhanced

> **Community-Maintained Fork**: This is an enhanced version of the [original AWS sample](https://github.com/aws-samples/fedramp-integrated-inventory-workbook) (now archived). Includes security fixes, Python 3.11 upgrade, and 17 additional AWS services.

## Overview

This sample shows how you can create a Lambda function to retrieve inventory information to create the integrated inventory spreadsheet which can be used as a separate attachment to the FedRAMP System Security Plan (SSP). This is an enhanced fork of the [original AWS blog post project](https://aws.amazon.com/blogs/publicsector/automating-creation-fedramp-integrated-inventory-workbook/). The spreadsheet template can be found [here](https://www.fedramp.gov/new-integrated-inventory-template/).

This sample populates the inventory spreadsheet with a point in time view of AWS resources spanning multiple accounts. **15 resource types** are now supported across compute, storage, database, and network categories.

### Deployment Models

Two deployment architectures are available to fit different organizational structures:

**1. Cross-Account Model** - Traditional approach using IAM role assumption
- Lambda assumes roles into each member account sequentially
- Requires cross-account IAM role in every member account
- Best for: Standalone accounts, non-AWS Organizations environments, or when granular per-account control is needed
- Trade-offs: More complex setup, slower execution, higher API costs

**2. Config Aggregator Model** (Recommended) - Simplified approach using AWS Organizations
- Lambda queries a single Config Aggregator for all accounts
- No cross-account roles needed - automatic authorization via AWS Organizations
- Best for: AWS Organizations with 3+ accounts, production FedRAMP environments
- Benefits: Simpler deployment, faster execution, lower costs, automatic account discovery

See the [Deployment Options](#-deployment-options-how-to-install) section below for detailed comparison and setup instructions.

### What Gets Collected

The solution automatically discovers and inventories:
- **Compute**: EC2 instances, Lambda functions, EKS clusters
- **Storage**: S3 buckets, EFS file systems
- **Database**: RDS, DynamoDB, Redshift, ElastiCache, OpenSearch
- **Network**: Load balancers, API Gateway, CloudFront, NAT Gateways, Network Interfaces

For each resource, the inventory captures:
- Asset type and unique identifier (ARN)
- IP addresses and DNS names
- Public/private accessibility
- VPC/network configuration
- Tags (owner, IIR diagram label)
- Hardware/software details

**Note**: Software running on EC2 instances/containers must be tracked separately. This solution focuses on AWS infrastructure resources. The design is extensible to add custom data sources.

---

</details>

---

## What's New - January 2025

<details>
<summary>🔒 Critical Security Fixes</summary>

- Fixed CloudFormation YAML syntax errors in AssumeRolePolicyDocument (missing list indicator)
- Fixed ARN parsing boundary check preventing IndexError
- Fixed mutable default argument causing shared state between instances
- Added S3 bucket encryption (AES256) for FedRAMP compliance
- Fixed logger level configuration to properly handle string environment variables
- Added error handling to Lambda handler to return 500 status on failures
- Fixed configuration error handling - CROSS_ACCOUNT_ROLE_NAME validation now fails fast
- Added error handling for ACCOUNT_LIST JSON parsing with clear error messages

</details>

<details>
<summary>⚡ High Priority Fixes</summary>

- **Upgraded Lambda runtime from Python 3.8 to Python 3.11** (3.8 deprecated)
- Added environment variable validation for CROSS_ACCOUNT_ROLE_NAME
- Fixed dictionary access safety checks throughout codebase
- Fixed S3 public accessibility detection using publicAccessBlockConfiguration
- Fixed API Gateway public/private endpoint detection
- Fixed VPC configuration key capitalization (vpcOptions vs vPCOptions)
- Fixed ElastiCache engine type detection from configuration
- Fixed NetworkInterface public IP association detection
- Fixed NAT Gateway to create separate entries for private and public IPs
- Fixed file handle resource leak using context manager
- Removed duplicate owner field write in reports
- Fixed vpcId/vpcid key access with safe fallback to prevent KeyError
- Fixed RDS engine/engineVersion key access with safe defaults
- Added validation for REPORT_TARGET_BUCKET_PATH and REPORT_TARGET_BUCKET_NAME environment variables

</details>

<details>
<summary>🏗️ Infrastructure Improvements</summary>

- Added CloudWatch Log Groups with 90-day retention policy
- Added S3 lifecycle policies (7-year retention, 90-day noncurrent versions)
- Removed hardcoded IAM role names for stack reusability
- Fixed CloudFormation parameter validation (12-digit AWS account ID pattern)
- Fixed Output to return ARN instead of role name
- Removed obsolete DependsOn configurations
- Made temp file paths portable across operating systems

</details>

<details>
<summary>🚀 New AWS Service Support (8→25 resource types)</summary>

**Compute Resources:**
- AWS Lambda Functions
- Amazon EKS Clusters
- Amazon ECS Tasks & Services
- Amazon EC2 Instances

**Storage Resources:**
- Amazon S3 Buckets
- Amazon EFS File Systems

**Database Resources:**
- Amazon RDS (DB Instances & Clusters)
- Amazon DynamoDB Tables
- Amazon Redshift Clusters
- Amazon ElastiCache (Redis & Memcached)
- Amazon OpenSearch/Elasticsearch Domains

**Network Resources:**
- Elastic Load Balancers (Classic, ALB, NLB)
- Amazon API Gateway (REST, HTTP, WebSocket)
- Amazon CloudFront Distributions
- NAT Gateways
- Network Interfaces

</details>

<details>
<summary>📊 Performance Optimizations</summary>

- Replaced deep copy with shallow copy for dictionary operations
- Fixed PEP8 violations (empty container checks, naming conventions)

</details>

See [CHANGELOG.md](CHANGELOG.md) for complete details.

---

<details>
<summary>📜 License & Dependencies</summary>

This library is licensed under the MIT-0 License. See the LICENSE file.

Additionally, this project installs the following software for the purposes of deploying and running the labs into the lab environment:

* [openpyxl](https://openpyxl.readthedocs.io/en/stable/index.html) package. Python open source software is provided under the MIT/Expat License.
* [pytest](https://docs.pytest.org/en/latest/) package. Python open source software is provided under the MIT License.
* [pylint](https://pylint.readthedocs.io/en/latest/) package. Python open source software is provided under the GNU General Public License.
* [mypy](http://mypy-lang.org/) package. Python open source software is provided under the MIT License.
* [autopep8](https://github.com/hhatto/autopep8) package. Python open source software is provided under the MIT License.
* [callee](https://callee.readthedocs.io/en/latest/reference/general.html) package. Python open source software is provided under the BSD 3-Clause "New" or "Revised" License.

</details>

<details>
<summary>📁 Project Structure</summary>

This project follows the [src project structure](https://blog.ionelmc.ro/2014/05/25/python-packaging/). In other words, this:
```
├─ src
│  └─ packagename
│     ├─ __init__.py
│     └─ ...
├─ tests
│  └─ ...
```

Additionally, here are notes of other key files/folders not typically found in a Python project:

* **package.sh** - This script bundles the package so that it can be uploaded to Lambda. However, a Lambda package .zip file is already included with the repository. This requires the setup of a virtual environment using pyenv. [AWS Serverless Application Model](https://aws.amazon.com/serverless/sam/) was not used in an effort to minimize the number of concepts introduced.

</details>

<details>
<summary>🚀 Deployment Options (How to Install)</summary>

## Choose Your Deployment Method

Two deployment options are available based on your AWS environment:

| Feature | **Option 1: Cross-Account** | **Option 2: Config Aggregator** | **Option 3: Manual Python** |
|---------|------------------------------|----------------------------------|------------------------------|
| **When to Use** | Organizations without AWS Organizations, or need granular per-account control | Organizations using AWS Organizations (most FedRAMP customers) | Development, testing, one-off inventory collection |
| **Setup Complexity** | Complex - requires IAM roles in each member account | Simple - management account only | Minimal - local Python environment |
| **Performance** | Slower - sequential account processing | Faster - parallel data collection | Same as Option 1 (uses cross-account) |
| **Cost** | Higher - multiple API calls per account | Lower - single aggregated query | Same as Option 1 |
| **IAM Requirements** | Cross-account role in every member account | Config Aggregator authorization (automatic with Orgs) | Local AWS credentials with cross-account role |
| **Best For** | Standalone accounts, non-Org environments | AWS Organizations with 3+ accounts | Local development, debugging, ad-hoc reports |

---

<details>
<summary>🏛️ Option 1: Cross-Account Deployment</summary>

**When to Use:**
- ✅ Organizations without AWS Organizations
- ✅ Need granular per-account IAM control
- ✅ Scanning specific accounts (not entire organization)
- ✅ Testing/development environments

Deploy as a fully automated Lambda function with scheduled execution.

**Quick Start (Automated):**

```bash
# 1. Clone the repository
git clone https://github.com/DanielODeter/fedramp-integrated-inventory-workbook.git
cd fedramp-integrated-inventory-workbook

# 2. Run the quick-deploy script
# Linux/Mac
./quick-deploy.sh <management-account-id> <member-account-id> [aws-profile] [region]

# Windows
quick-deploy.bat <management-account-id> <member-account-id> [aws-profile] [region]

# Example
./quick-deploy.sh 123456789012 987654321098 my-profile us-east-1
```

The script automates all 4 deployment steps below.

---

**Manual Deployment:**

**Prerequisites:**
- AWS CLI configured with appropriate credentials
- AWS Config enabled in all target accounts
- Cross-account IAM role created in member accounts

**Quick Deploy:**

```bash
# 1. Package Lambda code
pip install -r requirements.txt -t package/
cp -r src/inventory package/
cd package && zip -r ../fedramp-inventory-lambda.zip . && cd ..

# 2. Upload to S3
aws s3 mb s3://fedramp-lambda-code-<ACCOUNT_ID>
aws s3 cp fedramp-inventory-lambda.zip s3://fedramp-lambda-code-<ACCOUNT_ID>/

# 3. Deploy CloudFormation stack
aws cloudformation deploy \
  --template-file templates/InventoryCollector.yml \
  --stack-name fedramp-inventory \
  --parameter-overrides \
    MasterAccountName=management \
    DomainAccountId=<MEMBER_ACCOUNT_ID> \
    DomainAccountName=member \
    LambdaPayloadLocation=fedramp-lambda-code-<ACCOUNT_ID> \
    LambdaPayload=fedramp-inventory-lambda.zip \
  --capabilities CAPABILITY_NAMED_IAM
```

**What Gets Created:**
- Lambda function (Python 3.11, 15-minute timeout)
- S3 bucket for inventory reports (encrypted, 7-year retention)
- IAM execution role with Config read permissions
- CloudWatch Event Rule (scheduled: 9 AM & 9 PM UTC)
- CloudWatch Log Group (90-day retention)

**CloudFormation Parameters:**
- `MasterAccountName` - Name for management account (default: "Master")
- `DomainAccountId` - AWS account ID of member account to scan
- `DomainAccountName` - Name for member account (default: "Domain")
- `LambdaPayloadLocation` - S3 bucket containing Lambda zip
- `LambdaPayload` - S3 key for Lambda zip file
- `ScheduleExpression` - Cron schedule (default: `cron(0 9,21 * * ? *)`)

**Outputs:**
- `InventoryReportBucket` - S3 bucket where reports are stored
- `LambdaFunctionName` - Name of the Lambda function

</details>

<details>
<summary>🚀 Option 2: Config Aggregator Deployment (Recommended)</summary>

**When to Use:**
- ✅ Using AWS Organizations
- ✅ Scanning 3+ accounts
- ✅ Want simpler deployment (no member account setup)
- ✅ Need faster performance
- ✅ Want lower costs
- ✅ Production FedRAMP environments

**Prerequisites:**
- AWS Organizations enabled
- AWS Config Aggregator created (see setup below)
- AWS Config enabled in all member accounts

**Step 1: Create Config Aggregator (One-Time Setup)**

```bash
# Option A: Via AWS Console
# 1. Go to AWS Config console
# 2. Navigate to 'Aggregators' in the left menu
# 3. Click 'Add aggregator'
# 4. Choose 'Add an aggregator for my organization'
# 5. Name it 'OrganizationConfigAggregator'

# Option B: Via AWS CLI
aws configservice put-configuration-aggregator \
  --configuration-aggregator-name OrganizationConfigAggregator \
  --organization-aggregation-source '{"RoleArn":"arn:aws:iam::<MGMT_ACCOUNT_ID>:role/aws-service-role/organizations.amazonaws.com/AWSServiceRoleForOrganizations","AllAwsRegions":true}' \
  --region us-east-1
```

**Step 2: Deploy Inventory Solution**

```bash
# 1. Clone the repository
git clone https://github.com/DanielODeter/fedramp-integrated-inventory-workbook.git
cd fedramp-integrated-inventory-workbook

# 2. Run the aggregator deployment script
# Linux/Mac
./quick-deploy-aggregator.sh <management-account-id> [aws-profile] [region] [aggregator-name]

# Windows
quick-deploy-aggregator.bat <management-account-id> [aws-profile] [region] [aggregator-name]

# Example
./quick-deploy-aggregator.sh 123456789012 my-profile us-east-1 OrganizationConfigAggregator
```

**What Gets Created:**
- Lambda function (Python 3.11, 15-minute timeout)
- S3 bucket for inventory reports (encrypted, 90-day retention)
- IAM execution role with Config Aggregator read permissions
- EventBridge Rule (scheduled: monthly on 1st at 2 AM UTC)
- CloudWatch Log Group (90-day retention)

**Key Differences from Cross-Account:**
- ✅ No cross-account IAM roles needed
- ✅ No ACCOUNT_LIST environment variable needed
- ✅ Single API call instead of N calls (one per account)
- ✅ Faster execution time
- ✅ Simpler IAM permissions
- ✅ Automatic discovery of all Organization accounts

**CloudFormation Parameters:**
- `MasterAccountName` - Name for management account (default: "management")
- `ConfigAggregatorName` - Name of Config Aggregator (default: "OrganizationConfigAggregator")
- `LambdaPayloadLocation` - S3 bucket containing Lambda zip
- `LambdaPayload` - S3 key for Lambda zip file

**Outputs:**
- `LambdaFunctionName` - Name of the Lambda function
- `ReportsBucketName` - S3 bucket where reports are stored
- `ConfigAggregatorUsed` - Config Aggregator being used

</details>

<details>
<summary>💻 Option 3: Manual Python Execution (Development/Testing)</summary>

Run locally for development or one-off inventory collection:

**Prerequisites:**
- Python 3.11+
- AWS credentials configured locally
- Environment variables set (see below)

**Setup:**

``` bash
python -m venv .
source ./bin/activate  # On Windows: .\Scripts\activate
pip install -r requirements.txt
```

**Run Tests:**

``` bash
pip install pytest callee
cd src
python -m pytest -v -s ../tests
```

If you've got everything installed correctly, you should see output similar to:

![Unit Test Results](./docs/TestResults.png)

**Execute Inventory Collection:**

```bash
# Set required environment variables
export AWS_REGION=us-east-1
export ACCOUNT_LIST='[{"name":"management","id":"123456789012"}]'
export CROSS_ACCOUNT_ROLE_NAME=InventoryCollector-for-Lambda
export REPORT_TARGET_BUCKET_NAME=my-inventory-reports
export REPORT_TARGET_BUCKET_PATH=inventory-reports

# Run the handler
python -m inventory.handler
```

</details>

<details>
<summary>🛠️ Development Setup</summary>

The project was developed using Visual Studio Code and the .vscode directory with three launch configuration is included. Among them is "Run All Tests" configuration which can be used to run all unit tests in the project. Unit tests mock out calls to AWS services so you do not need to worry about tests using the services when executed. A .env.sample file is included which you can use to set the environment variables used by Visual Studio Code. If the .env file is not recognized by Visual Studio Code, ensure that the "python.envFile" setting is set to "${workspaceFolder}/.env".

</details>

<details>
<summary>⚙️ Environment Variables</summary>

* **AWS_REGION** - AWS region from which the AWS Config resources will be queried
* **ACCOUNT_LIST** - JSON document containing the list of accounts that need to be queried for inventory with the following structure
``` json
[ { "name": <AWS ACCOUNT NAME>, "id": <AWS ACCOUNT NUMBER> } ]
```
* **CROSS_ACCOUNT_ROLE_NAME** - Name of the role that will be assumed on the accounts where inventory needs to be retrieved
* **REPORT_TARGET_BUCKET_PATH** - Prefix of the S3 object key for the report. Similar to foler path to where the report will be uploaded
* **REPORT_TARGET_BUCKET_NAME** - Name of the S3 bucket where report will be uploaded (without "s3://")
* **LOG_LEVEL (Optional)** - Default of INFO. The package uses the STL's logger module and any of the [log levels](https://docs.python.org/3/library/logging.html#levels) available there can be used.
* **REPORT_WORKSHEET_NAME (Optional)** - Default of "Inventory". Name of the worksheet in the "SSP-A13-FedRAMP-Integrated-Inventory-Workbook-Template" spreadsheet where inventory data will be populated.
* **REPORT_WORKSHEET_FIRST_WRITEABLE_ROW_NUMBER** (Optional) - Default of 3. Row number (not index) of where inventory data will start to be populated.

</details>

</details>

<details>
<summary>🏛️ Design & Architecture</summary>

<details>
<summary>✅ Items Completed in This Fork</summary>

* ✅ CloudWatch Log Groups with 90-day retention policy
* ✅ S3 bucket encryption (AES256) and lifecycle policies
* ✅ Improved error handling and input validation
* ✅ Expanded resource type coverage (8→25 types)
* ✅ Python 3.11 runtime upgrade
* ✅ Security vulnerability fixes

</details>

<details>
<summary>🔮 Items Out-of-Scope / Future Enhancements</summary>

* CloudWatch alarms/SNS notifications for inventory collection errors
* AWS Organizations integration for automatic account discovery
* CloudWatch custom metrics for inventory statistics
* Software/Container inventory (applications running on compute resources)
* Structured logging (JSON format for better parsing)
* S3 bucket policies for report access control
* Automated CI/CD pipeline with code coverage reporting
* AWS SAM or CDK for infrastructure as code

</details>

<details>
<summary>🏛️ Architecture Diagrams</summary>
### Conceptual Design
![Conceptual Design](./docs/ConceptualDesign.png)

The above diagram depics the conceptual design. As you can see, the Lambda function can be triggered by a CloudWatch event, gathers inventory information from AWS Config and persists the Workbook into a S3 bucket.

### Static Relationships
![Class Diagram](./docs/StaticClassDiagram.png)

The above diagram shows the modules that make up the inventory package and relationships between them. 

Classes in the Readers and Reports modules implement the [Command Handler pattern](https://blogs.cuttingedge.it/steven/posts/2011/meanwhile-on-the-command-side-of-my-architecture/). To keep things simple and given that dependency injection is not used, method arguments are not represented as Command classes.

The Handler module contains the Lambda entry point that acts as the coordinator of the AwsConfigInventoryReader which is responsible for retrieving inventory information, CreateReportCommandHandler which is responsible for creating the inventory report spreadsheet, and the DeliverReportCommandHandler which is responsible for uploading the spreadsheet to S3.

The Mappers module is composed of a class hierarchy that implements the [Data Mapper pattern](https://martinfowler.com/eaaCatalog/dataMapper.html), providing a well known extensibility point for adding additional classes to map new resource types. The result of data mapping is a list of InventoryData instances. The goal is to normalize the various data structures retrieved from AWS Config into a single type which can then be used by the CreateReportCommandHandler to populate the inventory spreadsheet.

### Dynamic Behavior
The following section details this package's runtime behavior of the major components

#### Report Generation
![Report Generation Sequence Diagram](./docs/SequenceOverview.png)

Before we get into the details, lets look at sequence of steps and the classes that the Lambda Handler module uses to create the inventory report. As you can see, the Handler needs to directly interact with only three classes, AwsConfiInventoryReader, CreateReportCommandHandler and DeliverReportCommandHandler, whose names imply their responsibility. Now let's take a bit of a more detailed look at the call sequence.

![Report Generation Sequence Diagram](./docs/ReportGenerationSequenceDiagram.png)

The above sequence diagram depicts the report generation process in its entirety. Most of the complexity is centered around the retrieval and mapping the AWS Config data into a normalized structure. It is the AwsConfigInventoryReader's resposibility to return this normalized structure. As AwsConfigInventoryReader iterates through each AWS Config resource, it queries the list of DataMappers to determine which can handle the item. Once all AWS Config resources have been mapped into an InventoryData instance, the list is returned to the Handler.

The Handler subsequently calls the CreateReportCommandHandler and DeliverReportCommandHandler to create the inventory spreadsheet and upload it to S3 respectively.

#### Error Handling
![Error Handling Sequence Diagram](./docs/ErrorHandlingSequenceDiagram.png)

As depicted above, errors encountered during the retrieval of inventory information from AWS Config, are logged; however, processing continues. Below is a screenshot from CloudWatch showing the log entry with specific sections of the log entry highlighted.

![Error Log Entry](docs/ErrorLogEntry.png)

</details>

</details>