# (c) 2019 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
# License:
# This sample code is made available under the MIT-0 license. See the LICENSE file.
import copy
import logging
import os
from typing import List
from abc import ABC, abstractmethod

_logger = logging.getLogger("inventory.mappers")
_logger.setLevel(getattr(logging, os.environ.get("LOG_LEVEL", "INFO"), logging.INFO))

def _get_tag_value(tags: dict, tag_name: str) -> str:
    return next((tag["value"] for tag in tags if tag["key"].casefold() == tag_name.casefold()), '')

class InventoryData:
   def __init__(self, *, asset_type=None, unique_id=None, ip_address=None, location=None, is_virtual=None,
                 authenticated_scan_planned=None, dns_name=None, mac_address=None, baseline_config=None,
                 hardware_model=None,
                 is_public=None, network_id=None, iir_diagram_label=None, owner=None, software_product_name=None, software_vendor=None):
        self.asset_type = asset_type
        self.unique_id = unique_id
        self.ip_address = ip_address
        self.location = location
        self.is_virtual = is_virtual
        self.authenticated_scan_planned = authenticated_scan_planned
        self.dns_name = dns_name
        self.mac_address = mac_address
        self.baseline_config = baseline_config
        self.hardware_model = hardware_model
        self.is_public = is_public
        self.network_id = network_id
        self.iir_diagram_label = iir_diagram_label
        self.owner = owner
        self.software_product_name = software_product_name
        self.software_vendor = software_vendor

class DataMapper(ABC):
    @abstractmethod
    def _do_mapping(self, config_resource: dict) -> List[InventoryData]:
        pass

    @abstractmethod
    def _get_supported_resource_type(self) -> List[str]:
        pass

    def can_map(self, resource_type: str) -> bool:
        return resource_type in self._get_supported_resource_type()

    def map(self, config_resource: dict) -> List[InventoryData]:
        if not self.can_map(config_resource["resourceType"]):
            return[]

        mapped_data = []

        _logger.debug(f"mapping {config_resource['resourceType']}")

        mapped_data.extend(self._do_mapping(config_resource))

        _logger.debug(f"mapping resulted in a total of {len(mapped_data)} rows")

        return mapped_data    

class EC2DataMapper(DataMapper):
    def _get_supported_resource_type(self) -> List[str]:
        return ["AWS::EC2::Instance"]

    def _do_mapping(self, config_resource: dict) -> List[InventoryData]:
        ec2_data_list: List[InventoryData] = []
        config = config_resource.get("configuration", {})
        tags = config_resource.get("tags", [])

        for nic in config.get("networkInterfaces", []):
            for ipAddress in nic.get("privateIpAddresses", []):
                ec2_data = { "asset_type": "EC2",
                             "unique_id": config.get("instanceId", ""),
                             "ip_address": ipAddress.get("privateIpAddress", ""),
                             "is_virtual": "Yes",
                             "authenticated_scan_planned": "Yes",
                             "mac_address": nic.get("macAddress", ""),
                             "baseline_config": config.get("imageId", ""),
                             "hardware_model": config.get("instanceType", ""),
                             "network_id": config.get("vpcId", ""),
                             "iir_diagram_label": _get_tag_value(tags, "iir_diagram_label"),
                             "owner": _get_tag_value(tags, "owner") }

                if (public_dns_name := config.get("publicDnsName")):
                    ec2_data["dns_name"] = public_dns_name
                    ec2_data["is_public"] = "Yes"
                else:
                    ec2_data["dns_name"] = config.get("privateDnsName", "")
                    ec2_data["is_public"] = "No"

                ec2_data_list.append(InventoryData(**ec2_data))

                if "association" in ipAddress:
                    # Each IP address needs its own row in report so public IP requires an additional row
                    ec2_data = {**ec2_data}
                    ec2_data["ip_address"] = ipAddress.get("association", {}).get("publicIp", "")

                    ec2_data_list.append(InventoryData(**ec2_data))

        return ec2_data_list

