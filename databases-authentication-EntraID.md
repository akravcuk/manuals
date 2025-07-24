# Enabling Entra ID Authentication for Azure MySQL Flexible Server
## Skills Applied
Azure Identity, MySQL, Role-based Access Control (RBAC), Azure CLI

## Objective
Integrate identity-based access to Azure Database for MySQL Flexible Server using Entra ID (formerly Azure AD) for secure, token-based authentication — aligned with Zero Trust principles.


## Enabled Entra ID authentication via Azure Portal
Security > Authentication > Add authentication method

https://learn.microsoft.com/en-us/azure/mysql/flexible-server/concepts-azure-ad-authentication


## Configured MySQL client connection with Entra-issued OAuth token:
https://learn.microsoft.com/en-us/azure/mysql/flexible-server/how-to-azure-ad

```bash
TOKEN=$(az account get-access-token \
    --resource https://ossrdbms-aad.database.windows.net \
    --query accessToken \
    --output tsv)

mysql \
    -h <server>.mysql.database.azure.com \
    -u <user>@<tenant-domain> \
    -p $TOKEN
```

## Verified role assignment, token expiry handling, and conditional access scenarios.

## Impact

Eliminated password-based logins for DBAs and services.

Improved auditability and control via Azure Entra ID RBAC.

Prepared infrastructure for broader enterprise identity integration.

 #Azure #MySQL #EntraID #CloudSecurity #IdentityManagement #RBAC #DevOps #InfrastructureAsCode