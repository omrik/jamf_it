# Apple Business Manager to Jamf Pro Device Sync

A Python script that synchronizes device purchase information from Apple Business Manager (ABM) to Jamf Pro, automatically updating purchasing details for all managed devices.

## 🚀 Features

- **Automated Sync**: Fetches all devices from Apple Business Manager and updates corresponding records in Jamf Pro
- **Comprehensive Data Mapping**: Maps ABM purchase data to Jamf Pro purchasing fields
- **Robust Error Handling**: Handles API errors gracefully with detailed logging
- **Secure Token Management**: Uses external shell scripts for secure token retrieval
- **Modern API Support**: Uses the latest ABM API v1 and Jamf Pro API v1 endpoints
- **Detailed Reporting**: Provides comprehensive sync statistics and logging

## 📋 Prerequisites

- Python 3.7+
- `requests` library
- Apple Business Manager account with API access
- Jamf Pro server with API access
- Shell scripts for token generation (see setup below)

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/abm-jamf-sync.git
   cd abm-jamf-sync
   ```

2. **Install dependencies**:
   ```bash
   pip install requests
   ```

3. **Set up token scripts** (see Configuration section below)

## ⚙️ Configuration

### 1. Update Server URL

Edit the `JAMF_SERVER_URL` in the `main()` function:
```python
JAMF_SERVER_URL = "https://your-jamf-server.com"
```

### 2. Create Token Scripts

Create two executable shell scripts in the same directory:

**`get_abm_token.sh`** - Apple Business Manager token:
```bash
#!/bin/bash
# Your ABM token retrieval logic here
echo "your_abm_server_token_here"
```

**`get_jamf_token.sh`** - Jamf Pro token:
```bash
#!/bin/bash
# Example Jamf Pro token retrieval
curl -s -u "$JAMF_USER:$JAMF_PASS" \
  "$JAMF_URL/api/v1/auth/token" \
  -H "Accept: application/json" | \
  jq -r '.token'
```

### 4. Create Vendor Mapping (Optional)

Create a `vendor_mapping.json` file to map vendor IDs to readable names:

```json
{
  "1210895": "Apple",
  "64AFCB0": "AMIRIM",
  "37E8FF0": "WEDIGGIT LTD",
  "4C90610": "ESPIRCOM SYSTEMS LTD"
}
```

This will display vendor names like "AMIRIM" instead of cryptic IDs like "64AFCB0" in Jamf Pro. If the file is not found, vendor IDs will be used as-is.

```bash
chmod +x get_abm_token.sh
chmod +x get_jamf_token.sh
```

## 🔄 Data Mapping

The script maps the following fields from ABM to Jamf Pro:

| Apple Business Manager | Jamf Pro Field | Description |
|------------------------|----------------|-------------|
| `serialNumber` | Search key | Used to find device in Jamf Pro |
| `addedToOrgDateTime` | `poDate` | Purchase order date |
| `addedToOrgDateTime + 3 years` | `warrantyDate` | Calculated warranty expiration |
| `orderNumber` | `poNumber` | Purchase order number |
| `purchaseSourceId` | `vendor` | Vendor name (mapped via vendor_mapping.json) |
| N/A | `purchased` | Always set to `true` |
| N/A | `lifeExpectancy` | Always set to `3` years |

**Note**: If `vendor_mapping.json` exists, vendor IDs will be converted to readable names (e.g., "64AFCB0" → "AMIRIM"). Otherwise, the vendor ID will be used directly.

## 🚦 Usage

### Basic Usage

```bash
python abm_jamf_sync.py
```

### Command Line Options

The script supports several command-line options for testing and debugging:

```bash
# Test mode - process only N devices
python abm_jamf_sync.py --test 2     # Process only 2 devices
python abm_jamf_sync.py --test 5     # Process only 5 devices
python abm_jamf_sync.py --test 10    # Process only 10 devices

# Dry run mode - show what would be updated without making changes
python abm_jamf_sync.py --dry-run

