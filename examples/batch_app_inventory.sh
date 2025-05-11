#!/bin/bash
#
# Example script for running app inventory across multiple groups
# 
# This script runs the jamf_app_inventory.py script for multiple computer
# groups and creates separate reports for each one.

# Configuration
REPORTS_DIR="./reports/$(date +%Y-%m-%d)"
MIN_VERSION_COUNT=2

# API Authentication - using environment variables for security
# Uncomment and set these if not already set in your environment
# export JAMF_URL="https://your-instance.jamfcloud.com"
# export JAMF_CLIENT_ID="your-client-id" 
# export JAMF_CLIENT_SECRET="your-super-secret-key"

# List of groups to analyze
GROUPS=(
  "Marketing"
  "Finance"
  "Engineering"
  "Sales"
  "IT Department"
)

# Create reports directory
mkdir -p "$REPORTS_DIR"
echo "Reports will be saved to: $REPORTS_DIR"

# Run inventory for each group
for group in "${GROUPS[@]}"; do
  echo "---------------------------------------------"
  echo "Processing group: $group"
  echo "---------------------------------------------"
  
  # Run the app inventory script with token authentication
  ../jamf_app_inventory.py -t -g "$group" \
    -o "$REPORTS_DIR/inventory_${group// /_}" \
    --min-version-count $MIN_VERSION_COUNT
  
  echo "Completed processing for: $group"
  echo ""
done

echo "All reports generated successfully!"
echo "Reports are available in: $REPORTS_DIR"
