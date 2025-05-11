#!/bin/bash
# Use Jamf API to get information
# usage jamf_get_token.sh 
# https://developer.jamf.com/jamf-pro/reference
# By Omri Kedem 08/2024
# first export your client secret: export gen_k="my-secret-xxxxx"
# then change your server URL and client_id

url="https://your-server.jamfcloud.com"
client_id="xxx-xxx-xxxx-xxxx"
client_secret=$gen_k

getAccessToken() {
        response=$(curl --silent --location --request POST "${url}/api/oauth/token" \
                --header "Content-Type: application/x-www-form-urlencoded" \
                --data-urlencode "client_id=${client_id}" \
                --data-urlencode "grant_type=client_credentials" \
                --data-urlencode "client_secret=${client_secret}")
        access_token=$(echo "$response" | plutil -extract access_token raw -)
        token_expires_in=$(echo "$response" | plutil -extract expires_in raw -)
        token_expiration_epoch=$(($current_epoch + $token_expires_in - 1))
}

checkTokenExpiration() {
        current_epoch=$(date +%s)
    if [[ token_expiration_epoch -ge current_epoch ]]
    then
        echo "Token valid until the following epoch time: " "$token_expiration_epoch"
    else
        echo "No valid token available, getting new token"
        getAccessToken
    fi
}

invalidateToken() {
        responseCode=$(curl -w "%{http_code}" -H "Authorization: Bearer ${access_token}" $url/api/v1/auth/invalidate-token -X POST -s -o /dev/null)
        if [[ ${responseCode} == 204 ]]
        then
                echo "Token successfully invalidated"
                access_token=""
                token_expiration_epoch="0"
        elif [[ ${responseCode} == 401 ]]
        then
                echo "Token already invalid"
        else
                echo "An unknown error occurred invalidating the token"
        fi
}


getAccessToken
echo $access_token
