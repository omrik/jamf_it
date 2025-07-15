# Jamf Pro IT Tools

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.6%2B-blue)](https://www.python.org/downloads/)

A collection of Python scripts for Jamf Pro administrators to analyze application usage and track software versions across managed devices. These tools help you make data-driven decisions about software deployment, licensing, and updates.

## 📊 Scripts Included

### 1. Application Usage Reporter

The `jamf_app_usage.py` script analyzes how frequently applications are used across your Jamf-managed computers.

**Key Features:**
- Retrieves application usage data (minutes of usage) for all computers or specific groups
- Reports which computers are using specific applications and for how long
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

### 3.  Apple Business Manager to Jamf Pro Device Sync

A Python script that synchronizes device purchase information from Apple Business Manager (ABM) to Jamf Pro, automatically updating purchasing details for all managed devices.

**Key Features:**
- **Automated Sync**: Fetches all devices from Apple Business Manager and updates corresponding records in Jamf Pro
- **Comprehensive Data Mapping**: Maps ABM purchase data to Jamf Pro purchasing fields
- **Robust Error Handling**: Handles API errors gracefully with detailed logging
- **Secure Token Management**: Uses external shell scripts for secure token retrieval
- **Modern API Support**: Uses the latest ABM API v1 and Jamf Pro API v1 endpoints
- **Detailed Reporting**: Provides comprehensive sync statistics and logging

## 📄 License

[MIT](https://github.com/omrik/jamf_it/blob/main/LICENSE)

## 👥 Contributing

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
