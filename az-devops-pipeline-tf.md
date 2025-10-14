# Azure DevOps Pipeline with Terraform in 10 Minutes

**How to build your infrastructure fast and easy with Azure DevOps and Terraform**

---

## Stack

- **Azure**
- **Terraform**
- **Powershell on Windows or Linux**

---

## Establish the Environment

### 1. Create Azure DevOps Organization

Set up your **Azure DevOps Organization** and connect it to **Microsoft Entra ID**.  
This connection allows you to create and use a **Service Principal** for Terraform deployments.

---

### 2. Configure Build Agents

You need computing resources to execute your pipelines.
(Create 'Default' Agent pool before)
- Navigate to:  
  **Organization → Settings → Agent Pools → Default → Azure Pipelines → Agents → New Agent**
- Download and install the agent. Follow the official documentation:  
  [Register agent using PAT](https://learn.microsoft.com/en-us/azure/devops/pipelines/agents/personal-access-token-agent-registration?view=azure-devops)
- Use a **Personal Access Token (PAT)** for agent registration.

---

### 3. Create and Clone Repository

Create a **new repo** inside your Azure DevOps project and **clone** it locally.

---

## Terraform Setup

You only need two basic files to get started.

### `main.tf`
```hcl
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
  required_version = ">= 1.13.3"
}

provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.location
}
```
variables.tf
```hcl
variable "resource_group_name" {
  description = "Name of the Azure Resource Group"
  type        = string
  default     = "sandbox-02-rg"
}

variable "location" {
  description = "Azure location/region"
  type        = string
  default     = "West Europe"
}
```

## Azure Pipeline Setup

We'll define all pipeline steps in a YAML file called azure-pipeline.yaml.

### 1. Credentials

Terraform authenticates to Azure using environment variables.
You can manage them securely via a Variable Group in Azure DevOps.

Create a group. In this example we call it 'Terraform-secrets':
Pipelines → Library → + Variable Group → “Terraform-secrets”

Add all the following variables (mark secrets accordingly):

```
ARM_CLIENT_ID
ARM_CLIENT_SECRET
ARM_TENANT_ID
ARM_SUBSCRIPTION_ID
```
Important: Even if a variable group is linked, secrets like ARM_CLIENT_SECRET
must still be explicitly mapped to each step via **env:**.

azure-pipeline.yaml
```yaml
trigger:
- none

pool:
  name: 'Default'

variables:
  # Map secret from variable group
  - name: 'ARM_CLIENT_SECRET'
    value: $(CLIENT_SECRET)

  # Include all variables from the group
  - group: 'Terraform-secrets'

steps:
  - checkout: self
    displayName: 'Checkout repository'

  - powershell: |
      Write-Host "ARM_CLIENT_ID: $env:ARM_CLIENT_ID"
      Write-Host "ARM_TENANT_ID: $env:ARM_TENANT_ID"
      Write-Host "ARM_CLIENT_SECRET (length): $($env:ARM_CLIENT_SECRET.Length)"
    displayName: 'Display secret variable'
    env:
      ARM_CLIENT_SECRET: $(ARM_CLIENT_SECRET)

  - powershell: |
      Write-Host "Testing Azure Service Principal login..."
      az login --service-principal `
               --username "$env:ARM_CLIENT_ID" `
               --password "$env:ARM_CLIENT_SECRET" `
               --tenant "$env:ARM_TENANT_ID"
    displayName: 'Verify Azure SP login'
    env:
      ARM_CLIENT_SECRET: $(ARM_CLIENT_SECRET)

  - powershell: |
      terraform init
    displayName: 'Terraform Init'

  - powershell: |
      terraform fmt -check
      terraform validate
    displayName: 'Terraform Format & Validate'

  - powershell: |
      terraform plan -out=tfplan -input=false
    displayName: 'Terraform Plan'
    condition: succeeded()

  - powershell: |
      terraform apply -input=false tfplan
    displayName: 'Terraform Apply'
    condition: succeeded()
```
### Final Result

After successful pipeline execution, verify your deployment:
```sh
# get the list of groups
az group list -o table

# output
Name            Location     Status
--------------  ------------  ---------
sandbox-02-rg   westeurope    Succeeded

```

## Summary

| Step | Action                          | Output                  |
| ---- | ------------------------------- | ----------------------- |
| 1    | Create Azure DevOps Org & Agent | Connected runner ready  |
| 2    | Create Terraform files          | Declarative IaC config  |
| 3    | Add secrets & pipeline YAML     | Automated provisioning  |
| 4    | Run pipeline                    | Resource group deployed |

***Pro Tip:*** Add terraform destroy -auto-approve as a cleanup stage for sandbox environments.
Keeps Azure costs low and your conscience clear.
