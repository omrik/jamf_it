# Jamf Application Usage Reporter

A Python script that retrieves application usage data from the Jamf Pro API and generates comprehensive CSV reports showing the amount of minutes each computer has used a specific application.

## Features

- Retrieves application usage data for all computers or specific computer groups
- Shows total minutes of usage per computer
- Includes serial numbers, device names, and other relevant information
- Supports both username/password and token-based authentication
- Auto-generates descriptive filenames for reports
- Provides a discovery mode to list all applications found in usage data
- Offers flexible app name matching
- Includes debug mode for troubleshooting

## Requirements

- Python 3.6 or higher
- Required Python packages: `requests`
- A Jamf Pro instance with API access
- For token authentication: a working `jamf_get_token.sh` script that outputs a valid API token

## Installation

1. Clone this repository or download the script:
   ```bash
   git clone https://github.com/omrik/jamf-it.git
   ```

2. Install the required packages:
   ```bash
   pip install requests
   ```

3. Make the script executable:
   ```bash
   chmod +x jamf_app_usage.py
   ```

## API Authentication & Permissions

### Setting Up API Access in Jamf Pro

To use this script, you'll need to set up API access in your Jamf Pro instance using API Roles and Clients:

#### Creating API Roles and Clients

1. Log in to your Jamf Pro instance as an administrator
2. Navigate to **Settings** > **System Settings** > **API Roles and Clients**
3. First, create a role by clicking the "New Role" button
4. Fill in the following details:
   - **Display Name**: Choose a descriptive name (e.g., "Application Usage Reporter")
   - **Privileges**: Assign the following minimum permissions:
     - **Classic API**: ✓ Read (required for this script)
     - **Computers**: ✓ Read
     - **Computer Extension Attributes**: ✓ Read 
     - **Static Computer Groups**: ✓ Read
     - **Smart Computer Groups**: ✓ Read
     - **Users**: ✓ Read
     - **Computer Reports**: ✓ Read
   - Click **Save** to create the role

5. Next, create a client by clicking the "New Client" button
6. Fill in the following details:
   - **Display Name**: A descriptive name (e.g., "Application Usage Client")
   - **Client ID**: Auto-generated or specify your own
   - **Access Token Lifetime**: Set an appropriate duration (default is 30 minutes)
   - **Authorization Scopes**: Select the role you just created
7. Click **Save** to create the client
8. Note down your **Client ID** and **Client Secret** - you'll need these for authentication

#### Authentication Methods

This script supports two authentication methods:

##### 1. Username/Password Authentication (Legacy)

If your Jamf Pro instance still supports basic authentication with the Classic API, you can use the `-u` and `-p` parameters:

```bash
./jamf_app_usage.py -a "Chrome" -s "https://your-instance.jamfcloud.com" -u "username" -p "password"
```

##### 2. Token-Based Authentication (Recommended)

For more secure token-based authentication, you can create a script (`jamf_get_token.sh`) that obtains a valid token using environment variables:

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

To use token authentication:

1. Set your environment variables:
   ```bash
   export JAMF_URL="https://your-instance.jamfcloud.com"
   export JAMF_CLIENT_ID="your-client-id"
   export JAMF_CLIENT_SECRET="your-super-secret-key"
   ```

2. Make the script executable:
   ```bash
   chmod +x jamf_get_token.sh
   ```

3. Run the application usage script with the `-t` flag:
   ```bash
   ./jamf_app_usage.py -a "Chrome" -t
   ```

This approach keeps your credentials secure by never storing them in plaintext in the script.

### Security Best Practices

1. **Use Environment Variables**: Store sensitive credentials as environment variables instead of hardcoding them.
2. **Least Privilege**: Create API clients with only the necessary permissions.
3. **Rotate Client Secrets**: Regularly update your client secrets.
4. **Limited Token Lifetime**: Set appropriate token lifetimes based on your usage patterns.
5. **Audit API Usage**: Periodically review API activity in Jamf Pro logs.
6. **Secure Storage**: Consider using a password manager or secret management service for storing credentials.

### Troubleshooting Authentication Issues

If you encounter authentication problems:

