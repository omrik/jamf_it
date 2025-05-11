#!/usr/bin/env python3
"""
Jamf Application Inventory and Update Checker

This script retrieves a complete inventory of applications installed on computers managed by Jamf Pro,
identifies outdated versions, and outputs the results to CSV files in a useful format.

Reports Generated:
1. Applications Summary: One app per line with version count, newest version, oldest version
2. Outdated Computers: List of computers that don't have the latest version of installed apps

Key Features:
- Automatically determines the latest version of each app based on what's installed
- No need for manual version tracking - uses the newest discovered version as the reference
- Highlights computers with outdated versions of any application
- Simple, concise reports with the information you need

API Requirements:
- Access to the Jamf Pro Classic API through API Roles and Clients
- API role with read access to the required endpoints
- Classic API: Read, Computers: Read, Computer Groups: Read

Author: Your Name
Version: 2.0.0
License: MIT
"""

import argparse
import base64
import csv
import datetime
import json
import os
import re
import requests
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from urllib3.exceptions import InsecureRequestWarning

# Suppress insecure HTTPS warnings (remove in production or use proper certificates)
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

#------------------------------------------------------------------------------
# Core Functions
#------------------------------------------------------------------------------

def get_token():
    """
    Get the API token from an external script.
    
    Returns:
        str: The API token if successful, None otherwise.
    """
    try:
        token = subprocess.check_output(['bash', './jamf_get_token.sh'], encoding="utf-8").strip()
        return token
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

def create_filename(prefix, group_name=None):
    """
    Create a sanitized filename based on prefix and group name.
    
    Args:
        prefix (str): Prefix for the filename
        group_name (str, optional): Name of the computer group
        
    Returns:
        str: A sanitized filename suitable for any filesystem
    """
    # Format current date
    date_str = datetime.datetime.now().strftime('%Y-%m-%d')
    
    # Create filename with timestamp
    if group_name:
        # Sanitize group name
        sanitized_group = group_name.replace('/', '_').replace('\\', '_')
        sanitized_group = sanitized_group.replace(':', '_').replace('*', '_').replace('?', '_')
        sanitized_group = sanitized_group.replace('"', '_').replace('<', '_').replace('>', '_')
        sanitized_group = sanitized_group.replace('|', '_').replace(' ', '_')
        
        return f"{prefix}_{sanitized_group}_{date_str}.csv"
    else:
        return f"{prefix}_{date_str}.csv"

def version_key(version_str):
    """
    Create a key for sorting versions that handles mixed types correctly.
    
    Args:
        version_str (str): Version string to parse
        
    Returns:
        tuple: Tuple of components where strings are converted to a comparable format
    """
    # Handle empty or missing versions
    if not version_str or version_str == "Not Installed" or version_str.lower() == "unknown":
        return ((0, 0),)
    
    # Remove any build numbers or extra information in parentheses
    version_str = re.sub(r'\(.*?\)', '', version_str).strip()
    
    # Extract numbers and strings from the version
    components = []
    for part in re.findall(r'(\d+|\D+)', version_str):
        if part.isdigit():
            # Type 0 = integer
            components.append((0, int(part)))
        elif part.strip():
            # Type 1 = string
            components.append((1, part.strip()))
    
    return tuple(components) if components else ((0, 0),)

def compare_versions(version1, version2):
    """
    Compare two version strings.
    
    Args:
        version1 (str): First version string
        version2 (str): Second version string
        
    Returns:
        int: -1 if version1 < version2, 0 if equal, 1 if version1 > version2
    """
    key1 = version_key(version1)
    key2 = version_key(version2)
    
    if key1 < key2:
        return -1
    elif key1 > key2:
        return 1
    else:
        return 0

#------------------------------------------------------------------------------
# Jamf API Functions
#------------------------------------------------------------------------------

