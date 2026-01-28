# (c) 2019 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
# License:
# This sample code is made available under the MIT-0 license. See the LICENSE file.
import logging
import json
import os
from inventory.readers import AwsConfigInventoryReader
from inventory.aggregator_reader import AwsConfigAggregatorInventoryReader
from inventory.reports import CreateReportCommandHandler, DeliverReportCommandHandler

_logger = logging.getLogger("inventory.handler")
_logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    try:
        _logger.info("Starting FedRAMP inventory collection")
        
        # Choose reader based on deployment type
        use_aggregator = os.environ.get('USE_AGGREGATOR', 'false').lower() == 'true'
        
        if use_aggregator:
            _logger.info("Using Config Aggregator reader")
            inventory = AwsConfigAggregatorInventoryReader(lambda_context=context).get_resources_from_all_accounts()
        else:
            _logger.info("Using cross-account reader")
            inventory = AwsConfigInventoryReader(lambda_context=context).get_resources_from_all_accounts()
        
        report_path = CreateReportCommandHandler().execute(inventory)
        report_url = DeliverReportCommandHandler().execute(report_path)
        
        _logger.info(f"Inventory collection completed successfully. Report: {report_url}")
        return {'statusCode': 200,
                'body': json.dumps({
                        'report': { 'url': report_url }
                    })
                }
    except Exception as ex:
        _logger.error(f"Inventory collection failed: {ex}", exc_info=True)
        return {'statusCode': 500,
                'body': json.dumps({
                        'error': 'Internal server error occurred'
                    })
                }

if __name__ == "__main__":
    class Context(object):
        def __init__(self):
            self.invoked_function_arn = "arn:aws-us-gov:lambda:us-east-1:123456789012:function:testing"

    result = lambda_handler(None, Context())

    print(result)
