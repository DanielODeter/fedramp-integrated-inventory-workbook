#!/usr/bin/env python
# (c) 2019 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
# License: MIT-0
import json
import os
from botocore.exceptions import ClientError
from callee import String, Contains
from unittest.mock import Mock, MagicMock, ANY
import pytest
from inventory.mappers import DataMapper
from inventory.aggregator_reader import AwsConfigAggregatorInventoryReader

def setup_function():
    os.environ["CONFIG_AGGREGATOR_NAME"] = "TestAggregator"

def _make_reader(mappers=None, config_client=None):
    return AwsConfigAggregatorInventoryReader(
        lambda_context=MagicMock(),
        config_client=config_client or Mock(),
        mappers=mappers or []
    )

def _mock_config_client(pages):
    """Build a mock config client that returns the given list of page dicts."""
    client = Mock()
    client.select_aggregate_resource_config.side_effect = pages
    return client

def test_given_single_page_of_resources_then_all_are_processed():
    mock_mapper = Mock(spec=DataMapper)
    mock_mapper.can_map.return_value = True
    mock_mapper.map.return_value = [Mock()]

    client = _mock_config_client([
        {"Results": [json.dumps({"resourceType": "AWS::EC2::Instance"})], "NextToken": ""}
    ])
    reader = _make_reader(mappers=[mock_mapper], config_client=client)

    result = reader.get_resources_from_all_accounts()

    assert len(result) == 1
    mock_mapper.map.assert_called_once()

def test_given_multiple_pages_then_all_pages_are_consumed():
    mock_mapper = Mock(spec=DataMapper)
    mock_mapper.can_map.return_value = False

    client = _mock_config_client([
        {"Results": [json.dumps({"resourceType": "foobar"})], "NextToken": "page2"},
        {"Results": [json.dumps({"resourceType": "foobar"})], "NextToken": ""},
    ])
    reader = _make_reader(mappers=[mock_mapper], config_client=client)

    reader.get_resources_from_all_accounts()

    assert client.select_aggregate_resource_config.call_count == 2

def test_given_unsupported_resource_type_then_warning_logged_and_skipped():
    mock_mapper = Mock(spec=DataMapper)
    mock_mapper.can_map.return_value = False

    client = _mock_config_client([
        {"Results": [json.dumps({"resourceType": "AWS::Unknown::Resource"})], "NextToken": ""}
    ])
    reader = _make_reader(mappers=[mock_mapper], config_client=client)

    result = reader.get_resources_from_all_accounts()

    assert len(result) == 0

def test_given_client_error_then_exception_is_raised():
    client = Mock()
    client.select_aggregate_resource_config.side_effect = ClientError(
        error_response={"Error": {"Code": "AccessDeniedException"}},
        operation_name="select_aggregate_resource_config"
    )
    reader = _make_reader(config_client=client)

    with pytest.raises(ClientError):
        reader.get_resources_from_all_accounts()

def test_given_missing_aggregator_name_then_value_error_raised():
    del os.environ["CONFIG_AGGREGATOR_NAME"]
    reader = _make_reader()

    with pytest.raises(ValueError, match="CONFIG_AGGREGATOR_NAME"):
        reader.get_resources_from_all_accounts()
