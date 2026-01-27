# FedRAMP Integrated Inventory Workbook Generator - Enhanced

> **Community-Maintained Fork**: This is an enhanced version of the [original AWS sample](https://github.com/aws-samples/fedramp-integrated-inventory-workbook) (now archived). Includes security fixes, Python 3.11 upgrade, and 17 additional AWS services.

## What's New - January 2025

### 🔒 Critical Security Fixes
- Fixed CloudFormation YAML syntax errors in AssumeRolePolicyDocument (missing list indicator)
- Fixed ARN parsing boundary check preventing IndexError
- Fixed mutable default argument causing shared state between instances
- Added S3 bucket encryption (AES256) for FedRAMP compliance
- Fixed logger level configuration to properly handle string environment variables

### ⚡ High Priority Fixes
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

### 🏗️ Infrastructure Improvements
- Added CloudWatch Log Groups with 90-day retention policy
- Added S3 lifecycle policies (7-year retention, 90-day noncurrent versions)
- Removed hardcoded IAM role names for stack reusability
- Fixed CloudFormation parameter validation (12-digit AWS account ID pattern)
- Fixed Output to return ARN instead of role name
- Removed obsolete DependsOn configurations
- Made temp file paths portable across operating systems

### 🚀 New AWS Service Support (8→25 resource types)

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

### 📊 Performance Optimizations
- Replaced deep copy with shallow copy for dictionary operations
- Fixed PEP8 violations (empty container checks, naming conventions)

See [CHANGELOG.md](CHANGELOG.md) for complete details.

---

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

Additionally, this project installs the following software for the purposes of deploying and running the labs into the lab environment:

* [openpyxl](https://openpyxl.readthedocs.io/en/stable/index.html) package. Python open source software is provided under the MIT/Expat License.
* [pytest](https://docs.pytest.org/en/latest/) package. Python open source software is provided under the MIT License.
* [pylint](https://pylint.readthedocs.io/en/latest/) package. Python open source software is provided under the GNU General Public License.
* [mypy](http://mypy-lang.org/) package. Python open source software is provided under the MIT License.
* [autopep8](https://github.com/hhatto/autopep8) package. Python open source software is provided under the MIT License.
* [callee](https://callee.readthedocs.io/en/latest/reference/general.html) package. Python open source software is provided under the BSD 3-Clause "New" or "Revised" License.

## Overview

This sample shows how you can create a Lambda function to retrieve inventory information to create the integrated inventory spreadsheet which can be used as a separate attachment to the FedRAMP System Security Plan (SSP). This is an enhanced fork of the [original AWS blog post project](https://aws.amazon.com/blogs/publicsector/automating-creation-fedramp-integrated-inventory-workbook/). The spreadsheet template can be found [here](https://www.fedramp.gov/new-integrated-inventory-template/).

This sample populates the inventory spreadsheet with a point in time view of AWS resources spanning multiple accounts. **25 resource types** are now supported (see list above).

There are other assets that must be tracked in the spreadsheet (e.g. software running on EC2 instances/containers) which this sample does not gather. The design does lend itself to be extended to gather inventory information from multiple sources for various resource types.

## Contents

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

## Running the Code
The code requires Python 3.11+. After cloning the repository locally, create a virtualenv however you prefer. Both a requirements.txt file and Pipfile have been provided, for example if you have Python 3.11 installed and set at the current version, you can run the following commands in the project directory:

``` bash
python -m venv .
source ./bin/activate
```

Install the package, its dependencies and dev dependencies. Dev dependencies are not included in the requirements.txt as pipenv is used for dependency management, and requirements.txt was created without including dev dependencies. For ease of getting up an running though, you can execute the following commands:

``` bash
python -m pip install -r requirements.txt
python -m pip install pytest
python -m pip install callee
cd src
python -m pytest -v -s ../tests
```

If you've got everything installed correctly, you should see output similar to:

![Unit Test Results](./docs/TestResults.png)

### Development
The project was developed using Visual Studio Code and the .vscode directory with three launch configuration is included. Among them is "Run All Tests" configuration which can be used to run all unit tests in the project. Unit tests mock out calls to AWS services so you do not need to worry about tests using the services when executed. A .env.sample file is included which you can use to set the environment variables used by Visual Studio Code. If the .env file is not recognized by Visual Studio Code, ensure that the "python.envFile" setting is set to "${workspaceFolder}/.env".

### Environment Variables

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

## Design
This section contains the design details of this package.

### Items Completed in This Fork
* ✅ CloudWatch Log Groups with 90-day retention policy
* ✅ S3 bucket encryption (AES256) and lifecycle policies
* ✅ Improved error handling and input validation
* ✅ Expanded resource type coverage (8→25 types)
* ✅ Python 3.11 runtime upgrade
* ✅ Security vulnerability fixes

### Items Out-of-Scope / Future Enhancements
* CloudWatch alarms/SNS notifications for inventory collection errors
* AWS Organizations integration for automatic account discovery
* CloudWatch custom metrics for inventory statistics
* Software/Container inventory (applications running on compute resources)
* Structured logging (JSON format for better parsing)
* S3 bucket policies for report access control
* Automated CI/CD pipeline with code coverage reporting
* AWS SAM or CDK for infrastructure as code

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