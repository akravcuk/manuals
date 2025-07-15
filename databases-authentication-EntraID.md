# Enable Entra ID authentication with Azure MySQL Flexible Server

1. Security > Authentication > Add authentication method
https://learn.microsoft.com/en-us/azure/mysql/flexible-server/concepts-azure-ad-authentication


# Connect to Azure MySQL Flexible Server with Entra ID
https://learn.microsoft.com/en-us/azure/mysql/flexible-server/how-to-azure-ad

```bash
TOKEN=$(az account get-access-token \
    --resource https://ossrdbms-aad.database.windows.net \
    --query accessToken \
    --output tsv)

mysql \
    -h <database-name>.mysql.database.azure.com \
    -u <user-name>@<domain-name> \
    -p $TOKEN
```