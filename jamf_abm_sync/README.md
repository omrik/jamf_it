# Apple Business Manager to Jamf Pro Integration Suite

A comprehensive Python toolkit for synchronizing and comparing device purchase information between Apple Business Manager (ABM) and Jamf Pro. This suite provides both sync capabilities and read-only comparison tools for managing your Mac fleet.

## 🚀 Features

### Sync Script (`abm_jamf_sync.py`)
- **Automated Sync**: Fetches all devices from Apple Business Manager and updates corresponding records in Jamf Pro
- **Comprehensive Data Mapping**: Maps ABM purchase data to Jamf Pro purchasing fields
- **Test & Dry Run Modes**: Safe testing with limited devices and preview mode
- **Vendor Name Mapping**: Converts vendor IDs to readable company names

### Comparison Script (`abm_jamf_compare.py`)
- **Read-Only Analysis**: Compare purchase information without making changes
- **Missing Device Detection**: Identify devices in ABM but not in Jamf Pro
- **Difference Reporting**: Show mismatched purchase information between systems
- **Multiple Output Formats**: Clean tabulated display and CSV export with essential fields
- **Professional Reports**: Executive-ready summaries and detailed analysis

## 📋 Prerequisites

- Python 3.7+
- `requests` library
- Apple Business Manager account with API access
- Jamf Pro server with API access
- Shell scripts for token generation (see setup below)

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/omrik/jamf_it.git
   cd jamf_it/jamf_abm_sync
   ```

2. **Install dependencies**:
   ```bash
   pip install requests
   ```

3. **Set up token scripts and configuration** (see Configuration section below)

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
  "2341567": "Apple",
  "A7B9C2D": "TechSource Solutions",
  "F5E4A8B": "Global Systems Ltd",
  "X9Y2Z5K": "Premier IT Distributors"
}
```

This will display vendor names like "TechSource Solutions" instead of cryptic IDs like "A7B9C2D" in Jamf Pro. If the file is not found, vendor IDs will be used as-is.

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

**Note**: If `vendor_mapping.json` exists, vendor IDs will be converted to readable names (e.g., "A7B9C2D" → "TechSource Solutions"). Otherwise, the vendor ID will be used directly.

## 🚦 Usage

### Sync Script (`abm_jamf_sync.py`)

**Basic sync - updates all devices:**
```bash
python abm_jamf_sync.py
```

**Test & Debug Options:**
```bash
# Test mode - process only N devices
python abm_jamf_sync.py --test 2     # Process only 2 devices
python abm_jamf_sync.py --test 5     # Process only 5 devices
python abm_jamf_sync.py --test 10    # Process only 10 devices

# Dry run mode - show what would be updated without making changes
python abm_jamf_sync.py --dry-run

# Combined options - test with preview
python abm_jamf_sync.py --test 2 --dry-run

# Help
python abm_jamf_sync.py --help
```

### Comparison Script (`abm_jamf_compare.py`)

**Analysis Options:**
```bash
# Show purchase information differences (default)
python abm_jamf_compare.py
python abm_jamf_compare.py --diff

# Show devices in ABM but not in Jamf Pro
python abm_jamf_compare.py --missing

# Show both differences and missing devices
python abm_jamf_compare.py --all
```

**Export Options:**
```bash
# Export differences to CSV for spreadsheet analysis
python abm_jamf_compare.py --diff --output csv

# Export missing devices to CSV
python abm_jamf_compare.py --missing --output csv

# Export everything to CSV
python abm_jamf_compare.py --all --output csv
```

### Recommended Workflow

1. **First, analyze the current state:**
   ```bash
   python abm_jamf_compare.py --all --output csv
   ```

2. **Test sync on a few devices:**
   ```bash
   python abm_jamf_sync.py --test 5 --dry-run
   ```

3. **Run actual sync for testing:**
   ```bash
   python abm_jamf_sync.py --test 5
   ```

4. **Full sync when ready:**
   ```bash
   python abm_jamf_sync.py
   ```

## 📊 Output Examples

### Sync Script Output

**Test mode with dry run:**
```
2025-07-23 15:25:02,324 - INFO - TEST MODE: Processing only 2 devices
2025-07-23 15:25:02,324 - INFO - DRY RUN MODE: No actual updates will be made
2025-07-23 15:25:02,324 - INFO - Processing device 1/2: MXN8J2K9LM4P
2025-07-23 15:25:02,324 - INFO - DRY RUN: Would update computer ID 145
2025-07-23 15:25:02,324 - INFO - DRY RUN: Purchase data: {
  "purchased": true,
  "lifeExpectancy": 3,
  "warrantyDate": "2024-11-24",
  "vendor": "TechSource Solutions",
  "poDate": "2021-11-25",
  "poNumber": "PO-2021-78456"
}

=== SYNC COMPLETED ===
TEST MODE: Processed 2 of 187 devices
DRY RUN MODE: No actual changes were made
```

