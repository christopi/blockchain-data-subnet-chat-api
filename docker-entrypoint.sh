#!/bin/bash
# Retrieve the secret JSON from AWS Secrets Manager
SECRET_JSON=$(aws secretsmanager get-secret-value --secret-id API_KEY --query SecretString --output text --region us-east-1)
#
# Extract the API key using jq
API_KEY=$(echo $SECRET_JSON | jq -r '.API_KEY')
#
# Export the API key as an environment variable
export API_KEY=$API_KEY
#
# Execute the Docker CMD
exec "$@"
# !/bin/bash

