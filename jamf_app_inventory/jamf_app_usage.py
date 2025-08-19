#!/usr/bin/env python3
"""
Jamf Application Usage Reporter - Modular Version

Enhanced version with improved error handling, token refresh, and batch processing.
Uses the jamf_api_client module for robust API interactions.

Author: Omri KEdem
Version: 1.0.70
License: MIT
"""

import argparse
import csv
import datetime
import time
import os
import sys
from jamf_api_client import JamfAPIClient, save_progress, load_progress

def create_filename(app_name, group_name=None, days=None):
    """Create a sanitized filename based on app name and group name."""
    sanitized_app = app_name.replace('.app', '').replace('/', '_').replace('\\', '_')
    sanitized_app = sanitized_app.replace(':', '_').replace('*', '_').replace('?', '_')
    sanitized_app = sanitized_app.replace('"', '_').replace('<', '_').replace('>', '_')
    sanitized_app = sanitized_app.replace('|', '_').replace(' ', '_')
    
    date_str = datetime.datetime.now().strftime('%Y-%m-%d')
    
    if group_name:
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
            return f"{sanitized_app}_{date_str}.csv"

def find_app_usage(usage_data, app_name, debug=False):
    """
    Find usage minutes for a specific application in the usage data.
    
    Args:
        usage_data (dict): Dictionary with dates as keys and app lists as values
        app_name (str): Application name to search for
        debug (bool): Enable debug output
        
    Returns:
        dict: Dictionary with dates as keys and minutes as values
    """
    app_name_clean = app_name.lower().strip()
    app_name_no_ext = app_name_clean.replace('.app', '').strip()
    
    apps_data = {}
    
    for date, apps in usage_data.items():
        for app in apps:
            current_app = app['name']
            current_app_clean = current_app.lower().strip()
            current_app_no_ext = current_app_clean.replace('.app', '').strip()
            
            # Flexible app name matching
            exact_match = (current_app_clean == app_name_clean)
            no_ext_match = (current_app_no_ext == app_name_no_ext)
            partial_match = (app_name_no_ext in current_app_no_ext)
            contains_match = (app_name_clean in current_app_clean or 
                             current_app_clean in app_name_clean)
            
            is_match = exact_match or no_ext_match or partial_match or contains_match
            
            if is_match:
                if debug:
                    print(f"Match found: '{current_app}' for search term '{app_name}'")
                
                if date not in apps_data:
                    apps_data[date] = 0
                apps_data[date] += app['foreground']
    
    return apps_data

def list_all_applications(api_client, computers, start_date, end_date, verify_ssl=True, max_computers=5):
    """
    List all applications found in usage data from a sample of computers.
    
    Args:
        api_client (JamfAPIClient): Initialized API client
        computers (list): List of computers to check
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format
        verify_ssl (bool): Whether to verify SSL certificates
        max_computers (int): Maximum number of computers to check
        
    Returns:
        dict: Dictionary with app names as keys and total minutes as values
    """
    all_found_apps = {}
    computers_to_check = computers[:max_computers]
    
    for computer_id, computer_name, serial_number in computers_to_check:
        print(f"Fetching apps for {computer_name} (Serial: {serial_number or 'N/A'})...")
        
        usage_data = api_client.get_computer_application_usage(
            computer_id, computer_name, serial_number, start_date, end_date, verify_ssl
        )
        
        if usage_data:
            app_count = 0
            for date, apps in usage_data.items():
                for app in apps:
                    app_name = app['name']
                    minutes = app['foreground']
                    if app_name not in all_found_apps:
                        all_found_apps[app_name] = 0
                    all_found_apps[app_name] += minutes
                    app_count += 1
            
            if app_count > 0:
                print(f"Found {app_count} app entries for {computer_name}")
    
    return all_found_apps

def parse_arguments():
    """Parse command-line arguments."""
    default_server = "https://your-instance.jamfcloud.com"
    
    parser = argparse.ArgumentParser(description="Retrieve application usage data from Jamf Pro API")
    parser.add_argument('-s', '--server', default=default_server, 
                        help=f'Jamf Pro server URL (default: {default_server})')
    parser.add_argument('-u', '--username', help='API username (not needed if using token authentication)')
    parser.add_argument('-p', '--password', help='API password (not needed if using token authentication)')
    parser.add_argument('-a', '--app', help='Application name to search for (e.g., "Google Chrome.app")')
    parser.add_argument('-d', '--days', type=int, default=30, help='Number of days to look back (default: 30)')
    parser.add_argument('-o', '--output', help='Output CSV file name (default: auto-generated based on app and group)')
    parser.add_argument('-t', '--token', action='store_true', help='Use token authentication from jamf_get_token.sh script')
    parser.add_argument('-g', '--group', help='Only include computers from this Jamf computer group')
    parser.add_argument('--insecure', action='store_true', help='Skip SSL certificate verification')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode with verbose output')
    parser.add_argument('--list-apps', action='store_true', help='List all applications found in usage data for the first 5 computers')
    parser.add_argument('--batch-size', type=int, default=50, help='Number of computers to process in each batch (default: 50)')
    parser.add_argument('--delay', type=float, default=0.5, help='Delay between API requests in seconds (default: 0.5)')
    parser.add_argument('--resume', action='store_true', help='Resume from previous progress file')
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.list_apps and not args.app:
        parser.error("the --app argument is required unless --list-apps is specified")
    
    return args

