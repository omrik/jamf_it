#!/usr/bin/env python3
"""
Apple Business Manager to Jamf Pro Device Sync Script - Optimized Version
High-performance version that bulk fetches all Jamf computers for faster processing.

This optimized version improves performance by:
- Fetching all Jamf computers in bulk at startup
- Creating an in-memory lookup dictionary by serial number
- Eliminating individual API calls for device lookups
- Maintaining individual updates for proper error handling

Author: IT Team  
Version: 2.0 (Optimized)
"""

import requests
import json
import logging
import subprocess
import os
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from urllib.parse import urlparse, parse_qs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DeviceInfo:
    """Simple device information container"""
    def __init__(self, serial_number: str, added_to_org_date: str, order_number: str, 
                 purchase_source_type: str, purchase_source_id: str):
        self.serial_number = serial_number
        self.added_to_org_date = added_to_org_date
        self.order_number = order_number
        self.purchase_source_type = purchase_source_type
        self.purchase_source_id = purchase_source_id

class TokenExpiredError(Exception):
    """Custom exception for when API tokens expire"""
    pass

def get_token_from_script(script_name: str, token_type: str = "API") -> str:
    """
    Get API token by running a shell script
    
    Args:
        script_name: Name of the shell script to execute
        token_type: Type of token for logging (e.g., "Jamf Pro", "Apple Business Manager")
        
    Returns:
        API token as string
    """
    try:
        # Run the shell script and capture output
        result = subprocess.run(
            [f"./{script_name}"],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Get the token from stdout and strip any whitespace
        token = result.stdout.strip()
        
        if not token:
            raise ValueError(f"Shell script {script_name} returned empty token")
        
        logger.info(f"Successfully retrieved {token_type} token from {script_name}")
        return token
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Shell script {script_name} failed: {e}")
        logger.error(f"Script output: {e.stdout}")
        logger.error(f"Script error: {e.stderr}")
        raise
    except Exception as e:
        logger.error(f"Error getting {token_type} token from {script_name}: {e}")
        raise

def load_vendor_mapping(mapping_file: str = "vendor_mapping.json") -> Dict[str, str]:
    """
    Load vendor ID to name mapping from external JSON file
    
    Args:
        mapping_file: Path to the vendor mapping JSON file
        
    Returns:
        Dictionary mapping vendor IDs to vendor names
    """
    try:
        if not os.path.exists(mapping_file):
            logger.warning(f"Vendor mapping file {mapping_file} not found. Using vendor IDs as names.")
            return {}
        
        with open(mapping_file, 'r') as f:
            mapping = json.load(f)
        
        logger.info(f"Loaded {len(mapping)} vendor mappings from {mapping_file}")
        return mapping
        
    except Exception as e:
        logger.error(f"Error loading vendor mapping file {mapping_file}: {e}")
        logger.warning("Using vendor IDs as names.")
        return {}

def get_vendor_name(vendor_id: str, vendor_mapping: Dict[str, str]) -> str:
    """
    Get vendor name from vendor ID using the mapping
    
    Args:
        vendor_id: Vendor ID from ABM
        vendor_mapping: Dictionary mapping vendor IDs to names
        
    Returns:
        Vendor name if found in mapping, otherwise returns the vendor ID
    """
    return vendor_mapping.get(vendor_id, vendor_id)

def get_devices_from_abm(abm_token: str) -> List[DeviceInfo]:
    """
    Fetch all devices from Apple Business Manager using pagination
    
    Args:
        abm_token: ABM API token
        
    Returns:
        List of DeviceInfo objects
    """
    logger.info("Fetching devices from Apple Business Manager...")
    
    devices = []
    base_url = "https://api-business.apple.com/v1"
    headers = {
        'Authorization': f'Bearer {abm_token}',
        'Content-Type': 'application/json'
    }
    
    cursor = None
    page = 1
    
    while True:
        # Build API request
        url = f"{base_url}/orgDevices"
        params = {"limit": 100}
        if cursor:
            params["cursor"] = cursor
        
        # Make request
        logger.info(f"Fetching page {page} from ABM...")
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Process devices - Apple Business Manager uses 'data' array
        device_list = data.get('data', [])
        logger.info(f"Found {len(device_list)} devices in page {page}")
        
        if not device_list:
            logger.info("No more devices found, pagination complete")
            break
        
        for device_data in device_list:
            # Extract attributes from the nested structure
            attributes = device_data.get('attributes', {})
            
            device = DeviceInfo(
                serial_number=attributes.get('serialNumber', ''),
                added_to_org_date=attributes.get('addedToOrgDateTime', ''),
                order_number=attributes.get('orderNumber', ''),
                purchase_source_type=attributes.get('purchaseSourceType', ''),
                purchase_source_id=attributes.get('purchaseSourceId', '')
            )
            devices.append(device)
        
        # Handle JSON API pagination - check for next page
        links = data.get('links', {})
        meta = data.get('meta', {})
        
        next_url = links.get('next')
        if next_url:
            # Extract cursor parameter from the next URL
            parsed_url = urlparse(next_url)
            query_params = parse_qs(parsed_url.query)
            cursor = query_params.get('cursor', [None])[0]
            logger.info(f"Moving to page {page + 1} with cursor from next URL")
        elif 'cursor' in meta:
            # Fallback: check for cursor in metadata
            cursor = meta['cursor']  
            logger.info(f"Moving to page {page + 1} with meta cursor")
        else:
            cursor = None
            logger.info("No pagination info found")
        
        if not cursor:
            logger.info("No more pages available, pagination complete")
            break
        
        page += 1
    
    logger.info(f"Retrieved {len(devices)} devices from ABM across {page} pages")
    return devices

def get_all_jamf_computers(jamf_token: str, jamf_server_url: str) -> Dict[str, Dict]:
    """
    Fetch all computers from Jamf Pro using the modern API and create a serial number lookup dictionary
    
    This function bulk fetches all computers from Jamf Pro using the v1 API at once and creates
    an in-memory dictionary for fast serial number lookups, eliminating the need
    for individual API calls during the sync process.
    
    Args:
        jamf_token: Jamf Pro API token
        jamf_server_url: Jamf Pro server URL
        
    Returns:
        Dictionary mapping serial numbers to computer records
        
    Raises:
        TokenExpiredError: If the Jamf Pro token expires during fetch
    """
    logger.info("Bulk fetching all computers from Jamf Pro using v1 API...")
    
    computers = []
    page = 0
    page_size = 100
    
    while True:
        # Use the basic computers list endpoint (not inventory-detail)
        url = f"{jamf_server_url}/api/v1/computers-inventory"
        headers = {
            'Authorization': f'Bearer {jamf_token}',
            'Accept': 'application/json'
        }
        
        params = {
            'page': page,
            'page-size': page_size,
            'sort': 'id:asc',
            'section': 'GENERAL,HARDWARE'  # Get both general and hardware sections
        }
        
        logger.info(f"Fetching computers page {page} from Jamf Pro...")
        response = requests.get(url, headers=headers, params=params)
        
        # Check for token expiration
        if response.status_code == 401:
            raise TokenExpiredError("Jamf Pro token expired during bulk computer fetch")
        
        response.raise_for_status()
        data = response.json()
        
        # Get computers from this page
        page_computers = data.get('results', [])
        computers.extend(page_computers)
        
        logger.info(f"Retrieved {len(page_computers)} computers from page {page}")
        
        # Check if we have more pages
        total_count = data.get('totalCount', 0)
        if len(computers) >= total_count:
            break
        
        page += 1
    
    logger.info(f"Retrieved {len(computers)} total computers from Jamf Pro")
    
    # Debug: Check the structure of the first computer record
    if computers:
        logger.info(f"Sample computer structure: {json.dumps(computers[0], indent=2)[:500]}...")
    
    # Create lookup dictionary by serial number
    serial_lookup = {}
    
    for computer in computers:
        # Try multiple possible paths for serial number in v1 API
        serial_number = None
        
        # Check the hardware section first (most likely location)
        if 'hardware' in computer:
            serial_number = computer['hardware'].get('serialNumber')
        # Fallback to general section
        elif 'general' in computer:
            serial_number = computer['general'].get('serialNumber')
        # Final fallback to direct serialNumber field
        elif 'serialNumber' in computer:
            serial_number = computer.get('serialNumber')
        
        if serial_number:
            # Store the computer info for quick lookup
            serial_lookup[serial_number] = {
                'id': computer.get('id'),
                'name': computer.get('general', {}).get('name', 'Unknown'),
                'serial_number': serial_number
            }
        else:
            logger.warning(f"No serial number found for computer ID {computer.get('id')}")
            # Debug: Show available keys to help troubleshoot
            logger.debug(f"Available keys for computer {computer.get('id')}: {list(computer.keys())}")
            if 'hardware' in computer:
                logger.debug(f"Hardware keys: {list(computer['hardware'].keys())}")
    
    logger.info(f"Created lookup dictionary for {len(serial_lookup)} computers")
    return serial_lookup

def calculate_warranty_date(added_to_org_date: str) -> str:
    """
    Calculate warranty expiration date (3 years from added to org date)
    
    Args:
        added_to_org_date: Date device was added to organization
        
    Returns:
        Warranty expiration date as string
    """
    # Parse the date (assuming ISO format)
    added_date = datetime.fromisoformat(added_to_org_date.replace('Z', '+00:00'))
    
    # Add 3 years
    warranty_date = added_date + timedelta(days=3*365)
    
    # Return in YYYY-MM-DD format
    return warranty_date.strftime('%Y-%m-%d')

def create_jamf_purchase_data(device: DeviceInfo, vendor_mapping: Dict[str, str]) -> Dict:
    """
    Create Jamf Pro purchasing data from ABM device information
    
    Args:
        device: DeviceInfo object from ABM
        vendor_mapping: Dictionary mapping vendor IDs to names
        
    Returns:
        Dictionary formatted for Jamf Pro purchasing update
    """
    # Calculate warranty date
    warranty_date = calculate_warranty_date(device.added_to_org_date)
    
    # Format purchase date
    purchase_date = datetime.fromisoformat(device.added_to_org_date.replace('Z', '+00:00'))
    po_date = purchase_date.strftime('%Y-%m-%d')
    
    # Get vendor name from mapping
    vendor_name = get_vendor_name(device.purchase_source_id, vendor_mapping)
    
    # Build purchase data
    purchase_data = {
        "purchased": True,
        "lifeExpectancy": 3,
        "warrantyDate": warranty_date,
        "vendor": vendor_name,
        "poDate": po_date,
        "poNumber": device.order_number
    }
    
    return purchase_data

def update_jamf_computer(computer_id: int, purchase_data: Dict, jamf_token: str, jamf_server_url: str, dry_run: bool = False) -> bool:
    """
    Update computer purchasing information in Jamf Pro using v1 API
    
    Args:
        computer_id: Jamf Pro computer ID
        purchase_data: Purchase information to update
        jamf_token: Jamf Pro API token
        jamf_server_url: Jamf Pro server URL
        dry_run: If True, only log what would be updated without making changes
        
    Returns:
        True if successful (or if dry run), False otherwise
    """
    if dry_run:
        logger.info(f"DRY RUN: Would update computer ID {computer_id}")
        logger.info(f"DRY RUN: Purchase data: {json.dumps(purchase_data, indent=2)}")
        return True
    
    url = f"{jamf_server_url}/api/v1/computers-inventory-detail/{computer_id}"
    headers = {
        'Authorization': f'Bearer {jamf_token}',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    
    # Create JSON payload for v1 API
    json_payload = {
        "purchasing": {
            "purchased": purchase_data['purchased'],
            "lifeExpectancy": purchase_data['lifeExpectancy'],
            "warrantyDate": purchase_data['warrantyDate'],
            "vendor": purchase_data['vendor'],
            "poDate": purchase_data['poDate'],
            "poNumber": purchase_data['poNumber']
        }
    }
    
    response = requests.patch(url, headers=headers, json=json_payload)
    
    # Check for token expiration
    if response.status_code == 401:
        raise TokenExpiredError("Jamf Pro token expired during computer update")
    
    if response.status_code == 200:
        logger.info(f"Successfully updated computer ID {computer_id}")
        return True
    else:
        logger.error(f"Failed to update computer ID {computer_id}: {response.status_code}")
        logger.error(f"Response: {response.text}")
        return False

def sync_devices_optimized(abm_token: str, jamf_token: str, jamf_server_url: str, test_limit: Optional[int] = None, dry_run: bool = False):
    """
    Optimized sync function that bulk fetches Jamf computers for faster processing
    
    Args:
        abm_token: Apple Business Manager API token
        jamf_token: Jamf Pro API token
        jamf_server_url: Jamf Pro server URL
        test_limit: Optional limit on number of devices to process for testing
        dry_run: If True, show what would be updated without making changes
    """
    logger.info("Starting optimized device sync process...")
    
    if test_limit:
        logger.info(f"TEST MODE: Processing only {test_limit} devices")
    
    if dry_run:
        logger.info("DRY RUN MODE: No actual updates will be made")
    
    # Load vendor mapping
    vendor_mapping = load_vendor_mapping()
    
    # Counters for reporting
    total_devices = 0
    found_in_jamf = 0
    updated_successfully = 0
    failed_updates = 0
    not_found_in_jamf = 0
    token_refreshes = 0
    
    # Keep track of current Jamf token
    current_jamf_token = jamf_token
    
    # Step 1: Get all devices from Apple Business Manager
    abm_devices = get_devices_from_abm(abm_token)
    total_devices = len(abm_devices)
    
    # Step 2: Bulk fetch all Jamf computers (with token refresh on expiration)
    max_retries = 2
    jamf_computers = None
    
    for attempt in range(max_retries):
        try:
            jamf_computers = get_all_jamf_computers(current_jamf_token, jamf_server_url)
            break  # Success, exit retry loop
        except TokenExpiredError:
            if attempt < max_retries - 1:  # Don't refresh on last attempt
                logger.warning("Jamf Pro token expired during bulk fetch, refreshing...")
                try:
                    current_jamf_token = get_token_from_script("get_jamf_token.sh", "Jamf Pro")
                    token_refreshes += 1
                    logger.info("Successfully refreshed Jamf Pro token")
                    continue  # Retry with new token
                except Exception as e:
                    logger.error(f"Failed to refresh Jamf Pro token: {e}")
                    raise
            else:
                logger.error("Failed to bulk fetch computers after token refresh")
                raise
    
    if not jamf_computers:
        logger.error("Failed to retrieve Jamf computers, cannot continue")
        return
    
    logger.info(f"Optimization complete: {len(jamf_computers)} computers available for instant lookup")
    
    # Step 3: Process each ABM device using fast lookup
    for i, device in enumerate(abm_devices):
        # Check test limit
        if test_limit and i >= test_limit:
            logger.info(f"TEST MODE: Stopping after {test_limit} devices")
            break
            
        logger.info(f"Processing device {i+1}/{total_devices if not test_limit else test_limit}: {device.serial_number}")
        
        # Step 4: Fast lookup in Jamf computers dictionary
        jamf_computer = jamf_computers.get(device.serial_number)
        
        if not jamf_computer:
            logger.warning(f"Device {device.serial_number} not found in Jamf Pro")
            not_found_in_jamf += 1
            continue
        
        found_in_jamf += 1
        
        # Step 5: Get computer ID from lookup
        computer_id = jamf_computer['id']
        
        # Step 6: Create purchase data with vendor mapping
        purchase_data = create_jamf_purchase_data(device, vendor_mapping)
        
        if dry_run:
            logger.info(f"DRY RUN: Would update computer ID {computer_id}")
        else:
            logger.info(f"Updating computer ID {computer_id} with purchase data: {purchase_data}")
        
        # Step 7: Update Jamf Pro (with token refresh on expiration)
        for attempt in range(max_retries):
            try:
                if update_jamf_computer(computer_id, purchase_data, current_jamf_token, jamf_server_url, dry_run=dry_run):
                    updated_successfully += 1
                else:
                    failed_updates += 1
                break  # Success or failure, exit retry loop
            except TokenExpiredError:
                if attempt < max_retries - 1:  # Don't refresh on last attempt
                    logger.warning("Jamf Pro token expired during update, refreshing...")
                    try:
                        current_jamf_token = get_token_from_script("get_jamf_token.sh", "Jamf Pro")
                        token_refreshes += 1
                        logger.info("Successfully refreshed Jamf Pro token")
                        continue  # Retry with new token
                    except Exception as e:
                        logger.error(f"Failed to refresh Jamf Pro token: {e}")
                        failed_updates += 1
                        break
                else:
                    logger.error("Failed to update computer after token refresh")
                    failed_updates += 1
                    break
    
    # Step 8: Report results
    logger.info("=== OPTIMIZED SYNC COMPLETED ===")
    if test_limit:
        logger.info(f"TEST MODE: Processed {min(test_limit, total_devices)} of {total_devices} devices")
    if dry_run:
        logger.info("DRY RUN MODE: No actual changes were made")
    if token_refreshes > 0:
        logger.info(f"Jamf Pro token refreshed {token_refreshes} times during sync")
    
    # Performance metrics
    jamf_lookup_time_saved = (found_in_jamf + not_found_in_jamf) * 0.5  # Estimate 0.5s per API call saved
    logger.info(f"Performance: Saved approximately {jamf_lookup_time_saved:.1f} seconds with bulk lookup optimization")
    
    logger.info(f"Total ABM devices: {total_devices}")
    logger.info(f"Found in Jamf Pro: {found_in_jamf}")
    logger.info(f"{'Would be updated' if dry_run else 'Updated successfully'}: {updated_successfully}")
    logger.info(f"{'Would fail to update' if dry_run else 'Failed updates'}: {failed_updates}")
    logger.info(f"Not found in Jamf Pro: {not_found_in_jamf}")

def main():
    """
    Main function - configure your shell scripts and server URL here
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Optimized sync of device purchase information from Apple Business Manager to Jamf Pro')
    parser.add_argument('--test', type=int, metavar='N', help='Test mode: only process N devices (e.g., --test 2)')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode: show what would be updated without making changes')
    args = parser.parse_args()
    
    # Configuration
    JAMF_SERVER_URL = "https://your-jamf-server.com"
    
    try:
        # Get tokens from shell scripts
        ABM_TOKEN = get_token_from_script("get_abm_token.sh", "Apple Business Manager")
        JAMF_TOKEN = get_token_from_script("get_jamf_token.sh", "Jamf Pro")
        
        sync_devices_optimized(ABM_TOKEN, JAMF_TOKEN, JAMF_SERVER_URL, test_limit=args.test, dry_run=args.dry_run)
        
    except Exception as e:
        logger.error(f"Optimized sync failed: {e}")
        raise

if __name__ == "__main__":
    main()
