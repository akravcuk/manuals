# 🚀 Hybrid Access to Azure APIs with APIM + Entra ID + On-Prem Flask App

Modern architectures often require a **secure bridge between on-premises applications and cloud APIs**.  
This project demonstrates a **minimal hybrid setup** with:

- 🔹 An on-prem **Flask (Python)** application authenticating against **Microsoft Entra ID**  
- 🔹 Using the issued **JWT bearer token** to access APIs via **Azure API Management (APIM)**  
- 🔹 **APIM policies** validating tokens (issuer, audience, claims) before forwarding traffic  
- 🔹 Deployment of APIM fully automated with **Terraform**  

The application itself can run **anywhere** (local server, container, or cloud VM) → the core value is **token-based protection and hybrid flexibility**.

---

## ⚙️ Architecture Flow

1. User opens the Flask application → redirected to **Entra ID** login.  
2. Flask exchanges the **authorization code** for an **access token**.  
3. Application calls the **APIM frontend endpoint** with the token in `Authorization: Bearer ...`.  
4. **APIM Policy** validates the JWT and either forwards to backend or returns a mock response.  

---

## 🐍 Flask Application

```python
from flask import Flask, redirect, request
import requests, urllib.parse, jwt

app = Flask(__name__)
app.secret_key = "super-secret-key"     # Change

TENANT_ID =     ""
CLIENT_ID =     ""
CLIENT_SECRET = ""                      # Entra -> App registrations
REDIRECT_URI =  "http://localhost:5000/auth/redirect"

AUTH_URL =  f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/authorize"
TOKEN_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"

# Scope
SCOPE = ""

# URL APIM (frontend endpoint)
APIM_URL = "https://mayak-api.azure-api.net/mytestapi/get"


@app.route("/")
def index():
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "response_mode": "query",
        "scope": SCOPE,
        "state": "12345"
    }
    return redirect(AUTH_URL + "?" + urllib.parse.urlencode(params))


@app.route("/auth/redirect")
def auth_redirect():
    code = request.args.get("code")
    if not code:
        return {"error": "No code"}, 400
    data = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPE
    }

    token_resp = requests.post(TOKEN_URL, data=data).json()
    access_token = token_resp.get("access_token")
    if not access_token:
        return {"error": "Failed to get token", "details": token_resp}, 400

    # Call APIM with Token
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Ocp-Apim-Trace": "true"
    }

    apim_resp = requests.get(APIM_URL, headers=headers, timeout=10)

    trace_headers = {
        k: v for k, v in apim_resp.headers.items()
        if k.lower() in [
            "x-apim-trace-location",
            "x-azure-ref",
            "www-authenticate",
            "date",
            "content-type"
        ]
    }

    try:
        apim_body = apim_resp.json()
    except ValueError:
        apim_body = {"raw": apim_resp.text}

    return {
        "apim_status":  apim_resp.status_code,
        "apim_headers": trace_headers,
        "apim_response":apim_body
    }

# In Case if you don't want to use https://jwt.ms/
@app.route("/debug_claims")
def debug_claims():
    token = request.args.get("token")
    if not token:
        return {"error": "No token passed. Use /debug_claims?token=<JWT>"}, 400
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        return decoded
    except Exception as e:
        return {"error": str(e)}, 400

if __name__ == "__main__":
    app.run(port=5000, debug=True)
```

## 📜 APIM API Definition
```yaml
openapi: 3.0.1
info:
  title: myTestAPI
  version: '1.0'
servers:
  - url: https://mayak-api.azure-api.net/mytestapi
paths:
  /get:
    get:
      summary: GetTest
      operationId: gettest
      responses:
        '200':
          description: ''
components: { }
```

## 📜 APIM Policy
```xml
<policies>
    <inbound>
        <base />
        <validate-jwt header-name="Authorization" require-scheme="Bearer">
            <openid-config url="https://login.microsoftonline.com/<TENANT-ID>/v2.0/.well-known/openid-configuration" />
            <audiences>
                <audience>api://my-app-id</audience>
            </audiences>
            <issuers>
                <issuer>https://login.microsoftonline.com/<TENANT-ID>/v2.0</issuer>
            </issuers>
            <required-claims>
                <claim name="scp">
                    <value>Files.Read</value>
                </claim>
            </required-claims>
        </validate-jwt>
        <return-response>
            <set-status code="200" reason="OK" />
            <set-header name="Content-Type" exists-action="override">
                <value>application/json</value>
            </set-header>
            <set-body>@{
                return new JObject(
                    new JProperty("ok", true),
                    new JProperty("who", "APIM"),
                    new JProperty("note", "JWT validated; backend skipped")
                ).ToString();}
            </set-body>
        </return-response>
    </inbound>
    <backend>
        <base />
    </backend>
    <outbound>
        <base />
    </outbound>
    <on-error>
        <base />
    </on-error>
</policies>
```

## 🏗️ Terraform Template
```
resource "azurerm_api_management" "api" {
  location                      = "westeurope"
  name                          = "mayak-001-api"
  resource_group_name           = "apim-001-rg"
  publisher_email               = "admin@mayak.com"
  publisher_name                = "Mayak ltd"
  sku_name                      = "Basic_1"
  public_network_access_enabled = true
  notification_sender_email     = "apimgmt-noreply@mail.windowsazure.com"

  hostname_configuration {
    proxy {
      default_ssl_binding       = true
      host_name                 = "mayak-001-api.azure-api.net"
    }
  }
}
```