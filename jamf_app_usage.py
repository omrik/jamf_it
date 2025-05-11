def create_filename(app_name, group_name=None, days=None):
    """Create a sanitized filename based on app name and group name."""
    # Sanitize app name for use in filename - remove extension and problematic characters
    sanitized_app = app_name.replace('.app', '').replace('/', '_').replace('\\', '_')
    sanitized_app = sanitized_app.replace(':', '_').replace('*', '_').replace('?', '_')
    sanitized_app = sanitized_app.replace('"', '_').replace('<', '_').replace('>', '_')
    sanitized_app = sanitized_app.replace('|', '_').replace(' ', '_')
    
    # Format current date
    date_str = datetime.datetime.now().strftime('%Y-%m-%d')
    
    # Create filename with timestamp
    if group_name:
        # Sanitize group name too
        sanitized_group = group_name.replace('/', '_').replace('\\', '_')
        sanitized_group = sanitized_group.replace(':', '_').replace('*', '_').replace('?', '_')
        sanitized_group = sanitized_group.replace('"', '_').replace('<', '_').replace('>', '_')
        sanitized_group = sanitized_group.replace('|', '_').replace(' ', '_')
        
        if days:
            return f"{sanitized_app}_{sanitized_group}_{days}days_{date_str}.csv"
        else:
            return f"{sanitized_app}_{sanitized_group}_{date_str}.csv"
    else:
        if days:
            return f"{sanitized_app}_{days}days_{date_str}.csv"
        else:
            return f"{sanitized_app}_{date_str}.csv"#!/usr/bin/env python3
"""
Jamf Application Usage Reporter
This script retrieves application usage data from Jamf Pro API and outputs it to a CSV file.
It shows the amount of minutes each computer has used a specific application.
"""

import argparse
import base64
import csv
import datetime
import json
import os
import requests
import subprocess
import sys
from requests.auth import HTTPBasicAuth
from urllib3.exceptions import InsecureRequestWarning

# Suppress insecure HTTPS warnings (remove in production or use proper certificates)
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

def get_token():
    """
    Get the API token from an external script or return None if not available.
    """
    try:
        token = subprocess.check_output(['bash', './jamf_get_token.sh'], encoding="utf-8").strip()
        return token
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

def parse_arguments():
    """Parse command-line arguments."""
    # Default server URL (using a generic placeholder)
    default_server = "https://your-instance.jamfcloud.com"
    
    parser = argparse.ArgumentParser(description="Retrieve application usage data from Jamf Pro API")
    parser.add_argument('-s', '--server', default=default_server, 
                        help=f'Jamf Pro server URL (default: {default_server})')
    parser.add_argument('-u', '--username', help='API username (not needed if using token authentication)')
    parser.add_argument('-p', '--password', help='API password (not needed if using token authentication)')
    parser.add_argument('-a', '--app', required=True, help='Application name to search for (e.g., "Google Chrome.app")')
    parser.add_argument('-d', '--days', type=int, default=30, help='Number of days to look back (default: 30)')
    parser.add_argument('-o', '--output', help='Output CSV file name (default: auto-generated based on app and group)')
    parser.add_argument('-t', '--token', action='store_true', help='Use token authentication from jamf_get_token.sh script')
    parser.add_argument('-g', '--group', help='Only include computers from this Jamf computer group')
    parser.add_argument('--insecure', action='store_true', help='Skip SSL certificate verification')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode with verbose output')
    parser.add_argument('--list-apps', action='store_true', help='List all applications found in usage data for the first 5 computers')
    
    return parser.parse_args()

def get_computer_group_members(server, auth_header, group_name, verify_ssl=True):
    """Fetch the list of computer IDs that belong to a specific computer group."""
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
                # Get serial number from computer details
                detail_url = f"{server}/JSSResource/computers/id/{computer['id']}/subset/General"
                try:
                    detail_response = requests.get(detail_url, headers=headers, verify=verify_ssl)
                    detail_response.raise_for_status()
                    details = detail_response.json()
                    
                    if 'general' in details['computer'] and 'serial_number' in details['computer']['general']:
                        serial_number = details['computer']['general']['serial_number']
                        computer_list.append((computer['id'], computer['name'], serial_number))
                    else:
                        # Fall back to just ID and name if serial not found
                        computer_list.append((computer['id'], computer['name'], None))
                except:
                    # If detail fetch fails, fall back to just ID and name
                    computer_list.append((computer['id'], computer['name'], None))
        
        return computer_list
    except requests.exceptions.RequestException as e:
        print(f"Error fetching computer group '{group_name}': {e}", file=sys.stderr)
        sys.exit(1)