class ElbDataMapper(DataMapper):
    def _get_supported_resource_type(self) -> List[str]:
        return ["AWS::ElasticLoadBalancing::LoadBalancer", "AWS::ElasticLoadBalancingV2::LoadBalancer"]

    def _get_asset_type_name(self, config_resource: dict) -> str:
        if config_resource["resourceType"] == "AWS::ElasticLoadBalancing::LoadBalancer":
            return "Load Balancer-Classic"
        else:
            return f"Load Balancer-{config_resource['configuration']['type']}"

    def _get_ip_addresses(self, availability_zones: dict) -> List[str]:
        ip_addresses: List[str] = []

        for availabilityZone in availability_zones:
            if load_balancer_addresses := availabilityZone.get("loadBalancerAddresses"):
                for load_balancer_address in (load_balancer_address for load_balancer_address in load_balancer_addresses if "ipAddress" in load_balancer_address):
                    ip_addresses.append(load_balancer_address["ipAddress"])

        return ip_addresses

    def _do_mapping(self, config_resource: dict) -> List[InventoryData]:
        data_list: List[InventoryData] = []

        data = { "asset_type": self._get_asset_type_name(config_resource),
                 "unique_id": config_resource["arn"],
                 "is_virtual": "Yes",
                 "authenticated_scan_planned": "Yes",
                 "is_public": "Yes" if config_resource.get("configuration").get("scheme", "unknown") == "internet-facing" else "No",
                 # Classic ELBs have key of "vpcid" while V2 ELBs have key of "vpcId"
                 "network_id": config_resource["configuration"]["vpcId"] if "vpcId" in config_resource["configuration"] else config_resource["configuration"]["vpcid"],
                 "iir_diagram_label": _get_tag_value(config_resource["tags"], "iir_diagram_label"),
                 "owner": _get_tag_value(config_resource["tags"], "owner") }

        if not ip_addresses:
            data_list.append(InventoryData(**data))
        else:
            for ip_address in ip_addresses:
                data = {**data}

                data["ip_address"] = ip_address

                data_list.append(InventoryData(**data))
        else:
            data_list.append(InventoryData(**data))

        return data_list

class RdsDataMapper(DataMapper):
    def _get_supported_resource_type(self) -> List[str]:
        return ["AWS::RDS::DBInstance", "AWS::RDS::DBCluster"]

    def _do_mapping(self, config_resource: dict) -> List[InventoryData]:
        data = { "asset_type": "RDS",
                 "unique_id": config_resource["arn"],
                 "is_virtual": "Yes",
                 "software_vendor": "AWS",
                 # DB Cluster vs DB Instance
                 "is_public": "Yes" if config_resource.get("configuration", {}).get("publiclyAccessible") else "No",                 
                 "hardware_model": config_resource["configuration"] ["dBInstanceClass"] if "dBInstanceClass" in config_resource["configuration"] else '',                 
                 "software_product_name": f"{config_resource['configuration']['engine']}-{config_resource['configuration']['engineVersion']}",
                 # DB Cluster vs DB Instance
                 "network_id": config_resource['configuration']['dBSubnetGroup']['vpcId'] if "dBSubnetGroup" in config_resource['configuration'] else config_resource['configuration']['dbsubnetGroup'] if "dbsubnetGroup" in config_resource['configuration'] else '',
                 "iir_diagram_label": _get_tag_value(config_resource["tags"], "iir_diagram_label"),
                 "owner": _get_tag_value(config_resource["tags"], "owner") }

        return [InventoryData(**data)]

class DynamoDbTableDataMapper(DataMapper):
    def _get_supported_resource_type(self) -> List[str]:
        return ["AWS::DynamoDB::Table"]

    def _do_mapping(self, config_resource: dict) -> List[InventoryData]:
        data = { "asset_type": "DynamoDB",
                 "unique_id": config_resource["arn"],
                 "is_virtual": "Yes",
                 "is_public": "No",
                 "software_vendor": "AWS",
                 "software_product_name": "DynamoDB",
                 "iir_diagram_label": _get_tag_value(config_resource["tags"], "iir_diagram_label"),
                 "owner": _get_tag_value(config_resource["tags"], "owner") }

        return [InventoryData(**data)]

