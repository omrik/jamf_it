#!/bin/bash
# Check if required environment variables are set
if [ -z "$JAMF_URL" ] || [ -z "$JAMF_CLIENT_ID" ] || [ -z "$JAMF_CLIENT_SECRET" ]; then
    echo "Error: Missing environment variables" >&2
    exit 1
fi

# Get the token using client credentials
TOKEN=$(curl -s -X POST "$JAMF_URL/api/v1/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=$JAMF_CLIENT_ID&client_secret=$JAMF_CLIENT_SECRET" \
  | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# Output the token (this will be captured by the Python script)
echo "$TOKEN"
