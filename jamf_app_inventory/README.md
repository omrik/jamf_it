# Jamf Pro App Inventory

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.6%2B-blue)](https://www.python.org/downloads/)

A collection of Python scripts for Jamf Pro administrators to analyze application usage and track software versions across managed devices. These tools help you make data-driven decisions about software deployment, licensing, and updates.

## 📊 Scripts Included

### 1. Application Usage Reporter

The application usage reporter consists of two main files:
- **`jamf_api_client.py`** - Robust API client library with token management, rate limiting, and error recovery
- **`jamf_app_usage.py`** - Enhanced usage reporter with batch processing and resume capabilities

**Key Features:**
- Retrieves application usage data (minutes of usage) for all computers or specific groups
- Reports which computers are using specific applications and for how long
- Automatic token refresh for long-running operations
- Rate limiting to avoid overwhelming the Jamf API
- Progress saving and resume capability for large environments
- Supports both username/password and token-based authentication
- Auto-generates descriptive filenames for reports
- Offers flexible app name matching for finding the right application

### 2. Application Inventory Tracker

The `jamf_app_inventory.py` script provides a comprehensive inventory of installed applications and identifies outdated versions.

**Key Features:**
- Creates a one-line-per-app summary showing version distribution
- Automatically determines the latest version of each application
- Identifies computers with outdated software that needs updating
- Works without requiring an external reference for latest versions
- Generates clear reports for application auditing and update planning

## 🖥️ Screenshots

<details>
<summary>Click to view screenshots</summary>

<img width="812" alt="Screenshot of app report" src="https://github.com/user-attachments/assets/ea1a00f4-f656-49d2-ad97-156e685729ec" />

<img width="812" alt="Screenshot of outdated computers" src="https://github.com/user-attachments/assets/387759d2-fb71-41c8-81b7-cbb81a601fac" />

</details>

## 🔧 Requirements

- Python 3.6 or higher
- Required Python packages: `requests`
- A Jamf Pro instance with API access
- For token authentication: a working `jamf_get_token.sh` script that outputs a valid API token

## 🚀 Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/omrik/jamf_it.git
   cd jamf_it/jamf_app_inventory
   ```

2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Make the scripts executable:
   ```bash
   chmod +x jamf_app_usage.py jamf_app_inventory.py
   ```

4. (Optional) For token authentication, create a `jamf_get_token.sh` script using the provided example:
   ```bash
   cp jamf_get_token.sh.example jamf_get_token.sh
   chmod +x jamf_get_token.sh
   ```

## 🔐 API Authentication

### Setting Up API Access in Jamf Pro

To use these scripts, you'll need to set up API access in your Jamf Pro instance using API Roles and Clients:

1. Log in to your Jamf Pro instance as an administrator
2. Navigate to **Settings** > **System Settings** > **API Roles and Clients**
3. First, create a role by clicking the "New Role" button
4. Fill in the following details:
   - **Display Name**: Choose a descriptive name (e.g., "Admin Tools Reporter")
   - **Privileges**: Assign the following minimum permissions:
     - **Classic API**: ✓ Read (required for these scripts)
     - **Computers**: ✓ Read
     - **Computer Extension Attributes**: ✓ Read 
     - **Static Computer Groups**: ✓ Read
     - **Smart Computer Groups**: ✓ Read
   - Click **Save** to create the role

5. Next, create a client by clicking the "New Client" button
6. Fill in the following details:
   - **Display Name**: A descriptive name (e.g., "Admin Tools Client")
   - **Client ID**: Auto-generated or specify your own
   - **Access Token Lifetime**: Set an appropriate duration (default is 30 minutes)
   - **Authorization Scopes**: Select the role you just created
7. Click **Save** to create the client
8. Note down your **Client ID** and **Client Secret** - you'll need these for authentication

### Secure Token Authentication

For token-based authentication, create a script named `jamf_get_token.sh` that uses environment variables to securely retrieve a token:

```bash
#!/bin/bash
# Check if required environment variables are set
if [ -z "$JAMF_URL" ] || [ -z "$JAMF_CLIENT_ID" ] || [ -z "$JAMF_CLIENT_SECRET" ]; then
    echo "Error: Missing environment variables" >&2
    exit 1
fi

# Get the token using client credentials
TOKEN=$(curl -s -X POST "$JAMF_URL/api/v1/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=$JAMF_CLIENT_ID&client_secret=$JAMF_CLIENT_SECRET" \
  | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# Output the token (this will be captured by the Python script)
echo "$TOKEN"
```

To use token authentication, set your environment variables and use the `-t` flag with the scripts:

```bash
export JAMF_URL="https://your-instance.jamfcloud.com"
export JAMF_CLIENT_ID="your-client-id"
export JAMF_CLIENT_SECRET="your-super-secret-key"
```

## 📋 Usage

### Application Usage Reporter

```bash
# Basic usage - shows usage for a specific application
./jamf_app_usage.py -a "Microsoft Word.app" -s "https://your-instance.jamfcloud.com" -u username -p password

# Find all used applications first
./jamf_app_usage.py --list-apps -s "https://your-instance.jamfcloud.com" -u username -p password

# Token authentication and filter by group
./jamf_app_usage.py -a "Slack.app" -t -g "Marketing"

# Debug mode for troubleshooting
./jamf_app_usage.py -a "Adobe Photoshop.app" -t --debug

# Resume from previous progress (for large environments)
./jamf_app_usage.py -a "Microsoft Excel.app" -t --resume

# Batch processing with custom settings
./jamf_app_usage.py -a "AutoCAD.app" -t --batch-size 25 --delay 1.0
```

### Application Inventory Tracker

```bash
# Basic usage - lists all applications and finds outdated versions
./jamf_app_inventory.py -s "https://your-instance.jamfcloud.com" -u username -p password

# Focus on applications with at least 3 different versions
./jamf_app_inventory.py -t -g "Finance" --min-version-count 3

# Custom output file naming
./jamf_app_inventory.py -t -g "Engineering" -o "eng_inventory"
```

## 📄 Output Examples

### Application Usage Report

The usage report shows which computers are using specific applications and for how long:

```
Computer ID,Computer Name,Serial Number,Application,Total Minutes,Days Used,Average Minutes Per Day,Date Range
42,MARKETING-01,C02XYZ123ABC,Microsoft Word.app,437,12,36.42,2023-05-01 to 2023-06-01
67,FINANCE-03,C02XYZ456DEF,Microsoft Word.app,1205,18,66.94,2023-05-01 to 2023-06-01
```

### Applications Summary Report

The inventory summary shows one line per application with version distribution:

```
Application,Version Count,Newest Version,Oldest Version,Total Installations,Computers with Latest Version,Computers with Outdated Versions
Adobe Acrobat Reader,3,23.006.20320,21.001.20145,45,12,33
Google Chrome,2,115.0.5790.170,114.0.5735.198,67,54,13
Microsoft Word,4,16.74.0,16.62.0,50,20,30
```

### Outdated Computers Report

The outdated computers report identifies which computers need updates:

```
Computer Name,Serial Number,OS Version,Last Inventory Update,Outdated Apps Count,Outdated Applications
FINANCE-MBP-01,C02XYZ123ABC,13.2.1,2023-06-01,2,Adobe Acrobat Reader (installed 21.001.20145 < latest 23.006.20320); Microsoft Word (installed 16.62.0 < latest 16.74.0)
IT-MBP-03,C02XYZ456DEF,13.3.1,2023-06-05,1,Google Chrome (installed 114.0.5735.198 < latest 115.0.5790.170)
```

## 📊 Example Workflows

### Software License Optimization

1. Run the usage reporter to identify rarely-used software:
   ```bash
   ./jamf_app_usage.py -a "ExpensiveSoftware.app" -t
   ```

2. Analyze the results to find computers where the software is rarely used
3. Consider reclaiming licenses or implementing a license-sharing approach

### Update Compliance Reporting

1. Generate an inventory report to find outdated applications:
   ```bash
   ./jamf_app_inventory.py -t -g "Marketing"
   ```

2. Identify computers with outdated software that needs patching
3. Create a targeted Smart Group in Jamf Pro for deploying updates

### Batch Reporting

Use the example scripts in the `examples` directory to generate reports for multiple applications or groups at once:

```bash
cd examples
./batch_app_inventory.sh
```

## 🏗️ Architecture

### Modular Design

The application usage reporter uses a modular architecture:

- **`jamf_api_client.py`** - Core API client library that handles:
  - Authentication (both basic auth and token-based)
  - Automatic token refresh for long-running operations
  - Rate limiting and retry logic
  - Error handling and recovery
  
- **`jamf_app_usage.py`** - Main script that uses the API client for:
  - Batch processing of large computer inventories
  - Progress tracking and resume capability
  - Flexible application name matching
  - CSV report generation

This modular approach makes the code more maintainable and allows for better error handling in large environments.

## 📂 Project Structure

```
jamf_it/
├── jamf_app_inventory/              # Main project directory
│   ├── jamf_app_usage.py     # Enhanced usage reporter script
│   ├── jamf_api_client.py           # Core API client library
│   ├── jamf_app_inventory.py        # Application inventory tracker script
│   ├── README.md                    # This documentation
│   ├── requirements.txt             # Python package dependencies
│   ├── LICENSE                      # MIT license
│   ├── .gitignore                   # Git ignore configuration
│   ├── jamf_get_token.sh.example    # Template for token authentication
│   ├── examples/                    # Example batch scripts
│   │   ├── batch_app_inventory.sh   # Run inventory for multiple groups
│   │   └── generate_usage_report.sh # Generate usage reports for multiple apps
│   └── reports/                     # Generated reports (gitignored)
└── other_projects/                  # Other jamf_it projects
```

## 🛠️ Troubleshooting

If you encounter issues:

1. **API Authentication Problems**
   - Verify your API credentials have the correct permissions
   - Check that your Jamf Pro instance supports the Classic API
   - Try using the `--debug` flag to see detailed API responses

2. **Import Errors**
   - Make sure you have `import os` and `import time` in your script imports
   - Verify that `jamf_api_client.py` is in the same directory as your main script
   - Check that all required packages are installed: `pip install -r requirements.txt`

3. **Version Comparison Issues**
   - If applications have unusual version formats, check the debug output
   - Look for error messages during the version sorting process

4. **Missing Data**
   - Ensure computers have recent inventory updates in Jamf Pro
   - Check that application usage tracking is enabled in your Jamf Pro instance

5. **Large Environment Performance**
   - Use the `--batch-size` parameter to adjust processing batches
   - Increase `--delay` between API calls if you're hitting rate limits
   - Use `--resume` to continue from where you left off if the script is interrupted

## 📄 License

[MIT](https://github.com/omrik/jamf_it/blob/main/LICENSE)

## 💥 Contributing

Contributions are welcome! Please feel free to submit a pull request or open issues on the [GitHub repository](https://github.com/omrik/jamf_it/issues).

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📱 Related Projects

- [Jamf Pro API Python Wrapper](https://github.com/bweber/jamf-pro-api-python)
- [python-jss](https://github.com/jssimporter/python-jss)
- [jamJAR](https://github.com/dataJAR/jamJAR)

---

Made with ❤️ by [Omri](https://github.com/omrik)
