#!/usr/bin/env python3
"""
Apple Business Manager and Jamf Pro Purchase Information Comparison Tool - Optimized Version
Compares purchase information between ABM and Jamf Pro without making any changes.

This optimized version improves performance by:
- Fetching all Jamf computers in bulk at startup
- Creating an in-memory lookup dictionary by serial number
- Eliminating individual API calls for device lookups
- Maintaining all original functionality and output formats

Author: IT Team
Version: 2.0 (Optimized)
"""

import requests
import json
import logging
import subprocess
import os
import argparse
import csv
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs

# Configure logging for better visibility of operations
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ABMDevice:
    """
    Data class representing a device from Apple Business Manager
    
    Contains all the purchase-related information we need from ABM API
    """
    serial_number: str
    added_to_org_date: str
    order_number: str
    purchase_source_type: str
    purchase_source_id: str
    device_model: str = ""

@dataclass 
class JamfDevice:
    """
    Data class representing a device's purchasing info from Jamf Pro
    
    Contains the current purchasing information stored in Jamf Pro
    """
    serial_number: str
    computer_id: int
    purchased: bool
    life_expectancy: Optional[int]
    warranty_date: Optional[str]
    vendor: Optional[str]
    po_date: Optional[str]
    po_number: Optional[str]

@dataclass
class PurchaseComparison:
    """
    Data class representing the comparison result between ABM and Jamf Pro
    
    Contains the differences found between the two systems for a single device
    """
    serial_number: str
    computer_id: int
    abm_data: ABMDevice
    jamf_data: JamfDevice
    differences: Dict[str, Tuple[str, str]]  # field: (abm_value, jamf_value)

