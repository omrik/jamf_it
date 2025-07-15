#!/usr/bin/env python3
"""
Apple Business Manager to Jamf Pro Device Sync Script
Syncs device purchase information from ABM to Jamf Pro with simplified logic.
"""

import requests
import json
import logging
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional

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

def get_devices_from_abm(abm_token: str) -> List[DeviceInfo]:
    """
    Fetch all devices from Apple Business Manager
    
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
    while True:
        # Build API request
        url = f"{base_url}/orgDevices"
        params = {"limit": 100}
        if cursor:
            params["cursor"] = cursor
        
        # Make request
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Process devices - Apple Business Manager uses 'data' array
        device_list = data.get('data', [])
        logger.info(f"Found {len(device_list)} devices in this batch")
        
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
        
        # Check for more pages
        cursor = data.get('cursor')
        if not cursor:
            break
    
    logger.info(f"Retrieved {len(devices)} devices from ABM")
    return devices

def find_jamf_computer(serial_number: str, jamf_token: str, jamf_server_url: str) -> Optional[Dict]:
    """
    Find a computer in Jamf Pro by serial number using Classic API
    
    Args:
        serial_number: Device serial number
        jamf_token: Jamf Pro API token
        jamf_server_url: Jamf Pro server URL
        
    Returns:
        Computer data or None if not found
    """
    url = f"{jamf_server_url}/JSSResource/computers/serialnumber/{serial_number}"
    headers = {
        'Authorization': f'Bearer {jamf_token}',
        'Accept': 'application/json'
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 404:
        return None
    
    response.raise_for_status()
    return response.json()

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

def create_jamf_purchase_data(device: DeviceInfo) -> Dict:
    """
    Create Jamf Pro purchasing data from ABM device information
    
    Args:
        device: DeviceInfo object from ABM
        
    Returns:
        Dictionary formatted for Jamf Pro purchasing update
    """
    # Calculate warranty date
    warranty_date = calculate_warranty_date(device.added_to_org_date)
    
    # Format purchase date
    purchase_date = datetime.fromisoformat(device.added_to_org_date.replace('Z', '+00:00'))
    po_date = purchase_date.strftime('%Y-%m-%d')
    
    # Build purchase data
    purchase_data = {
        "purchased": True,
        "lifeExpectancy": 3,
        "warrantyDate": warranty_date,
        "vendor": device.purchase_source_id,
        "poDate": po_date,
        "poNumber": device.order_number
    }
    
    return purchase_data

def update_jamf_computer(computer_id: int, purchase_data: Dict, jamf_token: str, jamf_server_url: str) -> bool:
    """
    Update computer purchasing information in Jamf Pro using v1 API
    
    Args:
        computer_id: Jamf Pro computer ID
        purchase_data: Purchase information to update
        jamf_token: Jamf Pro API token
        jamf_server_url: Jamf Pro server URL
        
    Returns:
        True if successful, False otherwise
    """
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
    
    if response.status_code == 200:
        logger.info(f"Successfully updated computer ID {computer_id}")
        return True
    else:
        logger.error(f"Failed to update computer ID {computer_id}: {response.status_code}")
        logger.error(f"Response: {response.text}")
        return False

def sync_devices(abm_token: str, jamf_token: str, jamf_server_url: str):
    """
    Main sync function - orchestrates the entire process
    
    Args:
        abm_token: Apple Business Manager API token
        jamf_token: Jamf Pro API token
        jamf_server_url: Jamf Pro server URL
    """
    logger.info("Starting device sync process...")
    
    # Counters for reporting
    total_devices = 0
    found_in_jamf = 0
    updated_successfully = 0
    failed_updates = 0
    not_found_in_jamf = 0
    
    # Step 1: Get all devices from Apple Business Manager
    abm_devices = get_devices_from_abm(abm_token)
    total_devices = len(abm_devices)
    
    # Step 2: Process each device
    for device in abm_devices:
        logger.info(f"Processing device: {device.serial_number}")
        
        # Step 3: Find device in Jamf Pro
        jamf_computer = find_jamf_computer(device.serial_number, jamf_token, jamf_server_url)
        
        if not jamf_computer:
            logger.warning(f"Device {device.serial_number} not found in Jamf Pro")
            not_found_in_jamf += 1
            continue
        
        found_in_jamf += 1
        
        # Step 4: Get computer ID
        computer_id = jamf_computer['computer']['general']['id']
        
        # Step 5: Create purchase data
        purchase_data = create_jamf_purchase_data(device)
        
        logger.info(f"Updating computer ID {computer_id} with purchase data: {purchase_data}")
        
        # Step 6: Update Jamf Pro
        if update_jamf_computer(computer_id, purchase_data, jamf_token, jamf_server_url):
            updated_successfully += 1
        else:
            failed_updates += 1
    
    # Step 7: Report results
    logger.info("=== SYNC COMPLETED ===")
    logger.info(f"Total ABM devices: {total_devices}")
    logger.info(f"Found in Jamf Pro: {found_in_jamf}")
    logger.info(f"Updated successfully: {updated_successfully}")
    logger.info(f"Failed updates: {failed_updates}")
    logger.info(f"Not found in Jamf Pro: {not_found_in_jamf}")

def main():
    """
    Main function - configure your shell scripts and server URL here
    """
    # Configuration
    JAMF_SERVER_URL = "https://your-jamf-server.com"
    
    try:
        # Get tokens from shell scripts
        ABM_TOKEN = get_token_from_script("get_abm_token.sh", "Apple Business Manager")
        JAMF_TOKEN = get_token_from_script("get_jamf_token.sh", "Jamf Pro")
        
        sync_devices(ABM_TOKEN, JAMF_TOKEN, JAMF_SERVER_URL)
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise

if __name__ == "__main__":
    main()