def get_computer_ids(server, auth_header, verify_ssl=True):
    """Fetch all computer IDs from Jamf Pro."""
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
        computer_data = []
        
        # Fetch details for each computer to get serial numbers
        for computer in computers:
            computer_id = computer['id']
            computer_name = computer['name']
            
            # Get serial number from computer details
            detail_url = f"{server}/JSSResource/computers/id/{computer_id}/subset/General"
            try:
                detail_response = requests.get(detail_url, headers=headers, verify=verify_ssl)
                detail_response.raise_for_status()
                details = detail_response.json()
                
                if 'general' in details['computer'] and 'serial_number' in details['computer']['general']:
                    serial_number = details['computer']['general']['serial_number']
                    computer_data.append((computer_id, computer_name, serial_number))
                else:
                    # Fall back to just ID and name if serial not found
                    computer_data.append((computer_id, computer_name, None))
            except:
                # If detail fetch fails, fall back to just ID and name
                computer_data.append((computer_id, computer_name, None))
        
        return computer_data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching computer IDs: {e}", file=sys.stderr)
        sys.exit(1)

def list_all_apps(server, auth_header, computer_id, computer_name, serial_number, start_date, end_date, verify_ssl=True):
    """Fetch and list all applications used on a specific computer."""
    # Ensure server URL doesn't end with a trailing slash
    server = server.rstrip('/')
    
    # First try with serial number if available
    if serial_number:
        url = f"{server}/JSSResource/computerapplicationusage/serialnumber/{serial_number}/{start_date}_{end_date}"
    else:
        # Fall back to computer ID if no serial number
        url = f"{server}/JSSResource/computerapplicationusage/id/{computer_id}/{start_date}_{end_date}"
    
    # Try with XML first, as this was how the original script worked
    xml_headers = {
        'Accept': 'text/xml'
    }
    xml_headers.update(auth_header)
    
    try:
        response = requests.get(url, headers=xml_headers, verify=verify_ssl)
        
        # Skip if no data is available for this computer
        if response.status_code == 404:
            return None
        
        response.raise_for_status()
        
        # Try to parse XML response
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.text)
        
        all_apps = []
        # Iterate through each day's usage data to collect app names
        for usage_data in root.findall('.//usage'):
            for app_elem in usage_data.findall('.//app'):
                name_elem = app_elem.find('name')
                foreground_elem = app_elem.find('foreground')
                
                if name_elem is not None and foreground_elem is not None:
                    app_name = name_elem.text
                    try:
                        minutes = int(foreground_elem.text)
                        all_apps.append((app_name, minutes))
                    except (ValueError, TypeError):
                        # Skip if minutes can't be converted to int
                        pass
        
        # Return a dict with app names as keys and total minutes as values
        app_usage = {}
        for app_name, minutes in all_apps:
            if app_name not in app_usage:
                app_usage[app_name] = 0
            app_usage[app_name] += minutes
        
        return app_usage
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching app list for computer {computer_name} (ID: {computer_id}): {e}", file=sys.stderr)
        return None