class EcsDataMapper(DataMapper):
    def _get_supported_resource_type(self) -> List[str]:
        return ["AWS::ECS::Task", "AWS::ECS::Service"]

    def _do_mapping(self, config_resource: dict) -> List[InventoryData]:
        data_list: List[InventoryData] = []
        config = config_resource["configuration"]
        
        if config_resource["resourceType"] == "AWS::ECS::Task":
            launch_type = config.get("launchType", "UNKNOWN")
            
            for attachment in config.get("attachments", []):
                if attachment.get("type") == "ElasticNetworkInterface":
                    for detail in attachment.get("details", []):
                        if detail.get("name") == "privateIPv4Address":
                            data = {
                                "asset_type": f"ECS-{launch_type}",
                                "unique_id": config_resource["arn"],
                                "ip_address": detail.get("value"),
                                "is_virtual": "Yes",
                                "authenticated_scan_planned": "Yes",
                                "is_public": "No",
                                "iir_diagram_label": _get_tag_value(config_resource["tags"], "iir_diagram_label"),
                                "owner": _get_tag_value(config_resource["tags"], "owner")
                            }
                            data_list.append(InventoryData(**data))
        else:
            data = {
                "asset_type": "ECS-Service",
                "unique_id": config_resource["arn"],
                "is_virtual": "Yes",
                "is_public": "No",
                "iir_diagram_label": _get_tag_value(config_resource["tags"], "iir_diagram_label"),
                "owner": _get_tag_value(config_resource["tags"], "owner")
            }
            data_list.append(InventoryData(**data))
        
        return data_list if data_list else [InventoryData(
            asset_type=f"ECS-{config.get('launchType', 'UNKNOWN')}",
            unique_id=config_resource["arn"],
            is_virtual="Yes",
            is_public="No",
            iir_diagram_label=_get_tag_value(config_resource["tags"], "iir_diagram_label"),
            owner=_get_tag_value(config_resource["tags"], "owner")
        )]

class LambdaDataMapper(DataMapper):
    def _get_supported_resource_type(self) -> List[str]:
        return ["AWS::Lambda::Function"]

    def _do_mapping(self, config_resource: dict) -> List[InventoryData]:
        config = config_resource["configuration"]
        data = {
            "asset_type": "Lambda",
            "unique_id": config_resource["arn"],
            "is_virtual": "Yes",
            "authenticated_scan_planned": "Yes",
            "is_public": "No",
            "software_vendor": "AWS",
            "software_product_name": f"Lambda-{config.get('runtime', 'unknown')}",
            "network_id": config.get("vpcConfig", {}).get("vpcId", ""),
            "iir_diagram_label": _get_tag_value(config_resource["tags"], "iir_diagram_label"),
            "owner": _get_tag_value(config_resource["tags"], "owner")
        }
        return [InventoryData(**data)]

class S3DataMapper(DataMapper):
    def _get_supported_resource_type(self) -> List[str]:
        return ["AWS::S3::Bucket"]

    def _do_mapping(self, config_resource: dict) -> List[InventoryData]:
        config = config_resource.get("configuration", {})
        
        # Check public access block configuration
        public_access_block = config.get("publicAccessBlockConfiguration", {})
        is_public = not (public_access_block.get("blockPublicAcls") and 
                        public_access_block.get("blockPublicPolicy") and
                        public_access_block.get("ignorePublicAcls") and
                        public_access_block.get("restrictPublicBuckets"))
        
        data = {
            "asset_type": "S3",
            "unique_id": config_resource["arn"],
            "is_virtual": "Yes",
            "is_public": "Yes" if is_public else "No",
            "software_vendor": "AWS",
            "software_product_name": "S3",
            "iir_diagram_label": _get_tag_value(config_resource.get("tags", []), "iir_diagram_label"),
            "owner": _get_tag_value(config_resource.get("tags", []), "owner")
        }
        return [InventoryData(**data)]

class EfsDataMapper(DataMapper):
    def _get_supported_resource_type(self) -> List[str]:
        return ["AWS::EFS::FileSystem"]

    def _do_mapping(self, config_resource: dict) -> List[InventoryData]:
        data = {
            "asset_type": "EFS",
            "unique_id": config_resource["arn"],
            "is_virtual": "Yes",
            "is_public": "No",
            "software_vendor": "AWS",
            "software_product_name": "EFS",
            "iir_diagram_label": _get_tag_value(config_resource["tags"], "iir_diagram_label"),
            "owner": _get_tag_value(config_resource["tags"], "owner")
        }
        return [InventoryData(**data)]

