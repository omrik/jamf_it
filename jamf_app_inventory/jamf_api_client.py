#!/usr/bin/env python3
"""
Jamf API Client Library

A robust Python library for interacting with the Jamf Pro API.
Handles authentication, token management, rate limiting, and error recovery.

Author: Your Name
Version: 1.0.0
License: MIT
"""

import base64
import json
import requests
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from urllib3.exceptions import InsecureRequestWarning

# Suppress insecure HTTPS warnings
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

class JamfAPIClient:
    """Enhanced Jamf API client with token management and rate limiting."""
    
    def __init__(self, server, username=None, password=None, use_token=False, request_delay=0.5):
        """
        Initialize the Jamf API client.
        
        Args:
            server (str): Jamf Pro server URL
            username (str, optional): API username for basic auth
            password (str, optional): API password for basic auth
            use_token (bool): Whether to use token authentication
            request_delay (float): Delay between requests in seconds
        """
        self.server = server.rstrip('/')
        self.username = username
        self.password = password
        self.use_token = use_token
        self.token = None
        self.token_expiry = None
        self.last_request_time = 0
        self.request_delay = request_delay
        
    def get_fresh_token(self):
        """Get a fresh API token from the external script."""
        if self.use_token:
            try:
                token = subprocess.check_output(['bash', './jamf_get_token.sh'], encoding="utf-8").strip()
                self.token = token
                # Set token expiry to 25 minutes from now (5 minute buffer)
                self.token_expiry = time.time() + (25 * 60)
                return token
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                print(f"Error getting token: {e}", file=sys.stderr)
                return None
        return None
    
    def is_token_expired(self):
        """Check if the current token is expired or about to expire."""
        if not self.token_expiry:
            return True
        # Refresh token if it expires in the next 2 minutes
        return time.time() >= (self.token_expiry - 120)
    
    def get_auth_header(self):
        """Get the appropriate authentication header."""
        auth_header = {}
        
        if self.use_token:
            # Check if token needs refresh
            if not self.token or self.is_token_expired():
                print("Refreshing API token...")
                if not self.get_fresh_token():
                    raise Exception("Failed to obtain API token")
            auth_header = {'Authorization': f'Bearer {self.token}'}
        elif self.username and self.password:
            auth_string = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
            auth_header = {'Authorization': f'Basic {auth_string}'}
        else:
            raise Exception("No valid authentication method available")
        
        return auth_header
    
    def make_request(self, url, headers=None, max_retries=3, verify_ssl=True, timeout=30):
        """
        Make a rate-limited API request with retry logic.
        
        Args:
            url (str): Full URL for the API request
            headers (dict, optional): Additional headers for the request
            max_retries (int): Maximum number of retry attempts
            verify_ssl (bool): Whether to verify SSL certificates
            timeout (int): Request timeout in seconds
            
        Returns:
            requests.Response: The response object
        """
        # Rate limiting
        time_since_last = time.time() - self.last_request_time
        if time_since_last < self.request_delay:
            time.sleep(self.request_delay - time_since_last)
        
        if headers is None:
            headers = {}
        
        for attempt in range(max_retries):
            try:
                # Get fresh auth header (handles token refresh)
                auth_header = self.get_auth_header()
                request_headers = {**headers, **auth_header}
                
                response = requests.get(url, headers=request_headers, verify=verify_ssl, timeout=timeout)
                self.last_request_time = time.time()
                
                if response.status_code == 401:
                    print(f"Authentication error on attempt {attempt + 1}. Refreshing token...")
                    self.token = None  # Force token refresh
                    if attempt < max_retries - 1:
                        time.sleep(2)  # Brief pause before retry
                        continue
                
                response.raise_for_status()
                return response
                
            except requests.exceptions.RequestException as e:
                print(f"Request attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    print(f"Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise
        
        return None
    
    def get_computers(self, verify_ssl=True):
        """
        Fetch all computer IDs and names from Jamf Pro.
        
        Args:
            verify_ssl (bool): Whether to verify SSL certificates
            
        Returns:
            list: List of tuples containing (computer_id, computer_name)
        """
        url = f"{self.server}/JSSResource/computers"
        headers = {'Accept': 'application/json'}
        
        try:
            response = self.make_request(url, headers=headers, verify_ssl=verify_ssl)
            computers = response.json()['computers']
            return [(computer['id'], computer['name']) for computer in computers]
        except Exception as e:
            print(f"Error fetching computer IDs: {e}", file=sys.stderr)
            raise
    
    def get_computer_group_members(self, group_name, verify_ssl=True):
        """
        Fetch computers that belong to a specific computer group.
        
        Args:
            group_name (str): Name of the computer group
            verify_ssl (bool): Whether to verify SSL certificates
            
        Returns:
            list: List of tuples containing (computer_id, computer_name, serial_number)
        """
        url = f"{self.server}/JSSResource/computergroups/name/{group_name}"
        headers = {'Accept': 'application/json'}
        
        try:
            response = self.make_request(url, headers=headers, verify_ssl=verify_ssl)
            group_data = response.json()
            computer_list = []
            
            if 'computer_group' in group_data and 'computers' in group_data['computer_group']:
                for computer in group_data['computer_group']['computers']:
                    # Get serial number from computer details
                    detail_url = f"{self.server}/JSSResource/computers/id/{computer['id']}/subset/General"
                    try:
                        detail_response = self.make_request(detail_url, headers=headers, verify_ssl=verify_ssl)
                        details = detail_response.json()
                        
                        if 'general' in details['computer'] and 'serial_number' in details['computer']['general']:
                            serial_number = details['computer']['general']['serial_number']
                            computer_list.append((computer['id'], computer['name'], serial_number))
                        else:
                            computer_list.append((computer['id'], computer['name'], None))
                    except:
                        computer_list.append((computer['id'], computer['name'], None))
            
            return computer_list
        except Exception as e:
            print(f"Error fetching computer group '{group_name}': {e}", file=sys.stderr)
            raise
    
    def get_computer_application_usage(self, computer_id, computer_name, serial_number, start_date, end_date, verify_ssl=True):
        """
        Fetch application usage data for a specific computer.
        
        Args:
            computer_id (int): Computer ID
            computer_name (str): Computer name
            serial_number (str): Computer serial number
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format
            verify_ssl (bool): Whether to verify SSL certificates
            
        Returns:
            dict: Dictionary with application usage data or None if no data
        """
        # First try with serial number if available
        if serial_number:
            url = f"{self.server}/JSSResource/computerapplicationusage/serialnumber/{serial_number}/{start_date}_{end_date}"
        else:
            url = f"{self.server}/JSSResource/computerapplicationusage/id/{computer_id}/{start_date}_{end_date}"
        
        xml_headers = {'Accept': 'text/xml'}
        
        try:
            response = self.make_request(url, headers=xml_headers, verify_ssl=verify_ssl)
            
            if response.status_code == 404:
                return None
            
            # Parse XML response
            root = ET.fromstring(response.text)
            usage_data = {}
            
            # Process usage data
            for usage_entry in root.findall('.//usage'):
                date_elem = usage_entry.find('date')
                date = date_elem.text if date_elem is not None else "Unknown"
                
                apps = []
                for app_elem in usage_entry.findall('.//app'):
                    name_elem = app_elem.find('name')
                    foreground_elem = app_elem.find('foreground')
                    
                    if name_elem is not None and foreground_elem is not None:
                        try:
                            apps.append({
                                'name': name_elem.text,
                                'foreground': int(foreground_elem.text)
                            })
                        except (ValueError, TypeError):
                            pass
                
                usage_data[date] = apps
            
            return usage_data
            
        except Exception as e:
            print(f"Error fetching usage data for computer {computer_name} (ID: {computer_id}): {e}", file=sys.stderr)
            return None

def save_progress(filename, processed_items):
    """Save progress to a JSON file."""
    with open(filename, 'w') as f:
        json.dump(list(processed_items), f)

def load_progress(filename):
    """Load previously processed items from a JSON file."""
    try:
        with open(filename, 'r') as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()
