# Changelog

## [1.0.1] - 2026-02-16

### Changed
- Added execute permission to `quick-deploy-aggregator.sh` script
- Updated `templates/InventoryCollector-Aggregator.yml` to include standardized environment variables:
  - Added `REPORT_TARGET_BUCKET_NAME` environment variable
  - Added `REPORT_TARGET_BUCKET_PATH` environment variable set to `inventory-reports`

### Technical Details
- Environment variables now align with standard Lambda handler expectations
- Maintains backward compatibility with existing `REPORT_BUCKET` variable

## [1.0.2] - 2026-02-16

### Changed
- Updated Excel template to FedRAMP REV 4 format
- Updated column mappings to match REV 4 template structure (columns now start at B instead of A)
- Replaced `iir_diagram_label` field with `function` field to align with REV 4 template
- Updated all resource mappers to use `function` instead of `iir_diagram_label`

### Technical Details
- Template file replaced with REV_4_SSP-A13-FedRAMP-Integrated-Inventory-Workbook-Template.xlsx
- Column mappings shifted by 1 (e.g., UNIQUE_ID moved from col 1 to col 2)
- Function column now at position 19 (was Diagram Label at position 18)