class RedshiftDataMapper(DataMapper):
    def _get_supported_resource_type(self) -> List[str]:
        return ["AWS::Redshift::Cluster"]

    def _do_mapping(self, config_resource: dict) -> List[InventoryData]:
        config = config_resource["configuration"]
        data = {
            "asset_type": "Redshift",
            "unique_id": config_resource["arn"],
            "is_virtual": "Yes",
            "is_public": "Yes" if config.get("publiclyAccessible") else "No",
            "software_vendor": "AWS",
            "software_product_name": f"Redshift-{config.get('clusterVersion', 'unknown')}",
            "hardware_model": config.get("nodeType", ""),
            "network_id": config.get("vpcId", ""),
            "iir_diagram_label": _get_tag_value(config_resource["tags"], "iir_diagram_label"),
            "owner": _get_tag_value(config_resource["tags"], "owner")
        }
        return [InventoryData(**data)]

class ElastiCacheDataMapper(DataMapper):
    def _get_supported_resource_type(self) -> List[str]:
        return ["AWS::ElastiCache::CacheCluster", "AWS::ElastiCache::ReplicationGroup"]

    def _do_mapping(self, config_resource: dict) -> List[InventoryData]:
        config = config_resource["configuration"]
        engine = config.get('engine', 'unknown')
        asset_type = f"ElastiCache-{engine.capitalize()}"
        
        data = {
            "asset_type": asset_type,
            "unique_id": config_resource["arn"],
            "is_virtual": "Yes",
            "is_public": "No",
            "software_vendor": "AWS",
            "software_product_name": f"{asset_type}-{config.get('engineVersion', 'unknown')}",
            "hardware_model": config.get("cacheNodeType", ""),
            "network_id": config.get("cacheSubnetGroup", {}).get("vpcId", ""),
            "iir_diagram_label": _get_tag_value(config_resource["tags"], "iir_diagram_label"),
            "owner": _get_tag_value(config_resource["tags"], "owner")
        }
        return [InventoryData(**data)]

class OpenSearchDataMapper(DataMapper):
    def _get_supported_resource_type(self) -> List[str]:
        return ["AWS::Elasticsearch::Domain", "AWS::OpenSearchService::Domain"]

    def _do_mapping(self, config_resource: dict) -> List[InventoryData]:
        config = config_resource["configuration"]
        data = {
            "asset_type": "OpenSearch",
            "unique_id": config_resource["arn"],
            "is_virtual": "Yes",
            "is_public": "No",
            "software_vendor": "AWS",
            "software_product_name": f"OpenSearch-{config.get('elasticsearchVersion', config.get('engineVersion', 'unknown'))}",
            "network_id": config.get("vpcOptions", {}).get("vpcId", ""),
            "iir_diagram_label": _get_tag_value(config_resource["tags"], "iir_diagram_label"),
            "owner": _get_tag_value(config_resource["tags"], "owner")
        }
        return [InventoryData(**data)]

class EksDataMapper(DataMapper):
    def _get_supported_resource_type(self) -> List[str]:
        return ["AWS::EKS::Cluster"]

    def _do_mapping(self, config_resource: dict) -> List[InventoryData]:
        config = config_resource["configuration"]
        data = {
            "asset_type": "EKS",
            "unique_id": config_resource["arn"],
            "is_virtual": "Yes",
            "authenticated_scan_planned": "Yes",
            "is_public": "No",
            "software_vendor": "AWS",
            "software_product_name": f"EKS-{config.get('version', 'unknown')}",
            "network_id": config.get("resourcesVpcConfig", {}).get("vpcId", ""),
            "iir_diagram_label": _get_tag_value(config_resource["tags"], "iir_diagram_label"),
            "owner": _get_tag_value(config_resource["tags"], "owner")
        }
        return [InventoryData(**data)]