1. **Check Environment Variables**: Ensure all required environment variables are set correctly.
2. **Check Permissions**: Verify the API client has the appropriate privileges listed above.
3. **API Access Enabled**: Ensure API access is enabled in your Jamf Pro instance.
4. **Network Access**: Make sure your system can access the Jamf Pro API endpoints.
5. **Token Expiration**: If using token authentication, ensure your token is not expired.
6. **Legacy API Support**: If using username/password, confirm the Classic API still allows this authentication method in your Jamf Pro version.

## Usage

### Basic Usage

```bash
# Search for a specific app usage across all computers
./jamf_app_usage.py -a "Google Chrome.app" -s "https://your-instance.jamfcloud.com" -u username -p password

# Filter by computer group
./jamf_app_usage.py -a "Microsoft Word.app" -g "Finance Department" -s "https://your-instance.jamfcloud.com" -u username -p password

# Specify a custom output filename
./jamf_app_usage.py -a "Slack.app" -o custom_report.csv -s "https://your-instance.jamfcloud.com" -u username -p password

# Look back at 60 days of usage data instead of the default 30
./jamf_app_usage.py -a "Adobe Photoshop.app" -d 60 -s "https://your-instance.jamfcloud.com" -u username -p password
```


### Listing Available Applications

To discover what applications are available in your Jamf usage data:

```bash
# List all applications with their usage minutes
./jamf_app_usage.py --list-apps -s "https://your-instance.jamfcloud.com" -u username -p password
```

This shows all applications found in the usage data from the first 5 computers, sorted by total minutes used.

### Analyzing Specific Application Usage

Once you know which application you want to analyze:

```bash
# Basic usage - search for a specific app
./jamf_app_usage.py -a "Microsoft Word.app" -s "https://your-instance.jamfcloud.com" -u username -p password

# Filter by computer group
./jamf_app_usage.py -a "Google Chrome.app" -g "Marketing" -s "https://your-instance.jamfcloud.com" -u username -p password

# Look back at more days of data
./jamf_app_usage.py -a "Slack.app" -d 90 -s "https://your-instance.jamfcloud.com" -u username -p password

# Specify a custom output filename
./jamf_app_usage.py -a "Safari.app" -o safari_report.csv -s "https://your-instance.jamfcloud.com" -u username -p password
```

### Token Authentication

If you have a script that retrieves API tokens:

```bash
# Use token authentication instead of username/password
./jamf_app_usage.py -a "Adobe Photoshop.app" -t -s "https://your-instance.jamfcloud.com"
```

This expects a script named `jamf_get_token.sh` in the same directory that outputs a valid API token.

### Troubleshooting

If you're having issues, use the debug mode:

```bash
# Enable debug mode for verbose output
./jamf_app_usage.py -a "Microsoft Excel.app" --debug -s "https://your-instance.jamfcloud.com" -u username -p password

# Skip SSL certificate verification (not recommended for production)
./jamf_app_usage.py -a "Keynote.app" --insecure -s "https://your-instance.jamfcloud.com" -u username -p password
```

## Output

The script generates a CSV file with the following information for each computer:
- Computer ID
- Computer Name
- Serial Number
- Application
- Total Minutes (total usage in minutes)
- Days Used (number of days the application was used)
- Average Minutes Per Day
- Date Range

### Auto-generated Filenames

If you don't specify an output filename with `-o`, the script will create a descriptive filename based on:
- The application name
- The computer group name (if specified)
- The number of days searched
- The current date

Example: `Microsoft_Word_Finance_Department_30days_2023-05-11.csv`

## How It Works

This script uses the Jamf Pro Classic API to:
1. Fetch a list of computers (all or filtered by group)
2. Retrieve serial numbers for each computer
3. Query the `/computerapplicationusage/serialnumber` endpoint for each computer
4. Parse the XML response to extract application usage data
5. Filter for the specified application (with flexible name matching)
6. Calculate total and average usage minutes
7. Output the results to a CSV file

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

- Thanks to the Jamf community for their valuable insights into the API
- Special thanks to https://github.com/jp-cpe/check-application-usage for the initial idea