### Comparison Script Output

**Purchase differences (tabulated format):**
```
================================================================================
PURCHASE INFORMATION COMPARISON
================================================================================
📊 Summary:
  • Devices in sync: 45
  • Devices with differences: 8
  • Devices not in Jamf Pro: 3

Devices with purchase information differences:

Serial Number: MXN8J2K9LM4P (Computer ID: 145)
Model: MacBook Pro 13"
Field                ABM                       Jamf
----------------------------------------------------------------------
Purchased            Yes                       No
Vendor               TechSource Solutions      A7B9C2D
Po Number            PO-2021-78456             None
Warranty Date        2024-11-24               None
```

**Missing devices:**
```
================================================================================
DEVICES IN ABM BUT NOT IN JAMF PRO
================================================================================
Found 3 devices in ABM that are not in Jamf Pro:

Serial Number   Model                Added to Org  Order Number
--------------------------------------------------------------------------------
MXN8J2K9LM4P   MacBook Pro 13"      2021-11-25    PO-2021-78456
QR5T8W2X9Y3Z   MacBook Air 13"      2022-03-15    PO-2022-91234
VB7N4M8K6L2J   iMac 24"             2023-01-10    PO-2023-45678

📄 Detailed data exported to missing_devices.csv
```

## 🔧 API Requirements

### Apple Business Manager
- **Endpoint**: `https://api-business.apple.com/v1/orgDevices`
- **Authentication**: Bearer token
- **Permissions**: Read access to organization devices
- **Features**: Full pagination support for large device inventories

### Jamf Pro
- **Search Endpoint**: `/JSSResource/computers/serialnumber/{serial}` (Classic API)
- **Update Endpoint**: `/api/v1/computers-inventory-detail/{id}` (Modern API)
- **Authentication**: Bearer token
- **Permissions**: 
  - **Sync script**: Read and update computer inventory
  - **Compare script**: Read-only computer inventory access

## 🛡️ Security Considerations

- **Token Management**: Tokens are retrieved from external shell scripts, never hardcoded
- **API Rate Limiting**: Built-in rate limiting respects API guidelines
- **Error Handling**: Comprehensive error handling prevents data corruption
- **Logging**: Detailed logging for audit trails and troubleshooting
- **Read-Only Mode**: Comparison script requires no write permissions

## 🐛 Troubleshooting

### Common Issues

1. **"Exec format error"**: 
   - Ensure shell scripts have `#!/bin/bash` shebang and are executable
   - Run: `chmod +x get_abm_token.sh get_jamf_token.sh`

2. **"404 Not Found"**: 
   - Device exists in ABM but not in Jamf Pro (expected for comparison script)
   - Check Jamf Pro enrollment status

3. **"401 Unauthorized"**: 
   - Check token permissions and expiration
   - Verify script paths are correct

4. **"Failed to resolve hostname"**:
   - Check JAMF_SERVER_URL format: `https://company.jamfcloud.com`
   - Ensure no double `https://` in URL

5. **"Only getting 100 devices"**:
   - Check pagination logs for cursor information
   - Verify ABM token has access to all devices

### Debug Mode

Enable debug logging by changing the logging level in either script:
```python
logging.basicConfig(level=logging.DEBUG)
```

### Quick URL Fix

To quickly update the Jamf Pro URL in scripts:
```bash
# macOS/BSD sed
sed -i '' 's|https://your-jamf-server.com|https://company.jamfcloud.com|g' *.py

# Linux sed  
sed -i 's|https://your-jamf-server.com|https://company.jamfcloud.com|g' *.py
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- **Documentation**: Update README for any new features
- **Error Handling**: Include comprehensive error handling
- **Logging**: Add appropriate log messages for debugging
- **Testing**: Test with small datasets first (`--test` flag)
- **Comments**: Document complex logic and API interactions

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Apple Business Manager API documentation
- Jamf Pro API documentation  
- Python `requests` library maintainers
- macOS system administrators community

---

**⚠️ Important Notes:**
- Always test in a development environment before running in production
- The sync script modifies Jamf Pro data - use dry run mode first
- The comparison script is read-only and safe to run anytime
- Keep your API tokens secure and rotate them regularly
