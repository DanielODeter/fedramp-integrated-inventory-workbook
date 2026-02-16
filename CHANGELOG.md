# Changelog

## [1.0.1] - 2025-01-15

### Changed
- Added execute permission to `quick-deploy-aggregator.sh` script
- Updated `templates/InventoryCollector-Aggregator.yml` to include standardized environment variables:
  - Added `REPORT_TARGET_BUCKET_NAME` environment variable
  - Added `REPORT_TARGET_BUCKET_PATH` environment variable set to `inventory-reports`

### Technical Details
- Environment variables now align with standard Lambda handler expectations
- Maintains backward compatibility with existing `REPORT_BUCKET` variable
