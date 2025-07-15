# Steps to configure audit logs for Azure Database for MySQL Flexible Server

1. Deploy Log Analytics workspace

2. Deploy storage account if audit requires
2.1 Security + Networking 
2.2 Configure firewall rules for the storage account
2.2.1 Exceptions: Allow trusted Azure services (e.g. Log Analytics, Azure Monitor) to access the storage account  


3. Diagnostic settings
3.1 Enable audit logs into defined Log Analytics workspace
3.2 Set retention period for audit logs in Log Analytics workspace for the specific Table
3.3 Configure alert rules for critical events in Log Analytics workspace (failed login attempts, privilege grants, DDL changes)


4. Database server parameters
```ini
audit_log_enabled = ON
audit_log_events = CONNECTION, CONNECTION_V2, DCL, DDL, DML_NONSELECT, TABLE_ACCESS
audit_log_include_users = (must be empty)
audit_log_exclude_users = azure_superuser
```

5. KQL queries for Log Analytics workspace
```kql
AzureDiagnostics 
| where event_class_s has "LOG"
| project TimeGenerated, user_s, sql_text_s
| order by TimeGenerated
```

## Security Baseline
https://learn.microsoft.com/en-us/security/benchmark/azure/baselines/azure-database-for-mysql-flexible-server-security-baseline?wt.mc_id=knowledgesearch_inproduct_copilot-in-azure#lt-4-enable-logging-for-security-investigation


## Technical References
https://learn.microsoft.com/en-us/azure/mysql/flexible-server/tutorial-configure-audit#set-up-diagnostics

https://learn.microsoft.com/en-us/azure/mysql/flexible-server/concepts-monitor-mysql

https://learn.microsoft.com/en-us/azure/azure-monitor/platform/diagnostic-settings?WT.mc_id=Portal-Microsoft_Azure_Monitoring#destinations