# MySQL
## Server Parameters
```yaml
audit_log_enabled: ON
audit_log_events: 6 selected
    - CONNECTION
    - CONNECTION_V2
    - DCL 
    - DDL 
    - DML_NONSELECT
    - TABLE_ACCESS
innodb_adaptive_hash_index: OFF
audit_log_exclude_users: azure_superuser
audit_log_include_users: admin@domain.com
```

## Security
```yaml
Identity:
    - db-admin-access-managed-identity
    - db-managed-identity

Authentication:
    Type: Mysql and Entra
    User assigned MI: db-admin-access-mi
    Entra admin name: admin@domain.com
```

## Monitoring
```yaml
Diagnostic settings:
    Logs: audit
    Destination details:
        - Send to log analytics workspace
        - Archive to storage account
```

# Storage Account
## MySubscription
```yaml
Role name: Storage Blob Data Contributor
Assigned to: db-managed-identity
Role assignment condition:
(
  (
    ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write'}
    OR ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/add/action'}
    OR (ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write'} AND SubOperationMatches{'Blob.Write.WithTagHeaders'})
    OR (ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/add/action'} AND SubOperationMatches{'Blob.Write.WithTagHeaders'})
  )
  AND
  @Environment[Microsoft.Network/privateEndpoints] StringEquals '/subscriptions/<subscription-id>/resourceGroups/rgname/providers/Microsoft.Network/privateEndpoints/subscription-rgname-audit-logs-storage-pep'
)

Role name: Storage Blob Data Reader
Assigned to: cloud-admin@domain.com
```

## Lifecycle management
```yaml
If haven't modified in days move to:
    30: Cool
    90: Cold
```

## Security + networking
```yaml
Networking:
    Firewall:
        Enable from selected virtual networks and IP addresses
            Vnets: none
        Firewall:
            Address range: You trusted IPs
    PEP:
        Name: subscription-rgname-audit-logs-storage-pep
        DNS configuration:
            Private DNS zone: 
                Name: privatelink.blob.core.windows.net
                VNET links: None (TBD)       
```

# KeyVault
## MySubscription
```yaml
User Access Administorator: cloud-admin@domain.com
```

## Networking
```yaml
PEP:
    name: subscription-rgname-keyvault-pep
    subnet: vnet-subnet
    dns configuration:
        custom dns records:
            - fqdn: subscription-rgname-keyvault.vault.azure.net
```

## Objects
```yaml
Keys:
    -
        name: key-1
        MySubscription:
            Key Vault crypto officer: user-1@domain.com
            Key Vault secrets officer: user-2@domain.com
        
Secrets:
Certificates:
```

## Monitoring
```yaml
Diagnostic settings:
    Category: audit
    Destination details:
        - Send to log analytics workspace
        - Archive to storage account:
            Subscription: MySubscription
            Storage account: auditlogst
```