class NetworkInterfaceDataMapper(DataMapper):
    def _get_supported_resource_type(self) -> List[str]:
        return ["AWS::EC2::NetworkInterface"]

    def _do_mapping(self, config_resource: dict) -> List[InventoryData]:
        config = config_resource["configuration"]
        data_list: List[InventoryData] = []
        
        for ip_addr in config.get("privateIpAddresses", []):
            data = {
                "asset_type": "NetworkInterface",
                "unique_id": config.get("networkInterfaceId", config_resource["arn"]),
                "ip_address": ip_addr.get("privateIpAddress"),
                "is_virtual": "Yes",
                "is_public": "No",
                "mac_address": config.get("macAddress", ""),
                "network_id": config.get("vpcId", ""),
                "iir_diagram_label": _get_tag_value(config_resource["tags"], "iir_diagram_label"),
                "owner": _get_tag_value(config_resource["tags"], "owner")
            }
            data_list.append(InventoryData(**data))
        
        return data_list if data_list else [InventoryData(
            asset_type="NetworkInterface",
            unique_id=config.get("networkInterfaceId", config_resource["arn"]),
            is_virtual="Yes",
            is_public="No",
            network_id=config.get("vpcId", ""),
            iir_diagram_label=_get_tag_value(config_resource["tags"], "iir_diagram_label"),
            owner=_get_tag_value(config_resource["tags"], "owner")
        )]

class NatGatewayDataMapper(DataMapper):
    def _get_supported_resource_type(self) -> List[str]:
        return ["AWS::EC2::NatGateway"]

    def _do_mapping(self, config_resource: dict) -> List[InventoryData]:
        config = config_resource["configuration"]
        data_list: List[InventoryData] = []
        
        for addr in config.get("natGatewayAddresses", []):
            data = {
                "asset_type": "NATGateway",
                "unique_id": config.get("natGatewayId", config_resource["arn"]),
                "ip_address": addr.get("privateIp", ""),
                "is_virtual": "Yes",
                "is_public": "Yes",
                "network_id": config.get("vpcId", ""),
                "iir_diagram_label": _get_tag_value(config_resource["tags"], "iir_diagram_label"),
                "owner": _get_tag_value(config_resource["tags"], "owner")
            }
            data_list.append(InventoryData(**data))
        
        return data_list if data_list else [InventoryData(
            asset_type="NATGateway",
            unique_id=config.get("natGatewayId", config_resource["arn"]),
            is_virtual="Yes",
            is_public="Yes",
            network_id=config.get("vpcId", ""),
            iir_diagram_label=_get_tag_value(config_resource["tags"], "iir_diagram_label"),
            owner=_get_tag_value(config_resource["tags"], "owner")
        )]

class ApiGatewayDataMapper(DataMapper):
    def _get_supported_resource_type(self) -> List[str]:
        return ["AWS::ApiGateway::RestApi", "AWS::ApiGatewayV2::Api"]

    def _do_mapping(self, config_resource: dict) -> List[InventoryData]:
        config = config_resource["configuration"]
        
        # Check if API is private
        is_private = False
        if config_resource["resourceType"] == "AWS::ApiGateway::RestApi":
            endpoint_types = config.get("endpointConfiguration", {}).get("types", [])
            is_private = "PRIVATE" in endpoint_types
        
        api_type = "API-REST" if config_resource["resourceType"] == "AWS::ApiGateway::RestApi" else f"API-{config.get('protocolType', 'HTTP')}"
        
        data = {
            "asset_type": api_type,
            "unique_id": config_resource["arn"],
            "is_virtual": "Yes",
            "is_public": "No" if is_private else "Yes",
            "software_vendor": "AWS",
            "software_product_name": "API Gateway",
            "network_id": ",".join(config.get("endpointConfiguration", {}).get("vpcEndpointIds", [])) if is_private else "",
            "iir_diagram_label": _get_tag_value(config_resource["tags"], "iir_diagram_label"),
            "owner": _get_tag_value(config_resource["tags"], "owner")
        }
        return [InventoryData(**data)]

class CloudFrontDataMapper(DataMapper):
    def _get_supported_resource_type(self) -> List[str]:
        return ["AWS::CloudFront::Distribution"]

    def _do_mapping(self, config_resource: dict) -> List[InventoryData]:
        config = config_resource["configuration"]
        data = {
            "asset_type": "CloudFront",
            "unique_id": config_resource["arn"],
            "dns_name": config.get("domainName", ""),
            "is_virtual": "Yes",
            "is_public": "Yes",
            "software_vendor": "AWS",
            "software_product_name": "CloudFront",
            "iir_diagram_label": _get_tag_value(config_resource["tags"], "iir_diagram_label"),
            "owner": _get_tag_value(config_resource["tags"], "owner")
        }
        return [InventoryData(**data)]