# Combined options
python abm_jamf_sync.py --test 2 --dry-run

# Help
python abm_jamf_sync.py --help
```

### Test Mode Output

When using `--test N`, the script will:
- Process only the first N devices from ABM
- Show progress as "Processing device X/N"
- Display a clear indication that it's in test mode
- Report how many devices were processed vs. total available

Example output:
```
2025-07-15 12:19:31,773 - INFO - TEST MODE: Processing only 2 devices
2025-07-15 12:19:31,773 - INFO - Processing device 1/2: C02G2034ML88
2025-07-15 12:19:34,416 - INFO - Processing device 2/2: C02H4567ML99
2025-07-15 12:19:35,500 - INFO - TEST MODE: Stopping after 2 devices
=== SYNC COMPLETED ===
TEST MODE: Processed 2 of 100 devices
```

## 📊 Output

The script provides detailed logging and a final summary:

```
2025-07-15 12:19:31,773 - INFO - Starting device sync process...
2025-07-15 12:19:31,773 - INFO - Loaded 4 vendor mappings from vendor_mapping.json
2025-07-15 12:19:31,773 - INFO - Processing device: C02G2034ML88
2025-07-15 12:19:34,416 - INFO - Updating computer ID 70 with purchase data: {'purchased': True, 'lifeExpectancy': 3, 'warrantyDate': '2024-11-24', 'vendor': 'AMIRIM', 'poDate': '2021-11-25', 'poNumber': '411469852-49285488'}
2025-07-15 12:19:34,984 - INFO - Successfully updated computer ID 70

=== SYNC COMPLETED ===
Total ABM devices: 100
Found in Jamf Pro: 95
Updated successfully: 95
Failed updates: 0
Not found in Jamf Pro: 5
```

### Test Mode Output

When using `--test N`, additional information is shown:
```
2025-07-15 12:19:31,773 - INFO - TEST MODE: Processing only 2 devices
2025-07-15 12:19:31,773 - INFO - Processing device 1/2: C02G2034ML88
2025-07-15 12:19:34,416 - INFO - Processing device 2/2: C02H4567ML99
2025-07-15 12:19:35,500 - INFO - TEST MODE: Stopping after 2 devices
=== SYNC COMPLETED ===
TEST MODE: Processed 2 of 100 devices
```

## 🔧 API Requirements

### Apple Business Manager
- **Endpoint**: `https://api-business.apple.com/v1/orgDevices`
- **Authentication**: Bearer token
- **Permissions**: Read access to organization devices

### Jamf Pro
- **Search Endpoint**: `/JSSResource/computers/serialnumber/{serial}` (Classic API)
- **Update Endpoint**: `/api/v1/computers-inventory-detail/{id}` (Modern API)
- **Authentication**: Bearer token
- **Permissions**: Read and update computer inventory

## 🛡️ Security Considerations

- **Token Management**: Tokens are retrieved from external shell scripts, never hardcoded
- **API Rate Limiting**: The script includes built-in rate limiting for API calls
- **Error Handling**: Comprehensive error handling prevents data corruption
- **Logging**: Detailed logging for audit trails and troubleshooting

## 🐛 Troubleshooting

### Common Issues

1. **"Exec format error"**: Ensure shell scripts have `#!/bin/bash` shebang and are executable
2. **"404 Not Found"**: Device exists in ABM but not in Jamf Pro (expected behavior)
3. **"415 Unsupported Media Type"**: Using wrong API version (script uses correct v1 API)
4. **"401 Unauthorized"**: Check token permissions and expiration

### Debug Mode

Enable debug logging by changing the logging level:
```python
logging.basicConfig(level=logging.DEBUG)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Apple Business Manager API documentation
- Jamf Pro API documentation
- Python `requests` library maintainers

## 📞 Support

If you encounter any issues or have questions:

1. Check the [Issues](https://github.com/yourusername/abm-jamf-sync/issues) page
2. Create a new issue with detailed information
3. Include log output and error messages

---

**Note**: This script is provided as-is. Always test in a development environment before running in production.
