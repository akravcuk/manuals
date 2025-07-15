#!/bin/bash

# 1. Get access token for Azure Key Vault
TOKEN=$(curl -s -H "Metadata: true" \
  "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2021-01-01&resource=https://vault.azure.net" \
  | jq -r .access_token)

# 2. Define vault and secret
VAULT_NAME="myvault"
SECRET_NAME="mysecret"

# 3. Query the secret from Key Vault
SECRET_VALUE=$(curl -s -H "Authorization: Bearer $TOKEN" \
  "https://${VAULT_NAME}.vault.azure.net/secrets/${SECRET_NAME}?api-version=7.4" \
  | jq -r .value)

echo "Secret value: $SECRET_VALUE"
