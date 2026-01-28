# (c) 2019 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
# License:
# This sample code is made available under the MIT-0 license. See the LICENSE file.
import json
import logging
import os
from typing import Iterator, List, Optional
import boto3
from botocore.exceptions import ClientError
from  inventory.mappers import (DataMapper, EC2DataMapper, ElbDataMapper, DynamoDbTableDataMapper, InventoryData, RdsDataMapper,
                                 LambdaDataMapper, S3DataMapper, EfsDataMapper, EksDataMapper, RedshiftDataMapper,
                                 ElastiCacheDataMapper, OpenSearchDataMapper, ApiGatewayDataMapper, CloudFrontDataMapper,
                                 NatGatewayDataMapper, NetworkInterfaceDataMapper)

_logger = logging.getLogger("inventory.readers")
log_level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
if log_level_name not in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'):
    _logger.setLevel(logging.INFO)
    _logger.warning("Invalid LOG_LEVEL '%s', defaulting to INFO", log_level_name)
else:
    _logger.setLevel(getattr(logging, log_level_name))

class AwsConfigInventoryReader():
    def __init__(self, lambda_context, sts_client=None, mappers=None):
        self._lambda_context = lambda_context
        self._sts_client = sts_client if sts_client is not None else boto3.client('sts')
        if mappers is None:
            mappers = [
                EC2DataMapper(), ElbDataMapper(), DynamoDbTableDataMapper(), RdsDataMapper(),
                LambdaDataMapper(), S3DataMapper(), EfsDataMapper(), EksDataMapper(),
                RedshiftDataMapper(), ElastiCacheDataMapper(), OpenSearchDataMapper(),
                ApiGatewayDataMapper(), CloudFrontDataMapper(), NatGatewayDataMapper(),
                NetworkInterfaceDataMapper()
            ]
        self._mappers: List[DataMapper] = mappers

    # Moved into it's own method to make it easier to mock boto3 client
    def _get_config_client(self, sts_response) -> boto3.client:
        return boto3.client('config', 
                            aws_access_key_id=sts_response['Credentials']['AccessKeyId'],
                            aws_secret_access_key=sts_response['Credentials']['SecretAccessKey'],
                            aws_session_token=sts_response['Credentials']['SessionToken'],
                            region_name=os.environ.get('AWS_REGION', 'us-east-1'))

    def _get_resources_from_account(self, account_id: str) -> Iterator[List[str]]:
        cross_account_role = os.environ.get('CROSS_ACCOUNT_ROLE_NAME')
        if not cross_account_role:
            raise ValueError("CROSS_ACCOUNT_ROLE_NAME environment variable is required")
        
        try:
            _logger.info(f"assuming role on account {account_id}")

            sts_response = self._sts_client.assume_role(RoleArn=f"arn:{self._get_aws_partition()}:iam::{account_id}:role/{cross_account_role}",
                                                        RoleSessionName=f"{account_id}-Assumed-Role",
                                                        DurationSeconds=900)
            config_client = self._get_config_client(sts_response)

            next_token: str = ''
            # Note: Resource types are hardcoded here for query performance.
            # This list should be kept in sync with the configured mappers.
            query = (
                "SELECT arn, resourceType, configuration, tags "
                "WHERE resourceType IN ("
                "'AWS::EC2::Instance', "
                "'AWS::ElasticLoadBalancingV2::LoadBalancer', "
                "'AWS::ElasticLoadBalancing::LoadBalancer', "
                "'AWS::DynamoDB::Table', "
                "'AWS::RDS::DBInstance', "
                "'AWS::RDS::DBCluster', "
                "'AWS::Lambda::Function', "
                "'AWS::S3::Bucket', "
                "'AWS::EFS::FileSystem', "
                "'AWS::EKS::Cluster', "
                "'AWS::Redshift::Cluster', "
                "'AWS::ElastiCache::CacheCluster', "
                "'AWS::ElastiCache::ReplicationGroup', "
                "'AWS::Elasticsearch::Domain', "
                "'AWS::OpenSearchService::Domain', "
                "'AWS::ApiGateway::RestApi', "
                "'AWS::ApiGatewayV2::Api', "
                "'AWS::CloudFront::Distribution', "
                "'AWS::EC2::NatGateway', "
                "'AWS::EC2::NetworkInterface')"
            )
            while True:
                resources_result = config_client.select_resource_config(
                    Expression=query,
                    NextToken=next_token
                )
                
                next_token = resources_result.get('NextToken', '')
                results: List[str] = resources_result.get('Results', [])

                _logger.debug(f"page returned {len(results)} and next token of '{next_token}'")

                yield results

                if not next_token:
                    break
        except ClientError as ex:
            _logger.error("Received error: %s while retrieving resources from account %s, returning empty results.", ex, account_id, exc_info=True)
            yield []

    def _get_aws_partition(self):
        arn_parts = self._lambda_context.invoked_function_arn.split(":")
        if len(arn_parts) < 2:
            raise ValueError(f"Invalid Lambda function ARN format: {self._lambda_context.invoked_function_arn}")
        return arn_parts[1]

    def get_resources_from_all_accounts(self) -> List[InventoryData]:
        _logger.info("starting retrieval of inventory from AWS Config")

        all_inventory : List[InventoryData] = []
        
        try:
            accounts = json.loads(os.environ["ACCOUNT_LIST"])
        except KeyError:
            _logger.error("ACCOUNT_LIST environment variable is required")
            raise ValueError("ACCOUNT_LIST environment variable is required")
        except json.JSONDecodeError as ex:
            _logger.error("ACCOUNT_LIST environment variable contains invalid JSON: %s", ex)
            raise ValueError(f"ACCOUNT_LIST environment variable contains invalid JSON: {ex}")

        for account in accounts:
            account_id = account.get('id')
            if not account_id:
                _logger.warning("Skipping account with missing 'id' field")
                continue
            
            _logger.info("retrieving inventory for account %s", account_id)

            for resource_list_page in self._get_resources_from_account(account_id):
                _logger.debug("current page of inventory contained %s items from AWS Config", len(resource_list_page))

                for raw_resource in resource_list_page:
                    resource : dict = json.loads(raw_resource)

                    # One line item returned from AWS Config can result in multiple inventory line items (e.g. multiple IPs)
                    # Mappers that do not support the resource type will return False
                    mapper: Optional[DataMapper] = next((mapper for mapper in self._mappers if mapper.can_map(resource["resourceType"])), None)
                    
                    if not mapper:
                        _logger.warning(f"skipping mapping, unable to find mapper for resource type of {resource['resourceType']}")

                        continue

                    inventory_items = mapper.map(resource)
                    if inventory_items:
                        all_inventory.extend(inventory_items)

        _logger.info(f"completed getting inventory, with a total of {len(all_inventory)}")

        return all_inventory
