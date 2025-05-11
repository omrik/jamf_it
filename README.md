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
   git clone https://github.com/your-username/jamf-app-usage.git
   ```

2. Install the required packages:
   ```bash
   pip install requests
   ```

3. Make the script executable:
   ```bash
   chmod +x jamf_app_usage.py
   ```

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

### Discovering Available Applications

## Usage

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
- Special thanks to [original script author or inspiration] for the initial idea
