# (c) 2019 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
# License:
# This sample code is made available under the MIT-0 license. See the LICENSE file.
import logging
from inventory.readers import AwsConfigInventoryReader
from inventory.reports import CreateReportCommandHandler, DeliverReportCommandHandler

_logger = logging.getLogger("inventory.handler")
_logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    try:
        _logger.info("Starting FedRAMP inventory collection")
        inventory = AwsConfigInventoryReader(lambda_context=context).get_resources_from_all_accounts()
        report_path = CreateReportCommandHandler().execute(inventory)
        report_url = DeliverReportCommandHandler().execute(report_path)
        
        _logger.info(f"Inventory collection completed successfully. Report: {report_url}")
        return {'statusCode': 200,
                'body': {
                        'report': { 'url': report_url }
                    }
                }
    except Exception as ex:
        _logger.error(f"Inventory collection failed: {ex}", exc_info=True)
        return {'statusCode': 500,
                'body': {
                        'error': 'Internal server error occurred'
                    }
                }

if __name__ == "__main__":
    class Context(object):
        def __init__(self):
            self.invoked_function_arn = "arn:aws-us-gov:lambda:us-east-1:123456789012:function:testing"

    result = lambda_handler(None, Context())

    print(result)