def get_app_usage(server, auth_header, computer_id, computer_name, serial_number, app_name, start_date, end_date, verify_ssl=True, debug=False):
    """Fetch application usage for a specific computer."""
    # Ensure server URL doesn't end with a trailing slash
    server = server.rstrip('/')
    
    # First try with serial number if available
    if serial_number:
        url = f"{server}/JSSResource/computerapplicationusage/serialnumber/{serial_number}/{start_date}_{end_date}"
    else:
        # Fall back to computer ID if no serial number
        url = f"{server}/JSSResource/computerapplicationusage/id/{computer_id}/{start_date}_{end_date}"
    
    # Try with XML first, as this was how the original script worked
    xml_headers = {
        'Accept': 'text/xml'
    }
    xml_headers.update(auth_header)
    
    try:
        response = requests.get(url, headers=xml_headers, verify=verify_ssl)
        
        # Skip if no data is available for this computer
        if response.status_code == 404:
            if debug:
                print(f"No data found for computer {computer_name} (ID: {computer_id})")
            return None
        
        response.raise_for_status()
        
        # Try to parse XML response
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.text)
        
        apps_data = {}
        # Prepare app name for flexible matching
        app_name_clean = app_name.lower().strip()
        app_name_no_ext = app_name_clean.replace('.app', '').strip()
        
        # Debugging: Print all app names found in XML
        if debug:
            all_app_names = set()
            for usage_data in root.findall('.//usage'):
                date_elem = usage_data.find('date')
                date = date_elem.text if date_elem is not None else "Unknown"
                
                for app_elem in usage_data.findall('.//app'):
                    name_elem = app_elem.find('name')
                    if name_elem is not None:
                        all_app_names.add(name_elem.text)
            
            print(f"All app names found for computer {computer_name} (ID: {computer_id}):")
            for name in sorted(all_app_names):
                print(f"  - '{name}'")
        
        # Process usage data
        for usage_data in root.findall('.//usage'):
            date_elem = usage_data.find('date')
            date = date_elem.text if date_elem is not None else "Unknown"
            
            if debug:
                print(f"Processing date: {date} for computer {computer_name} (ID: {computer_id})")
            
            for app_elem in usage_data.findall('.//app'):
                name_elem = app_elem.find('name')
                foreground_elem = app_elem.find('foreground')
                
                if name_elem is not None and foreground_elem is not None:
                    current_app = name_elem.text
                    foreground_minutes = int(foreground_elem.text)
                    
                    if current_app:
                        current_app_clean = current_app.lower().strip()
                        current_app_no_ext = current_app_clean.replace('.app', '').strip()
                        
                        # Exact match check
                        exact_match = (current_app_clean == app_name_clean)
                        
                        # No extension match
                        no_ext_match = (current_app_no_ext == app_name_no_ext)
                        
                        # Partial match
                        partial_match = (app_name_no_ext in current_app_no_ext)
                        
                        # String containment (both ways)
                        contains_match = (app_name_clean in current_app_clean or 
                                         current_app_clean in app_name_clean)
                        
                        is_match = exact_match or no_ext_match or partial_match or contains_match
                        
                        if is_match:
                            if debug:
                                print(f"Match found: '{current_app}' for search term '{app_name}'")
                                print(f"  - Exact match: {exact_match}")
                                print(f"  - No extension match: {no_ext_match}")
                                print(f"  - Partial match: {partial_match}")
                                print(f"  - Contains match: {contains_match}")
                                print(f"  - Minutes: {foreground_minutes}")
                            
                            if date not in apps_data:
                                apps_data[date] = 0
                            apps_data[date] += foreground_minutes
        
        return apps_data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching usage data for computer {computer_name} (ID: {computer_id}): {e}", file=sys.stderr)
        return None

