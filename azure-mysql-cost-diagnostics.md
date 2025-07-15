Вот готовый `.md` файл с улучшенным форматом:

````markdown
# 🔍 Find Expensive Queries in Azure MySQL (via KQL)

> **Case**: Azure Database for MySQL Flexible Server appears overpriced compared to Azure Calculator estimate.  
> **Likely cause**: Missing indexes → slow, inefficient queries.

---

## ✅ Step 1: Enable Query Logging (if not yet)

In **Azure Portal** → MySQL Flexible Server → **Server parameters**:

```yaml
log_output: TABLE
log_queries_not_using_indexes: ON
slow_query_log: ON
long_query_time: 1  # or lower for profiling
````

> ⚠️ `FILE` is not supported in Azure — use `TABLE` only.

---

## ✅ Step 2: Stream Logs to Log Analytics

Azure Portal → **Monitoring** → **Diagnostic settings** → *Add Diagnostic Setting*
Ensure **slow query logs** are sent to **Log Analytics Workspace (LAW)**.

> 💡 Set **time retention** for the table carefully — this affects cost.

---

## 🔎 Step 3: Find Slow Queries with KQL

```kql
AzureDiagnostics
| where ResourceType == "FLEXIBLESERVERS" and Category == "MySqlSlowLogs"
| summarize
    executions = count(),
    avg_time = avg(query_time_d),
    max_time = max(query_time_d),
    p95_time = percentile(query_time_d, 95)
  by tostring(sql_text_s)
| extend total_time = avg_time * executions
| order by total_time desc
```

---

## 🔍 Step 4: Investigate Problem Queries

Take a heavy query (or procedure that triggers it):

```sql
-- If triggered by stored procedure:
SHOW CREATE PROCEDURE PeriodicQuery;

-- Extract query and run:
EXPLAIN SELECT id, name, surname, volume FROM clients WHERE age > 35;
```

---

### ❌ Before Index

```yaml
- id: 1
  select_type: SIMPLE
  table: clients
  type: ALL
  possible_keys: null
  key: null
  rows: 10000
  filtered: 5.0
  extra: Using where
```

---

### ✅ After Adding Index (e.g., on `age`)

```yaml
- id: 1
  select_type: SIMPLE
  table: clients
  type: range
  possible_keys: age
  key: age
  key_len: 5
  rows: 1905
  filtered: 100.0
  extra: Using index condition
```

---

## 💡 Outcome

Database now executes efficiently, avoids full scans, and aligns closer to estimated cost.

---