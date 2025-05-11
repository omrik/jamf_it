#!/bin/bash
#
# Example script for generating application usage reports
# 
# This script runs the jamf_app_usage.py script for multiple applications
# and creates usage reports for each one.

# Configuration
REPORTS_DIR="./reports/usage/$(date +%Y-%m-%d)"
GROUP="All_Macs"  # Set to your group name or leave empty for all computers

# API Authentication - using environment variables for security
# Uncomment and set these if not already set in your environment
# export JAMF_URL="https://your-instance.jamfcloud.com"
# export JAMF_CLIENT_ID="your-client-id" 
# export JAMF_CLIENT_SECRET="your-super-secret-key"

# List of applications to analyze
APPLICATIONS=(
  "Microsoft Word.app"
  "Microsoft Excel.app"
  "Microsoft PowerPoint.app"
  "Google Chrome.app"
  "Slack.app"
  "Zoom.app"
)

# Create reports directory
mkdir -p "$REPORTS_DIR"
echo "Reports will be saved to: $REPORTS_DIR"

# Run usage report for each application
for app in "${APPLICATIONS[@]}"; do
  echo "---------------------------------------------"
  echo "Processing application: $app"
  echo "---------------------------------------------"
  
  # Create a sanitized filename from the app name
  filename=$(echo "$app" | sed 's/[^a-zA-Z0-9]/_/g' | sed 's/\.app//g')
  
  # Build the command
  cmd="../jamf_app_usage.py -t -a \"$app\" -o \"$REPORTS_DIR/${filename}_usage.csv\""
  
  # Add group parameter if specified
  if [ ! -z "$GROUP" ]; then
    cmd="$cmd -g \"$GROUP\""
  fi
  
  # Execute the command
  eval $cmd
  
  echo "Completed processing for: $app"
  echo ""
done

echo "All reports generated successfully!"
echo "Reports are available in: $REPORTS_DIR"
