#!/bin/bash
# Jamf API token script
# Usage: jamf_get_token.sh 
# https://developer.jamf.com/jamf-pro/reference
#
# Before running, set these environment variables:
# export JAMF_URL="https://your-instance.jamfcloud.com"
# export JAMF_CLIENT_ID="your-client-id"
# export JAMF_CLIENT_SECRET="your-client-secret"
# 
# Script will return the access token for use with other scripts

# Check if required environment variables are set
if [ -z "$JAMF_URL" ] || [ -z "$JAMF_CLIENT_ID" ] || [ -z "$JAMF_CLIENT_SECRET" ]; then
    echo "Error: Missing environment variables" >&2
    exit 1
fi

url=$JAMF_URL
client_id=$JAMF_CLIENT_ID
client_secret=$JAMF_CLIENT_SECRET

getAccessToken() {
    response=$(curl --silent --location --request POST "${url}/api/oauth/token" \
            --header "Content-Type: application/x-www-form-urlencoded" \
            --data-urlencode "client_id=${client_id}" \
            --data-urlencode "grant_type=client_credentials" \
            --data-urlencode "client_secret=${client_secret}")
    
    # Try to extract token with plutil (macOS)
    if command -v plutil >/dev/null 2>&1; then
        access_token=$(echo "$response" | plutil -extract access_token raw - 2>/dev/null)
        token_expires_in=$(echo "$response" | plutil -extract expires_in raw - 2>/dev/null)
    fi
    
    # If plutil failed or isn't available, try using alternative methods
    if [ -z "$access_token" ]; then
        if command -v jq >/dev/null 2>&1; then
            # Use jq if available
            access_token=$(echo "$response" | jq -r '.access_token')
            token_expires_in=$(echo "$response" | jq -r '.expires_in')
        else
            # Fallback to grep/cut
            access_token=$(echo "$response" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
            token_expires_in=$(echo "$response" | grep -o '"expires_in":[^,}]*' | cut -d':' -f2)
        fi
    fi
    
    # Calculate expiration time
    current_epoch=$(date +%s)
    token_expiration_epoch=$(($current_epoch + $token_expires_in - 1))
}

checkTokenExpiration() {
    current_epoch=$(date +%s)
    if [[ token_expiration_epoch -ge current_epoch ]]; then
        echo "Token valid until the following epoch time: " "$token_expiration_epoch"
    else
        echo "No valid token available, getting new token"
        getAccessToken
    fi
}

invalidateToken() {
    responseCode=$(curl -w "%{http_code}" -H "Authorization: Bearer ${access_token}" $url/api/v1/auth/invalidate-token -X POST -s -o /dev/null)
    if [[ ${responseCode} == 204 ]]; then
        echo "Token successfully invalidated"
        access_token=""
        token_expiration_epoch="0"
    elif [[ ${responseCode} == 401 ]]; then
        echo "Token already invalid"
    else
        echo "An unknown error occurred invalidating the token"
    fi
}

# Get a token and output it
getAccessToken

# Check if token was obtained
if [ -z "$access_token" ]; then
    echo "Error: Failed to obtain token. API response: $response" >&2
    exit 1
fi

# Output just the token (will be captured by the Python script)
echo $access_token
