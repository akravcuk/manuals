# Azure Cloud architecture patterns: Anti-corruption Layer

## Stack
- C# .NET Core
- Python Flask
- PostgreSQL or any other relational database (it will be boring w/o any db)

## Purpose
[Anti-corruption Layer pattern
 at Microsoft Learn](ttps://learn.microsoft.com/en-us/azure/architecture/patterns/anti-corruption-layer)

ACL acts as a translator, keeping old system flaws, architecture out of new ones.


## Short description
So we have one system and it's written with C#. Good, reliable and legacy. So. what we want is to develop the new one with regards to new best practices. Let's use different languages in illustration purposes.


## Components

1. **Legacy System**: The existing system that may have design flaws or outdated models.

```csharp
using Microsoft.AspNetCore.Builder;
using Microsoft.EntityFrameworkCore;
using Npgsql;

var builder = WebApplication.CreateBuilder(args);

// Connection string to PostgreSQL database
// Use Azure Key Vault or other secure methods to manage sensitive information in production
var connectionString = "Host=localhost;Database=labdb;Username=labuser;Password=labuser";

builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseNpgsql(connectionString));

var app = builder.Build();

app.MapGet("/", async () =>
{
    await using var conn = new NpgsqlConnection(connectionString);
    await conn.OpenAsync();

    await using var cmd = new NpgsqlCommand(
        "SELECT COUNT(*) FROM pg_catalog.pg_tables", conn);

    var count = await cmd.ExecuteScalarAsync();

    return Results.Ok(new { rowCount = count });
});

app.Run();

public class AppDbContext(DbContextOptions<AppDbContext> options) : DbContext(options);
```

2. **Modern Application**: The new system that needs to interact with the legacy system.

```python
import requests
from flask import Flask, jsonify

app = Flask(__name__)

# Just keep this endpoint with the code in demonstration purposes
# This is the example of corruption
@app.route('/old')
def index_old():
    try:
        response = requests.get('http://localhost:5000')
        count = response.json()['rowCount']
        return {"count": count}, 200
    except Exception as e:
        return {"error": str(e)}, 500


# This endpoint with the code is the example of ACL pattern
@app.route('/')
def index():
    try:
        response = requests.get('http://localhost:20000/members/count')
        count = response.json()['data']['count']
        return {"count": count}, 200
    except Exception as e:
        return {"error": str(e)}, 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
```

3. **Anti-corruption Layer (ACL)**: A layer that translates requests and responses between the legacy system and the modern application.

```python
import logging
import requests
from flask import Flask

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = Flask(__name__)
@app.route('/members/count')
def get_members_count():
    try:
        response = requests.get('http://localhost:5000', timeout=2)
        response.raise_for_status()

        number_of_members = int(response.json()['rowCount'])
        logger.info(f"Number of members retrieved: {number_of_members}")

        return {
            "status": "success",
            "data": {
                "count": number_of_members
            }
        }, 200

    except requests.exceptions.RequestException as e:
        error_msg = f"Error connecting to members service: {e}"
        logger.error(error_msg)
        
        return {
            "status": "error",
            "message": error_msg
        }, 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=20000)
```
