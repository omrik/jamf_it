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

### 3. Make Scripts Executable

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
| `purchaseSourceId` | `vendor` | Vendor identifier |
| N/A | `purchased` | Always set to `true` |
| N/A | `lifeExpectancy` | Always set to `3` years |

## 🚦 Usage

### Basic Usage

```bash
python abm_jamf_sync.py
```

### Testing with Limited Devices

For testing, you can modify the sync loop to process only a few devices:

```python
# In the sync_devices function, add this after the for loop:
for i, device in enumerate(abm_devices):
    if i >= 2:  # Stop after 2 devices for testing
        logger.info("Test mode: Stopping after 2 devices")
        break
    # ... rest of loop continues
```

### Dry Run Mode

To see what would be updated without making changes:

```python
# Add this flag at the top of sync_devices function:
DRY_RUN = True  # Set to False for actual updates

# Then in the update section:
if DRY_RUN:
    logger.info(f"DRY RUN: Would update computer ID {computer_id} with: {purchase_data}")
    updated_successfully += 1
else:
    if update_jamf_computer(computer_id, purchase_data, jamf_token, jamf_server_url):
        updated_successfully += 1
```

## 📊 Output

The script provides detailed logging and a final summary:

```
2025-07-15 12:19:31,773 - INFO - Processing device: C02G2034ML88
2025-07-15 12:19:34,416 - INFO - Updating computer ID 70 with purchase data: {'purchased': True, 'lifeExpectancy': 3, 'warrantyDate': '2024-11-24', 'vendor': '64AFCB0', 'poDate': '2021-11-25', 'poNumber': '411469852-49285488'}
2025-07-15 12:19:34,984 - INFO - Successfully updated computer ID 70

=== SYNC COMPLETED ===
Total ABM devices: 100
Found in Jamf Pro: 95
Updated successfully: 95
Failed updates: 0
Not found in Jamf Pro: 5
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
