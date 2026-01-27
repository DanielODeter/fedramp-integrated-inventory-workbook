# (c) 2019 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
# License:
# This sample code is made available under the MIT-0 license. See the LICENSE file.
from datetime import datetime
import logging
import tempfile
import os, os.path
from typing import List
import boto3
from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet
from inventory.mappers import InventoryData

_logger = logging.getLogger("inventory.reports")
_logger.setLevel(getattr(logging, os.environ.get("LOG_LEVEL", "INFO"), logging.INFO))
_current_dir_name = os.path.dirname(__file__)
_workbook_template_file_name = os.path.join(_current_dir_name, "SSP-A13-FedRAMP-Integrated-Inventory-Workbook-Template.xlsx")
_workbook_output_file_path = os.path.join(tempfile.gettempdir(), "SSP-A13-FedRAMP-Integrated-Inventory.xlsx")
DEFAULT_REPORT_WORKSHEET_FIRST_WRITEABLE_ROW_NUMBER = 3

class CreateReportCommandHandler():
    def _write_cell_if_value_provided(self, worksheet: Worksheet, column:int, row: int, value: str):
        if value:
            worksheet.cell(column=column, row=row, value=value)

    def execute(self, inventory: List[InventoryData]) -> str:
        try:
            workbook = load_workbook(_workbook_template_file_name)
        except FileNotFoundError:
            _logger.error(f"Template file not found: {_workbook_template_file_name}")
            raise
        except Exception as e:
            _logger.error(f"Failed to load workbook template: {e}", exc_info=True)
            raise
        
        report_worksheet_name = os.environ.get("REPORT_WORKSHEET_NAME", "Inventory")
        report_worksheet = workbook[report_worksheet_name]
        rowNumber: int = int(os.environ.get("REPORT_WORKSHEET_FIRST_WRITEABLE_ROW_NUMBER", DEFAULT_REPORT_WORKSHEET_FIRST_WRITEABLE_ROW_NUMBER))

        _logger.info(f"writing {len(inventory)} rows into worksheet {report_worksheet_name} starting at row {rowNumber}")

        for inventory_row in inventory:
            self._write_cell_if_value_provided(report_worksheet, 1, rowNumber, inventory_row.unique_id)
            self._write_cell_if_value_provided(report_worksheet, 2, rowNumber, inventory_row.ip_address)
            self._write_cell_if_value_provided(report_worksheet, 3, rowNumber, inventory_row.is_virtual)
            self._write_cell_if_value_provided(report_worksheet, 4, rowNumber, inventory_row.is_public)
            self._write_cell_if_value_provided(report_worksheet, 5, rowNumber, inventory_row.dns_name)
            self._write_cell_if_value_provided(report_worksheet, 7, rowNumber, inventory_row.mac_address)
            self._write_cell_if_value_provided(report_worksheet, 8, rowNumber, inventory_row.authenticated_scan_planned)
            self._write_cell_if_value_provided(report_worksheet, 9, rowNumber, inventory_row.baseline_config)
            self._write_cell_if_value_provided(report_worksheet, 12, rowNumber, inventory_row.asset_type)
            self._write_cell_if_value_provided(report_worksheet, 13, rowNumber, inventory_row.hardware_model)
            self._write_cell_if_value_provided(report_worksheet, 15, rowNumber, inventory_row.software_vendor)
            self._write_cell_if_value_provided(report_worksheet, 16, rowNumber, inventory_row.software_product_name)
            self._write_cell_if_value_provided(report_worksheet, 18, rowNumber, inventory_row.iir_diagram_label)
            self._write_cell_if_value_provided(report_worksheet, 21, rowNumber, inventory_row.network_id)
            self._write_cell_if_value_provided(report_worksheet, 22, rowNumber, inventory_row.owner)

            rowNumber += 1

        workbook.save(_workbook_output_file_path)

        _logger.info(f"completed saving inventory into {_workbook_output_file_path}")

        return _workbook_output_file_path

class DeliverReportCommandHandler():
    def __init__(self, s3_client=boto3.client('s3')):
        self._s3_client = s3_client

    def execute(self, report_file_name: str) -> str:
        target_path = os.environ.get("REPORT_TARGET_BUCKET_PATH")
        target_bucket = os.environ.get("REPORT_TARGET_BUCKET_NAME")
        
        if not target_path or not target_bucket:
            raise ValueError("REPORT_TARGET_BUCKET_PATH and REPORT_TARGET_BUCKET_NAME environment variables are required")
        
        report_filename = os.path.basename(_workbook_output_file_path)
        report_stem = os.path.splitext(report_filename)[0]
        report_s3_key = os.path.join(target_path, f"{report_stem}-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.xlsx")

        # Validate file path to prevent path traversal
        if os.path.abspath(report_file_name) != os.path.abspath(_workbook_output_file_path):
            raise ValueError(f"Invalid report file path: {report_file_name}")
        
        _logger.info(f"uploading file '{report_file_name}' to bucket '{target_bucket}' with key '{report_s3_key}'")

        with open(report_file_name, "rb") as object_data:
            self._s3_client.put_object(Bucket=target_bucket, Key=report_s3_key, Body=object_data)

        _logger.info(f"completed file upload")

        return f"https://{target_bucket}.s3.amazonaws.com/{report_s3_key}"