def get_computer_ids(server, auth_header, verify_ssl=True):
    """
    Fetch all computer IDs from Jamf Pro.
    
    Args:
        server (str): Jamf Pro server URL
        auth_header (dict): Authentication header
        verify_ssl (bool): Whether to verify SSL certificates
        
    Returns:
        list: List of tuples containing (computer_id, computer_name)
    """
    # Ensure server URL doesn't end with a trailing slash
    server = server.rstrip('/')
    url = f"{server}/JSSResource/computers"
    headers = {
        'Accept': 'application/json'
    }
    headers.update(auth_header)
    
    try:
        response = requests.get(url, headers=headers, verify=verify_ssl)
        response.raise_for_status()
        
        computers = response.json()['computers']
        return [(computer['id'], computer['name']) for computer in computers]
    except requests.exceptions.RequestException as e:
        print(f"Error fetching computer IDs: {e}", file=sys.stderr)
        sys.exit(1)

def get_computer_group_members(server, auth_header, group_name, verify_ssl=True):
    """
    Fetch the list of computer IDs that belong to a specific computer group.
    
    Args:
        server (str): Jamf Pro server URL
        auth_header (dict): Authentication header
        group_name (str): Name of the computer group
        verify_ssl (bool): Whether to verify SSL certificates
        
    Returns:
        list: List of tuples containing (computer_id, computer_name)
    """
    # Ensure server URL doesn't end with a trailing slash
    server = server.rstrip('/')
    
    # First, find the group ID by name
    url = f"{server}/JSSResource/computergroups/name/{group_name}"
    headers = {
        'Accept': 'application/json'
    }
    headers.update(auth_header)
    
    try:
        response = requests.get(url, headers=headers, verify=verify_ssl)
        response.raise_for_status()
        
        group_data = response.json()
        computer_list = []
        
        # Extract computer ID and name from the group
        if 'computer_group' in group_data and 'computers' in group_data['computer_group']:
            for computer in group_data['computer_group']['computers']:
                computer_list.append((computer['id'], computer['name']))
        
        return computer_list
    except requests.exceptions.RequestException as e:
        print(f"Error fetching computer group '{group_name}': {e}", file=sys.stderr)
        sys.exit(1)

def get_computer_applications(server, auth_header, computer_id, computer_name, verify_ssl=True, debug=False):
    """
    Fetch all applications installed on a specific computer.
    
    Args:
        server (str): Jamf Pro server URL
        auth_header (dict): Authentication header
        computer_id (int): Computer ID
        computer_name (str): Computer name
        verify_ssl (bool): Whether to verify SSL certificates
        debug (bool): Whether to enable debug output
        
    Returns:
        tuple: (list of application dictionaries, computer general info dictionary)
    """
    # Ensure server URL doesn't end with a trailing slash
    server = server.rstrip('/')
    url = f"{server}/JSSResource/computers/id/{computer_id}"
    
    # Use XML for more reliable parsing
    headers = {
        'Accept': 'text/xml'
    }
    headers.update(auth_header)
    
    try:
        if debug:
            print(f"Fetching applications for computer {computer_name} (ID: {computer_id})...")
        
        response = requests.get(url, headers=headers, verify=verify_ssl)
        response.raise_for_status()
        
        # Parse XML response
        root = ET.fromstring(response.text)
        
        # Get general info
        computer_info = {
            'computer_id': computer_id,
            'computer_name': computer_name,
            'serial_number': root.findtext('.//serial_number') or 'Unknown',
            'model': root.findtext('.//model') or 'Unknown',
            'os_version': root.findtext('.//os_version') or 'Unknown',
            'os_build': root.findtext('.//os_build') or 'Unknown',
            'last_report_date': root.findtext('.//report_date') or 'Unknown',
            'username': root.findtext('.//username') or 'Unknown',
            'last_inventory_update': root.findtext('.//last_inventory_update') or 'Unknown',
        }
        
        # Find all applications
        applications = []
        for app_elem in root.findall('.//software/applications/application'):
            app_name = app_elem.findtext('name') or 'Unknown'
            app_version = app_elem.findtext('version') or 'Unknown'
            app_path = app_elem.findtext('path') or 'Unknown'
            
            applications.append({
                'application_name': app_name,
                'application_version': app_version,
                'application_path': app_path
            })
        
        if debug:
            print(f"Found {len(applications)} applications on {computer_name}")
        
        return applications, computer_info
    except requests.exceptions.RequestException as e:
        print(f"Error fetching applications for computer {computer_name} (ID: {computer_id}): {e}", file=sys.stderr)
        return [], {}

#------------------------------------------------------------------------------
# Command Line Interface
#------------------------------------------------------------------------------

