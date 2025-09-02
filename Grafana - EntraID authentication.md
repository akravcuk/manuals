# Simple Grafana + Microsoft Entra ID (Azure AD) via **App Roles**

**Works with Grafana 12.1.1. No Graph API. No implicit flow.**

## What you’ll build

* Sign-in with Microsoft (Entra ID) to Grafana
* Role mapping from **App roles** → Grafana roles (**Admin/Editor/Viewer**) using the `roles` claim in the ID token
* Minimal configuration, production-safe defaults

---

## 1) Register the application

**Entra ID → App registrations → New registration**

* **Name:** `grafana`
* **Supported accounts:** Single tenant
* **Redirect URIs (Web):**

  * `https://<YOUR-GRAFANA>/login/azuread`
  * For local testing: `http://localhost:3000/login/azuread`

**Authentication**

* **Platform:** Web
* **Implicit grant and hybrid flows:** **Do NOT enable** (leave both unchecked)
* **Allow public client flows:** Off (device code was only for debugging; not needed in prod)

**Certificates & secrets**

* Create a **Client secret** and save its **Value**

---

## 2) Token configuration

**Token configuration → Add groups claim** (optional but useful later)

* Group types: **Security groups**
* Include in: **ID token** (and Access if you want)
* **Important:** **Uncheck** “**Emit groups as role claims**”
  (you want **`roles: ["Admin" | "Editor" | "Viewer"]`**, not GUIDs)

---

## 3) App roles (the key)

**App registrations → grafana → App roles → Create three roles**

* **Admin** — Value: `Admin` — Allowed member types: *Users/Groups*
* **Editor** — Value: `Editor` — Allowed member types: *Users/Groups*
* **Viewer** — Value: `Viewer` — Allowed member types: *Users/Groups*
  Click **Apply**.

**Enterprise applications → grafana → Users and groups → Add assignment**

* Assign your **groups/users** to **Admin/Editor/Viewer** app roles
* (Optional) **Properties → User assignment required = Yes** to restrict sign-in to assigned users only

> **No Microsoft Graph permissions needed.** Remove any Graph API permissions you added earlier—Grafana won’t call Graph in this setup.

---

## 4) Grafana configuration

Edit **grafana.ini** (not `defaults.ini`):

```ini
#################################### Azure AD OAuth #######################
[auth.azuread]
enabled = true
name = Microsoft
icon = microsoft

; First login only; set to false after initial onboarding
allow_sign_up = true
auto_login = true

client_authentication = client_secret_post
client_id     = <CLIENT_ID>          ; Application (client) ID
client_secret = <CLIENT_SECRET>       ; Certificates & secrets → Value

; Your tenant (Directory) ID
auth_url  = https://login.microsoftonline.com/<TENANT_ID>/oauth2/v2.0/authorize
token_url = https://login.microsoftonline.com/<TENANT_ID>/oauth2/v2.0/token
scopes = openid email profile

; Keep it simple: no Graph API calls
force_use_graph_api = false

; Strict: deny login if role not resolved
role_attribute_strict = true

; Map App roles → Grafana roles (reads the ID token claim "roles")
role_attribute_path = contains(roles[*], 'Admin') && 'Admin' || \
                      contains(roles[*], 'Editor') && 'Editor' || \
                      contains(roles[*], 'Viewer') && 'Viewer' || \
                      'Viewer'

; Optional: restrict to your tenant only
allowed_organizations = <TENANT_ID>

; Not needed when using App roles:
; allowed_groups =
; org_mapping =
; groups_attribute_path =

use_pkce = true
skip_org_role_sync = false
use_refresh_token = true
```

If Grafana is behind a domain/proxy, also set:

```ini
[server]
domain = <YOUR-DOMAIN>
root_url = https://<YOUR-DOMAIN>/
```

Restart Grafana and sign in with Microsoft. After users are created, set `allow_sign_up = false`.

---

## 5) Why this works (and what was breaking)

* Grafana expects a **role** from the IdP. With App roles, your ID token contains:

  * `roles: ["Admin" | "Editor" | "Viewer"]` → **strings**, not GUIDs.
  * (Optional) `groups: ["<GUID>", ...]` for advanced org mapping if you ever need it.
* If you enable **“Emit groups as role claims”**, Entra fills **`roles` with GUIDs** of groups. Grafana can’t map GUIDs to `Admin/Editor/Viewer` → you get `role_attribute_strict_violation`. Turning that off fixes it.

---

## 6) Troubleshooting (30-second checklist)

* **role\_attribute\_strict\_violation**

  * Decode your ID token at `jwt.ms`.
  * Expect: `roles: ["Admin" | "Editor" | "Viewer"]`.
  * If you see GUIDs in `roles`, go to **Token configuration** and **uncheck “Emit groups as role claims”**.
* **User not created**

  * `allow_sign_up = true` for first login, then set to false.
* **User not allowed**

  * In Enterprise app: **User assignment required = Yes** + make sure the user/group is assigned to an **App role**.
* **Invalid redirect\_uri / 400**

  * The redirect URI in Entra must match your Grafana URL exactly.

---

## Optional: multi-org with group mapping

If you ever need to map **Entra groups** to different **Grafana orgs**, use:

```ini
; Example (Org ID 1 is the default):
org_mapping = <groupGuidA>:1:Admin,<groupGuidB>:1:Editor,*:1:Viewer
; If your groups are in the "groups" claim (default), no extra setting needed.
; If Entra ever put groups somewhere else, point Grafana there:
; groups_attribute_path = groups
```

Most deployments don’t need this when App roles already define who is Admin/Editor/Viewer.

---

## Security hygiene

* Rotate the **client secret** regularly (and immediately if it ever leaked).
* Keep **Public client flows** disabled.
* Prefer **User assignment required = Yes** in the Enterprise app.
* Limit by tenant via `allowed_organizations`.