def main():
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
    
    # Calculate date range
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=args.days)
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    print(f"Fetching application usage for '{args.app}' from {start_date_str} to {end_date_str}...")
    
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
    
    # If list-apps mode is enabled, just list app names from the first few computers
    if args.list_apps:
        print("\nListing all applications found in usage data (from the first 5 computers):")
        all_found_apps = {}
        computers_to_check = computers[:5]  # Limit to first 5 computers to avoid long wait times
        
        for computer_id, computer_name, serial_number in computers_to_check:
            print(f"Fetching apps for {computer_name} (Serial: {serial_number or 'N/A'})...")
            app_usage = list_all_apps(args.server, auth_header, computer_id, computer_name, serial_number, 
                                     start_date_str, end_date_str, verify_ssl=not args.insecure)
            if app_usage:
                print(f"Found {len(app_usage)} apps for {computer_name}")
                for app_name, minutes in app_usage.items():
                    if app_name not in all_found_apps:
                        all_found_apps[app_name] = 0
                    all_found_apps[app_name] += minutes
        
        if all_found_apps:
            print("\nApplications found in the usage data (sorted by total minutes):")
            # Sort by total minutes, descending
            sorted_apps = sorted(all_found_apps.items(), key=lambda x: x[1], reverse=True)
            for app_name, minutes in sorted_apps:
                print(f"- '{app_name}': {minutes} minutes")
            print(f"\nTotal unique applications found: {len(all_found_apps)}")
            print("\nTo search for a specific app, run the script again with the -a option and the exact app name.")
        else:
            print("No application usage data found for the first 5 computers.")
        
        sys.exit(0)
    
    # Generate output filename if not specified
    if not args.output:
        args.output = create_filename(args.app, args.group, args.days)
        print(f"Output will be written to: {args.output}")
    
    # Prepare CSV data
    csv_data = []
    total_computers = len(computers)
    matched_computers = 0
    
    # Process each computer
    for index, (computer_id, computer_name, serial_number) in enumerate(computers):
        if args.debug:
            print(f"\nProcessing computer {index+1}/{total_computers}: {computer_name} (ID: {computer_id}, Serial: {serial_number or 'N/A'})")
        else:
            print(f"Processing computer {index+1}/{total_computers}: {computer_name}", end='\r')
        
        # Ensure server URL doesn't end with a trailing slash
        server_url = args.server.rstrip('/')
        
        # Some early debug analysis for the first few computers if debug mode
        if args.debug and index < 3:
            # Get all app names for this computer to help with debugging
            app_usage = list_all_apps(server_url, auth_header, computer_id, computer_name, serial_number,
                                     start_date_str, end_date_str, verify_ssl=not args.insecure)
            if app_usage:
                print(f"Applications found on {computer_name} (showing top 10 by usage):")
                # Sort by minutes, take top 10
                sorted_apps = sorted(app_usage.items(), key=lambda x: x[1], reverse=True)[:10]
                for app_name, minutes in sorted_apps:
                    print(f"  - '{app_name}': {minutes} minutes")
            else:
                print(f"No application usage data found for {computer_name}")
                
        usage_data = get_app_usage(
            server_url, auth_header, computer_id, computer_name, serial_number, args.app, 
            start_date_str, end_date_str, verify_ssl=not args.insecure, debug=args.debug
        )
        
        if usage_data:
            matched_computers += 1
            # Calculate total minutes across all days
            total_minutes = sum(usage_data.values())
            if total_minutes > 0:
                # Add to CSV data if app was used
                csv_data.append({
                    'Computer ID': computer_id,
                    'Computer Name': computer_name,
                    'Serial Number': serial_number or 'N/A',
                    'Application': args.app,
                    'Total Minutes': total_minutes,
                    'Days Used': len(usage_data),
                    'Average Minutes Per Day': round(total_minutes / len(usage_data), 2),
                    'Date Range': f"{start_date_str} to {end_date_str}"
                })
    
    print("\nProcessing complete.")
    
    # Write CSV file
    if csv_data:
        with open(args.output, 'w', newline='') as csv_file:
            fieldnames = ['Computer ID', 'Computer Name', 'Serial Number', 'Application', 'Total Minutes', 
                          'Days Used', 'Average Minutes Per Day', 'Date Range']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_data)
        
        print(f"\nResults written to {args.output}")
        print(f"Found {len(csv_data)} computers using '{args.app}'")
    else:
        print(f"\nNo usage data found for '{args.app}'")
        print("Possible reasons:")
        print("1. The application name might be different than what you provided")
        print("2. No computers have used this application in the specified time period")
        print("3. The application usage data might not be available or is stored differently")
        print("\nSuggestions:")
        print("- Try running with --list-apps to see all available applications")
        print("- Try a different app name format (with or without '.app' suffix)")
        print("- Try a partial name match (e.g., 'Chrome' instead of 'Google Chrome.app')")
        print("- Increase the number of days with -d option to look at a longer history")
        print("- Use --debug to see more detailed information about the API responses")

if __name__ == "__main__":
    main()