def parse_arguments():
    """
    Parse command-line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    # Default server URL (using a generic placeholder)
    default_server = "https://your-instance.jamfcloud.com"
    
    parser = argparse.ArgumentParser(description="Inventory applications and check for outdated versions in Jamf Pro")
    parser.add_argument('-s', '--server', default=default_server, 
                        help=f'Jamf Pro server URL (default: {default_server})')
    parser.add_argument('-u', '--username', help='API username (not needed if using token authentication)')
    parser.add_argument('-p', '--password', help='API password (not needed if using token authentication)')
    parser.add_argument('-t', '--token', action='store_true', help='Use token authentication from jamf_get_token.sh script')
    parser.add_argument('-g', '--group', help='Only include computers from this Jamf computer group')
    parser.add_argument('-o', '--output-prefix', default='jamf_inventory', 
                        help='Prefix for output CSV files (default: jamf_inventory)')
    parser.add_argument('--min-version-count', type=int, default=2,
                        help='Minimum number of different versions required to flag an app (default: 2)')
    parser.add_argument('--insecure', action='store_true', help='Skip SSL certificate verification')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode with verbose output')
    
    return parser.parse_args()

#------------------------------------------------------------------------------
# Main Function
#------------------------------------------------------------------------------

def main():
    """Main function that runs the script."""
    # Parse command-line arguments
    args = parse_arguments()
    
    # Ensure server URL is properly formatted
    if not args.server.startswith('http'):
        args.server = 'https://' + args.server
    
    # Prepare authentication
    auth_header = {}
    if args.token:
        token = get_token()
        if not token:
            print("Error: Token authentication selected but token retrieval failed. Ensure jamf_get_token.sh is available and working.", file=sys.stderr)
            sys.exit(1)
        auth_header = {'Authorization': f'Bearer {token}'}
    elif args.username and args.password:
        # Using Basic Auth for the classic API
        auth_string = base64.b64encode(f"{args.username}:{args.password}".encode()).decode()
        auth_header = {'Authorization': f'Basic {auth_string}'}
    else:
        print("Error: Either provide username and password or use token authentication.", file=sys.stderr)
        sys.exit(1)
    
    # Get computer IDs - either from a specific group or all computers
    if args.group:
        print(f"Getting computers from group: {args.group}")
        computers = get_computer_group_members(args.server, auth_header, args.group, verify_ssl=not args.insecure)
        print(f"Found {len(computers)} computers in group '{args.group}'.")
    else:
        computers = get_computer_ids(args.server, auth_header, verify_ssl=not args.insecure)
        print(f"Found {len(computers)} computers in Jamf Pro.")
    
    if not computers:
        print("No computers found. Exiting.")
        sys.exit(0)
    
    # Generate output filenames
    date_str = datetime.datetime.now().strftime('%Y-%m-%d')
    group_suffix = f"_{args.group.replace(' ', '_')}" if args.group else ""
    
    apps_summary_filename = f"{args.output_prefix}_apps_summary{group_suffix}_{date_str}.csv"
    outdated_computers_filename = f"{args.output_prefix}_outdated_computers{group_suffix}_{date_str}.csv"
    
    # Data structures for collecting information
    app_versions = defaultdict(list)  # Application name -> list of versions
    app_installations = defaultdict(list)  # Application name -> list of (computer_id, version)
    computer_details = {}  # Computer ID -> computer details
    
    # Process each computer
    total_computers = len(computers)
    for index, (computer_id, computer_name) in enumerate(computers):
        print(f"Processing computer {index+1}/{total_computers}: {computer_name}", end='\r')
        
        # Get applications for this computer
        applications, computer_info = get_computer_applications(
            args.server, auth_header, computer_id, computer_name, 
            verify_ssl=not args.insecure, debug=args.debug
        )
        
        if not computer_info:
            print(f"\nWarning: Could not retrieve information for computer {computer_name} (ID: {computer_id})")
            continue
        
        # Store computer details
        computer_details[computer_id] = computer_info
        
        # Process applications
        for app in applications:
            app_name = app['application_name']
            app_version = app['application_version']
            
            # Add to versions list for this application
            app_versions[app_name].append(app_version)
            
            # Track application installations with computer info
            app_installations[app_name].append((computer_id, app_version))
    
    print("\nProcessing complete.")
    
    # Determine latest version of each application and find outdated computers
    latest_versions = {}  # Application name -> latest version
    computer_outdated_apps = defaultdict(list)  # Computer ID -> list of (app_name, installed_version, latest_version)
    
    for app_name, versions in app_versions.items():
        # Find the latest version using our safe sorting function
        try:
            latest_version = sorted(versions, key=version_key)[-1]
            latest_versions[app_name] = latest_version
            
            # Check all installations to find outdated ones
            for computer_id, installed_version in app_installations[app_name]:
                if compare_versions(installed_version, latest_version) < 0:
                    computer_outdated_apps[computer_id].append(
                        (app_name, installed_version, latest_version)
                    )
        except Exception as e:
            print(f"Warning: Error processing versions for {app_name}: {e}")
    
    # Create applications summary report
    print(f"Generating applications summary report...")
    with open(apps_summary_filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Application', 'Version Count', 'Newest Version', 'Oldest Version', 
                         'Total Installations', 'Computers with Latest Version', 'Computers with Outdated Versions'])
        
        for app_name, versions in sorted(app_versions.items()):
            # Find newest and oldest versions safely
            if versions:
                try:
                    # Sort versions using the safe version comparison
                    sorted_versions = sorted(versions, key=version_key)
                    oldest_version = sorted_versions[0]
                    newest_version = sorted_versions[-1]
                    
                    # Count computers with the latest version vs outdated
                    latest_version_count = versions.count(newest_version)
                    outdated_count = len(versions) - latest_version_count
                except Exception as e:
                    print(f"Warning: Error sorting versions for {app_name}: {e}")
                    oldest_version = "Error"
                    newest_version = "Error"
                    latest_version_count = 0
                    outdated_count = 0
            else:
                oldest_version = "Unknown"
                newest_version = "Unknown"
                latest_version_count = 0
                outdated_count = 0
            
            # Count unique versions and total installations
            version_count = len(set(versions))
            total_installations = len(versions)
            
            # Only include in the report if there are multiple versions
            # or it's installed on a significant number of computers
            if version_count >= args.min_version_count or total_installations > 5:
                writer.writerow([
                    app_name, 
                    version_count, 
                    newest_version,
                    oldest_version,
                    total_installations,
                    latest_version_count,
                    outdated_count
                ])
    
    print(f"Applications summary written to {apps_summary_filename}")
    print(f"Found {len(app_versions)} unique applications across {len(computers)} computers")
    
    # Create outdated computers report
    computers_with_outdated_apps = len(computer_outdated_apps)
    if computers_with_outdated_apps > 0:
        print(f"Generating outdated computers report...")
        with open(outdated_computers_filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            
            # Create header row
            writer.writerow(['Computer Name', 'Serial Number', 'OS Version', 'Last Inventory Update', 'Outdated Apps Count', 'Outdated Applications'])
            
            for computer_id, outdated_apps in sorted(computer_outdated_apps.items(), 
                                                   key=lambda x: computer_details.get(x[0], {}).get('computer_name', '')):
                computer = computer_details.get(computer_id, {})
                if not computer:
                    continue
                
                # Format outdated apps as: App1 (installed v1 < latest v2), App2 (installed v3 < latest v4), ...
                outdated_apps_formatted = []
                for app_name, installed_version, latest_version in sorted(outdated_apps):
                    outdated_apps_formatted.append(f"{app_name} (installed {installed_version} < latest {latest_version})")
                
                writer.writerow([
                    computer.get('computer_name', 'Unknown'),
                    computer.get('serial_number', 'Unknown'),
                    computer.get('os_version', 'Unknown'),
                    computer.get('last_inventory_update', 'Unknown'),
                    len(outdated_apps),
                    '; '.join(outdated_apps_formatted)
                ])
        
        print(f"Outdated computers report written to {outdated_computers_filename}")
        print(f"Found {computers_with_outdated_apps} computers with outdated applications")
    else:
        print("No outdated applications found. Skipping outdated computers report.")

#------------------------------------------------------------------------------
# Entry Point
#------------------------------------------------------------------------------

if __name__ == "__main__":
    main()
