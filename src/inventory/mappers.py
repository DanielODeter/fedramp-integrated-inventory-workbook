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
    value = next((tag["value"] for tag in tags if tag["key"].casefold() == tag_name.casefold()), '')
    return _sanitize_for_excel(value) if value else ''

def _sanitize_for_excel(value: str) -> str:
    """Prevent Excel formula injection by prefixing dangerous characters"""
    if value and isinstance(value, str) and len(value) > 0 and value[0] in ('=', '+', '-', '@'):
        return f"'{value}"
    return value if value else ''

class InventoryData:
   def __init__(self, *, asset_type=None, unique_id=None, ip_address=None, location=None, is_virtual=None,
                 authenticated_scan_planned=None, dns_name=None, mac_address=None, baseline_config=None,
                 hardware_model=None,
                 is_public=None, network_id=None, iir_diagram_label=None, owner=None, software_product_name=None, software_vendor=None):
        self.asset_type = _sanitize_for_excel(asset_type) if asset_type else None
        self.unique_id = _sanitize_for_excel(unique_id) if unique_id else None
        self.ip_address = ip_address
        self.location = location
        self.is_virtual = is_virtual
        self.authenticated_scan_planned = authenticated_scan_planned
        self.dns_name = _sanitize_for_excel(dns_name) if dns_name else None
        self.mac_address = mac_address
        self.baseline_config = _sanitize_for_excel(baseline_config) if baseline_config else None
        self.hardware_model = _sanitize_for_excel(hardware_model) if hardware_model else None
        self.is_public = is_public
        self.network_id = network_id
        self.iir_diagram_label = _sanitize_for_excel(iir_diagram_label) if iir_diagram_label else None
        self.owner = _sanitize_for_excel(owner) if owner else None
        self.software_product_name = _sanitize_for_excel(software_product_name) if software_product_name else None
        self.software_vendor = _sanitize_for_excel(software_vendor) if software_vendor else None

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

        _logger.debug("mapping %s", config_resource['resourceType'])

        mapped_data.extend(self._do_mapping(config_resource))

        _logger.debug("mapping resulted in a total of %d rows", len(mapped_data))

        return mapped_data    

class EC2DataMapper(DataMapper):
    def _get_supported_resource_type(self) -> List[str]:
        return ["AWS::EC2::Instance"]

    def _do_mapping(self, config_resource: dict) -> List[InventoryData]:
        ec2_data_list: List[InventoryData] = []

        for nic in config_resource["configuration"]["networkInterfaces"]:
            for ipAddress in nic["privateIpAddresses"]:
                ec2_data = { "asset_type": "EC2",
                             "unique_id": config_resource["configuration"]["instanceId"],
                             "ip_address": ipAddress["privateIpAddress"],
                             "is_virtual": "Yes",
                             "authenticated_scan_planned": "Yes",
                             "mac_address": nic["macAddress"],
                             "baseline_config": config_resource["configuration"]["imageId"],
                             "hardware_model": config_resource["configuration"]["instanceType"],
                             "network_id": config_resource["configuration"]["vpcId"],
                             "iir_diagram_label": _get_tag_value(config_resource["tags"], "iir_diagram_label"),
                             "owner": _get_tag_value(config_resource["tags"], "owner") }

                if (public_dns_name := config_resource["configuration"].get("publicDnsName")):
                    ec2_data["dns_name"] = public_dns_name
                    ec2_data["is_public"] = "Yes"
                else:
                    ec2_data["dns_name"] = config_resource["configuration"]["privateDnsName"]
                    ec2_data["is_public"] = "No"

                ec2_data_list.append(InventoryData(**ec2_data))

                if "association" in ipAddress:
                    # Each IP address needs its own row in report so public IP requires an additional row
                    ec2_data = copy.deepcopy(ec2_data)
                    ec2_data["ip_address"] = ipAddress["association"]["publicIp"]

                    ec2_data_list.append(InventoryData(**ec2_data))

        return ec2_data_list

class ElbDataMapper(DataMapper):
    def _get_supported_resource_type(self) -> List[str]:
        return ["AWS::ElasticLoadBalancing::LoadBalancer", "AWS::ElasticLoadBalancingV2::LoadBalancer"]

    def _get_asset_type_name(self, config_resource: dict) -> str:
        if config_resource["resourceType"] == "AWS::ElasticLoadBalancing::LoadBalancer":
            return "Load Balancer-Classic"
        else:
            lb_type = _sanitize_for_excel(config_resource.get('configuration', {}).get('type', 'unknown'))
            return f"Load Balancer-{lb_type}"

    def _get_ip_addresses(self, availabilityZones: dict) -> List[str]:
        ip_addresses: List[str] = []

        for availabilityZone in availabilityZones:
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
                 "is_public": "Yes" if config_resource.get("configuration", {}).get("scheme", "unknown") == "internet-facing" else "No",
                 # Classic ELBs have key of "vpcid" while V2 ELBs have key of "vpcId"
                 "network_id": config_resource["configuration"].get("vpcId") or config_resource["configuration"].get("vpcid") or "",
                 "iir_diagram_label": _get_tag_value(config_resource["tags"], "iir_diagram_label"),
                 "owner": _get_tag_value(config_resource["tags"], "owner") }

        if len(ip_addresses := self._get_ip_addresses(config_resource.get("configuration", {}).get("availabilityZones", []))) > 0:
            for ip_address in ip_addresses:
                data = copy.deepcopy(data)

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
                 "is_public": "Yes" if "publiclyAccessible" in config_resource["configuration"] and config_resource["configuration"]["publiclyAccessible"] else "No",                 
                 "hardware_model": config_resource["configuration"].get("dBInstanceClass", ""),                 
                 "software_product_name": f"{config_resource['configuration'].get('engine', 'unknown')}-{config_resource['configuration'].get('engineVersion', 'unknown')}",
                 "network_id": config_resource['configuration'].get('dBSubnetGroup', {}).get('vpcId', '') if "dBSubnetGroup" in config_resource['configuration'] else (config_resource['configuration'].get('dbsubnetGroup', {}).get('vpcId', '') if "dbsubnetGroup" in config_resource['configuration'] else ''),
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