def get_token_from_script(script_name: str, token_type: str = "API") -> str:
    """
    Execute a shell script to retrieve an API token
    
    This function runs external shell scripts that handle token generation/retrieval
    for both ABM and Jamf Pro APIs. The scripts should output only the token.
    
    Args:
        script_name: Name of the shell script to execute (e.g., 'get_abm_token.sh')
        token_type: Type of token for logging purposes (e.g., 'Apple Business Manager')
        
    Returns:
        API token as string
        
    Raises:
        ValueError: If script returns empty token
        subprocess.CalledProcessError: If script execution fails
    """
    try:
        # Execute the shell script and capture its output
        result = subprocess.run(
            [f"./{script_name}"],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Extract token from stdout and clean whitespace
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
    
    This allows converting cryptic vendor IDs (like 'A7B9C2D') to readable names
    (like 'TechSource Solutions'). The mapping file is optional - if not found, vendor IDs
    will be used as-is.
    
    Args:
        mapping_file: Path to the vendor mapping JSON file
        
    Returns:
        Dictionary mapping vendor IDs to vendor names
        
    Example mapping file content:
        {
            "A7B9C2D": "TechSource Solutions",
            "F5E4A8B": "Global Systems Ltd",
            "2341567": "Apple"
        }
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
    Convert vendor ID to readable name using the mapping
    
    Args:
        vendor_id: Vendor ID from ABM (e.g., 'A7B9C2D')
        vendor_mapping: Dictionary mapping vendor IDs to names
        
    Returns:
        Vendor name if found in mapping, otherwise returns the vendor ID
        
    Example:
        get_vendor_name('A7B9C2D', {'A7B9C2D': 'TechSource Solutions'}) -> 'TechSource Solutions'
        get_vendor_name('UNKNOWN', {'A7B9C2D': 'TechSource Solutions'}) -> 'UNKNOWN'
    """
    return vendor_mapping.get(vendor_id, vendor_id)

def get_devices_from_abm(abm_token: str) -> List[ABMDevice]:
    """
    Fetch all devices from Apple Business Manager using pagination
    
    This function handles the ABM API's JSON API pagination format, which uses
    'links.next' URLs for pagination rather than simple cursor tokens.
    
    Args:
        abm_token: ABM API bearer token
        
    Returns:
        List of ABMDevice objects containing all devices from ABM
        
    Note:
        The ABM API returns data in pages of up to 100 devices each.
        This function automatically handles pagination to fetch all devices.
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
        # Build API request URL with pagination
        url = f"{base_url}/orgDevices"
        params = {"limit": 100}
        if cursor:
            params["cursor"] = cursor
        
        logger.info(f"Fetching page {page} from ABM...")
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Extract devices from the JSON API response
        device_list = data.get('data', [])
        logger.info(f"Found {len(device_list)} devices in page {page}")
        
        if not device_list:
            logger.info("No more devices found, pagination complete")
            break
        
        # Process each device and extract relevant attributes
        for device_data in device_list:
            attributes = device_data.get('attributes', {})
            
            device = ABMDevice(
                serial_number=attributes.get('serialNumber', ''),
                added_to_org_date=attributes.get('addedToOrgDateTime', ''),
                order_number=attributes.get('orderNumber', ''),
                purchase_source_type=attributes.get('purchaseSourceType', ''),
                purchase_source_id=attributes.get('purchaseSourceId', ''),
                device_model=attributes.get('deviceModel', '')
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

def get_all_jamf_computers_with_purchasing(jamf_token: str, jamf_server_url: str) -> Dict[str, JamfDevice]:
    """
    Fetch all computers with purchasing information from Jamf Pro using the modern API
    
    This optimized function bulk fetches all computers from Jamf Pro using the v1 API
    and creates an in-memory dictionary for fast serial number lookups, eliminating
    the need for individual API calls during the comparison process.
    
    Args:
        jamf_token: Jamf Pro API token
        jamf_server_url: Jamf Pro server URL
        
    Returns:
        Dictionary mapping serial numbers to JamfDevice objects
        
    Raises:
        Exception: If the Jamf Pro token expires or API call fails
    """
    logger.info("Bulk fetching all computers with purchasing info from Jamf Pro...")
    
    computers = []
    page = 0
    page_size = 100
    
    while True:
        # Use the v1 API to get computers with purchasing information
        url = f"{jamf_server_url}/api/v1/computers-inventory"
        headers = {
            'Authorization': f'Bearer {jamf_token}',
            'Accept': 'application/json'
        }
        
        params = {
            'page': page,
            'page-size': page_size,
            'sort': 'id:asc',
            'section': 'GENERAL,HARDWARE,PURCHASING'  # Get general, hardware, and purchasing sections
        }
        
        logger.info(f"Fetching computers page {page} from Jamf Pro...")
        response = requests.get(url, headers=headers, params=params)
        
        # Check for token expiration
        if response.status_code == 401:
            logger.error("Jamf Pro token expired during bulk computer fetch")
            logger.error("Please refresh your Jamf Pro token and try again")
            raise Exception("Jamf Pro token expired")
        
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
    
    # Create lookup dictionary by serial number with JamfDevice objects
    serial_lookup = {}
    
    for computer in computers:
        # Get serial number from hardware section (most reliable location)
        serial_number = None
        if 'hardware' in computer:
            serial_number = computer['hardware'].get('serialNumber')
        elif 'general' in computer:
            serial_number = computer['general'].get('serialNumber')
        
        if serial_number:
            # Extract purchasing information
            purchasing = computer.get('purchasing', {})
            
            # Create JamfDevice object for this computer
            jamf_device = JamfDevice(
                serial_number=serial_number,
                computer_id=computer.get('id'),
                purchased=purchasing.get('purchased', False),
                life_expectancy=purchasing.get('lifeExpectancy'),
                warranty_date=purchasing.get('warrantyExpiration'),
                vendor=purchasing.get('vendor'),
                po_date=purchasing.get('poDate'),
                po_number=purchasing.get('poNumber')
            )
            
            serial_lookup[serial_number] = jamf_device
    
    logger.info(f"Created lookup dictionary for {len(serial_lookup)} computers with purchasing info")
    return serial_lookup

def format_po_date(added_to_org_date: str) -> str:
    """
    Format purchase order date from ABM date
    
    Args:
        added_to_org_date: ISO format date string from ABM
        
    Returns:
        Formatted PO date in YYYY-MM-DD format
        
    Example:
        format_po_date('2021-11-25T08:25:53.921Z') -> '2021-11-25'
    """
    purchase_date = datetime.fromisoformat(added_to_org_date.replace('Z', '+00:00'))
    return purchase_date.strftime('%Y-%m-%d')

def compare_devices(abm_device: ABMDevice, jamf_device: JamfDevice, vendor_mapping: Dict[str, str]) -> PurchaseComparison:
    """
    Compare ABM and Jamf purchasing data for a single device
    
    This function performs field-by-field comparison between what ABM says the
    purchase information should be versus what's currently stored in Jamf Pro.
    Only compares fields that actually come from ABM data.
    
    Args:
        abm_device: Device data from ABM
        jamf_device: Device data from Jamf Pro
        vendor_mapping: Vendor ID to name mapping
        
    Returns:
        PurchaseComparison object containing any differences found
        
    Comparison logic:
        - vendor: Should be mapped vendor name from purchase_source_id
        - po_date: Should be ABM added_date (formatted)
        - po_number: Should be ABM order_number
    """
    differences = {}
    
    # Calculate expected values based on ABM data
    expected_vendor = get_vendor_name(abm_device.purchase_source_id, vendor_mapping)
    expected_po_date = format_po_date(abm_device.added_to_org_date)
    expected_po_number = abm_device.order_number
    
    # Compare each field and record differences
    if jamf_device.vendor != expected_vendor:
        differences['vendor'] = (expected_vendor, str(jamf_device.vendor))
    
    if jamf_device.po_date != expected_po_date:
        differences['po_date'] = (expected_po_date, str(jamf_device.po_date))
    
    if jamf_device.po_number != expected_po_number:
        differences['po_number'] = (expected_po_number, str(jamf_device.po_number))
    
    return PurchaseComparison(
        serial_number=abm_device.serial_number,
        computer_id=jamf_device.computer_id,
        abm_data=abm_device,
        jamf_data=jamf_device,
        differences=differences
    )

def export_missing_to_csv(missing_devices: List[ABMDevice], filename: str = "missing_devices.csv"):
    """
    Export missing devices to CSV file for analysis
    
    Args:
        missing_devices: List of devices that exist in ABM but not Jamf Pro
        filename: Output CSV filename
    """
    with open(filename, 'w', newline='') as csvfile:
        fieldnames = ['Serial Number', 'Model', 'Added to Org', 'Order Number', 'Purchase Source', 'Source ID']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for device in missing_devices:
            writer.writerow({
                'Serial Number': device.serial_number,
                'Model': device.device_model,
                'Added to Org': device.added_to_org_date,
                'Order Number': device.order_number,
                'Purchase Source': device.purchase_source_type,
                'Source ID': device.purchase_source_id
            })
    
    logger.info(f"Missing devices exported to {filename}")

def export_differences_to_csv(comparisons: List[PurchaseComparison], vendor_mapping: Dict[str, str], filename: str = "purchase_differences.csv"):
    """
    Export purchase differences to CSV file with proper vendor mapping
    
    Creates a spreadsheet with one row per device showing essential purchase fields
    from both ABM and Jamf Pro for easy comparison and analysis.
    
    Args:
        comparisons: List of device comparisons containing differences
        vendor_mapping: Vendor ID to name mapping (not used in current format)
        filename: Output CSV filename
    """
    with open(filename, 'w', newline='') as csvfile:
        fieldnames = [
            'serialNumber',
            'ABM_addedToOrgDateTime',
            'Jamf_poDate',
            'Jamf_warrantyDate',
            'ABM_orderNumber',
            'Jamf_poNumber',
            'ABM_purchaseSourceId',
            'Jamf_vendor'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for comparison in comparisons:
            writer.writerow({
                'serialNumber': comparison.serial_number,
                'ABM_addedToOrgDateTime': comparison.abm_data.added_to_org_date,
                'Jamf_poDate': comparison.jamf_data.po_date if comparison.jamf_data.po_date else '',
                'Jamf_warrantyDate': comparison.jamf_data.warranty_date if comparison.jamf_data.warranty_date else '',
                'ABM_orderNumber': comparison.abm_data.order_number,
                'Jamf_poNumber': comparison.jamf_data.po_number if comparison.jamf_data.po_number else '',
                'ABM_purchaseSourceId': comparison.abm_data.purchase_source_id,
                'Jamf_vendor': comparison.jamf_data.vendor if comparison.jamf_data.vendor else ''
            })
    
    logger.info(f"Purchase differences exported to {filename}")

def print_tabulated_comparison(comparison: PurchaseComparison):
    """
    Print a single device comparison in clean tabulated format
    
    This creates an easy-to-read table showing the differences between
    ABM and Jamf Pro for a single device, focusing only on fields that
    actually come from ABM.
    
    Args:
        comparison: Device comparison containing differences to display
        
    Example output:
        Serial Number: MXN8J2K9LM4P (Computer ID: 145)
        Model: MacBook Pro 13"
        Field                ABM                       Jamf
        ----------------------------------------------------------------------
        Vendor               TechSource Solutions      A7B9C2D
        Po Date              2021-11-25               None
        Po Number            PO-2021-78456            None
    """
    print(f"Serial Number: {comparison.serial_number} (Computer ID: {comparison.computer_id})")
    if comparison.abm_data.device_model:
        print(f"Model: {comparison.abm_data.device_model}")
    
    # Print table header
    print(f"{'Field':<20} {'ABM':<25} {'Jamf':<25}")
    print("-" * 70)
    
    # Print each difference in a clean format
    for field, (abm_value, jamf_value) in comparison.differences.items():
        field_display = field.replace('_', ' ').title()
        
        abm_display = str(abm_value) if abm_value else "None"
        jamf_display = str(jamf_value) if jamf_value else "None"
        
        print(f"{field_display:<20} {abm_display:<25} {jamf_display:<25}")
    
    print()  # Empty line after each device for readability

def show_missing_devices(abm_devices: List[ABMDevice], jamf_computers: Dict[str, JamfDevice], export_csv: bool = False):
    """
    Display and optionally export devices that exist in ABM but not in Jamf Pro (optimized version)
    
    This function checks every ABM device against the pre-loaded Jamf computers dictionary.
    Devices not found in Jamf Pro are candidates for enrollment or investigation.
    
    Args:
        abm_devices: List of all ABM devices
        jamf_computers: Pre-loaded dictionary of all Jamf computers
        export_csv: Whether to export results to CSV file
    """
    logger.info("Checking for devices in ABM but not in Jamf Pro...")
    
    missing_devices = []
    
    # Check each ABM device against the pre-loaded dictionary
    for i, abm_device in enumerate(abm_devices, 1):
        logger.info(f"Checking device {i}/{len(abm_devices)}: {abm_device.serial_number}")
        
        # Fast lookup in pre-loaded dictionary
        if abm_device.serial_number not in jamf_computers:
            missing_devices.append(abm_device)
    
    # Export to CSV if requested AND there are missing devices
    if export_csv and missing_devices:
        export_missing_to_csv(missing_devices)
    
    # Display results in clean format
    print("\n" + "="*80)
    print("DEVICES IN ABM BUT NOT IN JAMF PRO")
    print("="*80)
    
    if not missing_devices:
        print("✅ All ABM devices found in Jamf Pro!")
        return missing_devices  # Return empty list
    
    print(f"Found {len(missing_devices)} devices in ABM that are not in Jamf Pro:")
    print()
    
    # Print in tabulated format for easy reading
    print(f"{'Serial Number':<15} {'Model':<20} {'Added to Org':<12} {'Order Number':<20}")
    print("-" * 80)
    
    for device in missing_devices:
        added_date = device.added_to_org_date[:10] if device.added_to_org_date else "Unknown"
        model = device.device_model[:18] if device.device_model else "Unknown"
        order = device.order_number[:18] if device.order_number else "Unknown"
        
        print(f"{device.serial_number:<15} {model:<20} {added_date:<12} {order:<20}")
    
    if export_csv and missing_devices:
        print(f"\n📄 Detailed data exported to missing_devices.csv")
    
    return missing_devices  # Return the list for main function to check

def show_purchase_differences(abm_devices: List[ABMDevice], jamf_computers: Dict[str, JamfDevice], vendor_mapping: Dict[str, str], export_csv: bool = False):
    """
    Display and optionally export devices with purchase information differences (optimized version)
    
    This is the main comparison function that identifies devices where the
    purchase information in Jamf Pro doesn't match what ABM indicates it should be.
    Uses pre-loaded Jamf computers dictionary for fast lookups.
    
    Args:
        abm_devices: List of all ABM devices
        jamf_computers: Pre-loaded dictionary of all Jamf computers
        vendor_mapping: Vendor ID to name mapping
        export_csv: Whether to export results to CSV file
    """
    logger.info("Comparing purchase information between ABM and Jamf Pro...")
    
    devices_with_differences = []
    devices_in_sync = 0
    devices_not_in_jamf = 0
    
    # Compare each ABM device with its Jamf Pro counterpart using fast lookup
    for i, abm_device in enumerate(abm_devices, 1):
        logger.info(f"Comparing device {i}/{len(abm_devices)}: {abm_device.serial_number}")
        
        # Fast lookup in pre-loaded dictionary
        jamf_device = jamf_computers.get(abm_device.serial_number)
        
        if not jamf_device:
            devices_not_in_jamf += 1
            continue
        
        # Perform detailed comparison
        comparison = compare_devices(abm_device, jamf_device, vendor_mapping)
        
        if comparison.differences:
            devices_with_differences.append(comparison)
        else:
            devices_in_sync += 1
    
    # Export to CSV if requested
    if export_csv and devices_with_differences:
        export_differences_to_csv(devices_with_differences, vendor_mapping)
    
    # Display comprehensive results
    print("\n" + "="*80)
    print("PURCHASE INFORMATION COMPARISON")
    print("="*80)
    
    if not devices_with_differences:
        print("✅ All devices have matching purchase information!")
        print(f"\n📊 Summary:")
        print(f"  • Devices in sync: {devices_in_sync}")
        print(f"  • Devices with differences: {len(devices_with_differences)}")
        print(f"  • Devices not in Jamf Pro: {devices_not_in_jamf}")
        return
    
    print(f"Devices with purchase information differences:\n")
    
    # Print each device with differences in tabulated format
    for comparison in devices_with_differences:
        print_tabulated_comparison(comparison)
    
    # Display summary at the end
    print("="*80)
    print(f"📊 Summary:")
    print(f"  • Devices in sync: {devices_in_sync}")
    print(f"  • Devices with differences: {len(devices_with_differences)}")
    print(f"  • Devices not in Jamf Pro: {devices_not_in_jamf}")
    
    if export_csv:
        print(f"\n📄 Detailed data exported to purchase_differences.csv")

def main():
    """
    Main function - orchestrates the optimized comparison process
    
    Handles command line arguments, token retrieval, and coordinates the
    comparison operations using the optimized bulk fetch approach.
    """
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(
        description='Compare purchase information between Apple Business Manager and Jamf Pro (Optimized)',
        epilog="""
Examples:
  %(prog)s --diff                    # Show purchase differences (default)
  %(prog)s --missing                 # Show missing devices
  %(prog)s --all                     # Show both differences and missing
  %(prog)s --diff --output csv       # Export differences to CSV
  %(prog)s --all --output csv        # Export everything to CSV
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--diff', action='store_true', 
                       help='Show devices with purchase information differences')
    parser.add_argument('--missing', action='store_true', 
                       help='Show devices in ABM but not in Jamf Pro')
    parser.add_argument('--all', action='store_true', 
                       help='Show both differences and missing devices')
    parser.add_argument('--output', choices=['csv'], 
                       help='Export results to CSV files')
    
    args = parser.parse_args()
    
    # Default to showing differences if no specific option chosen
    if not (args.diff or args.missing or args.all):
        args.diff = True
    
    export_csv = args.output == 'csv'
    
    # Configuration - update this with your actual Jamf Pro server URL
    JAMF_SERVER_URL = "https://your-jamf-server.com"
    
    try:
        # Retrieve API tokens from shell scripts
        logger.info("Retrieving API tokens...")
        ABM_TOKEN = get_token_from_script("get_abm_token.sh", "Apple Business Manager")
        JAMF_TOKEN = get_token_from_script("get_jamf_token.sh", "Jamf Pro")
        
        # Load vendor mapping for readable vendor names
        vendor_mapping = load_vendor_mapping()
        
        # Fetch all devices from Apple Business Manager
        abm_devices = get_devices_from_abm(ABM_TOKEN)
        
        # OPTIMIZATION: Bulk fetch all Jamf computers with purchasing info
        jamf_computers = get_all_jamf_computers_with_purchasing(JAMF_TOKEN, JAMF_SERVER_URL)
        
        logger.info(f"Optimization complete: {len(jamf_computers)} computers available for instant lookup")
        
        # Calculate performance improvement
        lookup_time_saved = len(abm_devices) * 0.5  # Estimate 0.5s per API call saved
        logger.info(f"Performance: Saved approximately {lookup_time_saved:.1f} seconds with bulk lookup optimization")
        
        # Execute requested comparison operations using optimized functions
        csv_files_created = []
        
        if args.missing or args.all:
            missing_devices = show_missing_devices(abm_devices, jamf_computers, export_csv)
            if export_csv and missing_devices:
                csv_files_created.append("missing_devices.csv")
        
        if args.diff or args.all:
            show_purchase_differences(abm_devices, jamf_computers, vendor_mapping, export_csv)
            if export_csv:
                # Check if differences CSV would be created by comparing devices
                differences_count = 0
                for abm_device in abm_devices:
                    jamf_device = jamf_computers.get(abm_device.serial_number)
                    if jamf_device:
                        comparison = compare_devices(abm_device, jamf_device, vendor_mapping)
                        if comparison.differences:
                            differences_count += 1
                
                if differences_count > 0:
                    csv_files_created.append("purchase_differences.csv")
        
        if export_csv and csv_files_created:
            print(f"\n📊 CSV files generated: {', '.join(csv_files_created)}")
        elif export_csv:
            print(f"\n📊 No CSV files generated - no differences or missing devices found")
        
        logger.info("Optimized comparison completed successfully!")
        
    except Exception as e:
        logger.error(f"Comparison failed: {e}")
        raise

if __name__ == "__main__":
    main()