def main():
    """Main function that runs the script."""
    args = parse_arguments()
    
    # Ensure server URL is properly formatted
    if not args.server.startswith('http'):
        args.server = 'https://' + args.server
    
    # Create API client
    api_client = JamfAPIClient(
        server=args.server,
        username=args.username,
        password=args.password,
        use_token=args.token,
        request_delay=args.delay
    )
    
    # Calculate date range
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=args.days)
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    if args.list_apps:
        print(f"Listing applications used from {start_date_str} to {end_date_str}...")
    elif args.app:
        print(f"Fetching application usage for '{args.app}' from {start_date_str} to {end_date_str}...")
    
    # Get computer IDs
    try:
        if args.group:
            print(f"Getting computers from group: {args.group}")
            computers = api_client.get_computer_group_members(args.group, verify_ssl=not args.insecure)
            print(f"Found {len(computers)} computers in group '{args.group}'.")
        else:
            computers = api_client.get_computers(verify_ssl=not args.insecure)
            # Convert to format with serial numbers (set to None for now)
            computers = [(c[0], c[1], None) for c in computers]
            print(f"Found {len(computers)} computers in Jamf Pro.")
    except Exception as e:
        print(f"Failed to get computer list: {e}")
        sys.exit(1)
    
    if not computers:
        print("No computers found. Exiting.")
        sys.exit(0)
    
    # Handle large batches
    if len(computers) > 200:
        print(f"Large batch detected ({len(computers)} computers). Enabling enhanced processing...")
        api_client.request_delay = max(args.delay, 1.0)
    
    # Handle list-apps mode
    if args.list_apps:
        all_found_apps = list_all_applications(
            api_client, computers, start_date_str, end_date_str, 
            verify_ssl=not args.insecure, max_computers=5
        )
        
        if all_found_apps:
            print("\nApplications found in the usage data (sorted by total minutes):")
            sorted_apps = sorted(all_found_apps.items(), key=lambda x: x[1], reverse=True)
            for app_name, minutes in sorted_apps:
                print(f"- '{app_name}': {minutes} minutes")
            print(f"\nTotal unique applications found: {len(all_found_apps)}")
        else:
            print("No application usage data found.")
        
        sys.exit(0)
    
    # Progress file for resume capability
    progress_file = f"progress_{args.app.replace(' ', '_')}_{args.group or 'all'}.json"
    processed_computers = set()
    
    if args.resume:
        processed_computers = load_progress(progress_file)
        print(f"Resuming from progress file. {len(processed_computers)} computers already processed.")
    
    # Generate output filename if not specified
    if not args.output:
        args.output = create_filename(args.app, args.group, args.days)
        print(f"Output will be written to: {args.output}")
    
    # Prepare CSV data
    csv_data = []
    computers_to_process = [(c[0], c[1], c[2]) for c in computers if c[0] not in processed_computers]
    
    print(f"Processing {len(computers_to_process)} computers (skipping {len(processed_computers)} already processed)...")
    
    # Process computers in batches
    batch_size = args.batch_size
    for batch_start in range(0, len(computers_to_process), batch_size):
        batch_end = min(batch_start + batch_size, len(computers_to_process))
        batch = computers_to_process[batch_start:batch_end]
        
        print(f"\nProcessing batch {batch_start//batch_size + 1}/{(len(computers_to_process) + batch_size - 1)//batch_size}")
        print(f"Computers {batch_start + 1} to {batch_end} of {len(computers_to_process)} remaining")
        
        for computer_id, computer_name, serial_number in batch:
            current_index = batch_start + batch.index((computer_id, computer_name, serial_number)) + 1
            
            if args.debug:
                print(f"Processing: {computer_name} (ID: {computer_id}, Serial: {serial_number or 'N/A'})")
            else:
                print(f"Processing computer {current_index}/{len(computers_to_process)}: {computer_name}", end='\r')
            
            # Get usage data for this computer
            usage_data = api_client.get_computer_application_usage(
                computer_id, computer_name, serial_number, start_date_str, end_date_str, 
                verify_ssl=not args.insecure
            )
            
            if usage_data:
                # Find usage for the specific app
                app_usage = find_app_usage(usage_data, args.app, debug=args.debug)
                
                if app_usage:
                    total_minutes = sum(app_usage.values())
                    if total_minutes > 0:
                        csv_data.append({
                            'Computer ID': computer_id,
                            'Computer Name': computer_name,
                            'Serial Number': serial_number or 'N/A',
                            'Application': args.app,
                            'Total Minutes': total_minutes,
                            'Days Used': len(app_usage),
                            'Average Minutes Per Day': round(total_minutes / len(app_usage), 2),
                            'Date Range': f"{start_date_str} to {end_date_str}"
                        })
            
            # Mark as processed
            processed_computers.add(computer_id)
        
        # Save progress after each batch
        save_progress(progress_file, processed_computers)
        print(f"\nBatch complete. Progress saved. Found {len(csv_data)} computers with usage so far.")
        
        # Add a pause between batches for large operations
        if len(computers_to_process) > 100:
            print("Pausing briefly between batches...")
            time.sleep(2)
    
    print("\nProcessing complete.")
    
    # Clean up progress file on successful completion
    try:
        os.remove(progress_file)
    except FileNotFoundError:
        pass
    
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
        print(f"Total computers processed: {len(processed_computers)}")
    else:
        print(f"\nNo usage data found for '{args.app}'")
        print("Possible reasons:")
        print("1. The application name might be different than what you provided")
        print("2. No computers have used this application in the specified time period")
        print("3. Application usage data might not be available")
        print("\nSuggestions:")
        print("- Try running with --list-apps to see all available applications")
        print("- Try a different app name format (with or without '.app' suffix)")
        print("- Use --debug to see more detailed information about the API responses")

if __name__ == "__main__":
    main()
