# (c) 2019 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
# License:
# This sample code is made available under the MIT-0 license. See the LICENSE file.
import json
import logging
import os
from typing import Iterator, List, Optional
import boto3
from botocore.exceptions import ClientError
from inventory.mappers import (DataMapper, EC2DataMapper, ElbDataMapper, DynamoDbTableDataMapper, InventoryData, RdsDataMapper,
                                LambdaDataMapper, S3DataMapper, EfsDataMapper, EksDataMapper, RedshiftDataMapper,
                                ElastiCacheDataMapper, OpenSearchDataMapper, ApiGatewayDataMapper, CloudFrontDataMapper,
                                NatGatewayDataMapper, NetworkInterfaceDataMapper)

_logger = logging.getLogger("inventory.aggregator_reader")
log_level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
if log_level_name not in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'):
    _logger.setLevel(logging.INFO)
    _logger.warning("Invalid LOG_LEVEL '%s', defaulting to INFO", log_level_name)
else:
    _logger.setLevel(getattr(logging, log_level_name))

class AwsConfigAggregatorInventoryReader():
    """
    Reads AWS resource inventory using AWS Config Aggregator.
    Simpler and faster than cross-account role assumption approach.
    Requires AWS Organizations and a Config Aggregator.
    """
    def __init__(self, lambda_context, config_client=None, mappers=None):
        self._lambda_context = lambda_context
        self._config_client = config_client if config_client is not None else boto3.client('config', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
        if mappers is None:
            mappers = [
                EC2DataMapper(), ElbDataMapper(), DynamoDbTableDataMapper(), RdsDataMapper(),
                LambdaDataMapper(), S3DataMapper(), EfsDataMapper(), EksDataMapper(),
                RedshiftDataMapper(), ElastiCacheDataMapper(), OpenSearchDataMapper(),
                ApiGatewayDataMapper(), CloudFrontDataMapper(), NatGatewayDataMapper(),
                NetworkInterfaceDataMapper()
            ]
        self._mappers: List[DataMapper] = mappers

    def _get_resources_from_aggregator(self) -> Iterator[List[str]]:
        aggregator_name = os.environ.get('CONFIG_AGGREGATOR_NAME')
        if not aggregator_name:
            raise ValueError("CONFIG_AGGREGATOR_NAME environment variable is required")
        
        try:
            _logger.info("querying Config Aggregator: %s", aggregator_name)

            next_token: str = ''
            # Note: Resource types are hardcoded here for query performance.
            # This list should be kept in sync with the configured mappers.
            query = (
                "SELECT arn, resourceType, configuration, tags, accountId "
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
                if next_token:
                    resources_result = self._config_client.select_aggregate_resource_config(
                        Expression=query,
                        ConfigurationAggregatorName=aggregator_name,
                        NextToken=next_token
                    )
                else:
                    resources_result = self._config_client.select_aggregate_resource_config(
                        Expression=query,
                        ConfigurationAggregatorName=aggregator_name
                    )
                
                next_token = resources_result.get('NextToken', '')
                results: List[str] = resources_result.get('Results', [])

                _logger.debug("page returned %s resources and next token of '%s'", len(results), next_token)

                yield results

                if not next_token:
                    break
        except ClientError as ex:
            _logger.error("Received error: %s while retrieving resources from aggregator %s", ex, aggregator_name, exc_info=True)
            raise

    def get_resources_from_all_accounts(self) -> List[InventoryData]:
        _logger.info("starting retrieval of inventory from AWS Config Aggregator")

        all_inventory: List[InventoryData] = []

        for resource_list_page in self._get_resources_from_aggregator():
            _logger.debug("current page of inventory contained %s items from AWS Config Aggregator", len(resource_list_page))

            for raw_resource in resource_list_page:
                resource: dict = json.loads(raw_resource)

                # One line item returned from AWS Config can result in multiple inventory line items (e.g. multiple IPs)
                mapper: Optional[DataMapper] = next((mapper for mapper in self._mappers if mapper.can_map(resource["resourceType"])), None)
                
                if not mapper:
                    _logger.warning("skipping mapping, unable to find mapper for resource type of %s", resource['resourceType'])
                    continue

                inventory_items = mapper.map(resource)
                if inventory_items:
                    all_inventory.extend(inventory_items)

        _logger.info("completed getting inventory, with a total of %s", len(all_inventory))

        return all_inventory
