# Simple Azure DevOps Pipeline: Azure Repos, Jenkins, and Terraform

This guide demonstrates a minimal DevOps pipeline using Azure Repos, Jenkins, and Terraform to provision Azure infrastructure. The goal is to show how these technologies integrate in a straightforward workflow.

## Stack

- **Azure Repos** – Source control
- **Jenkins** (Java 21) – CI/CD automation
- **Terraform** – Infrastructure as Code (IaC)

## Getting Started

1. **Create an empty repository** in Azure Repos.
2. **Clone the repository** to your local machine using VS Code or any preferred IDE.

Azure DevOps: [https://dev.azure.com/](https://dev.azure.com/)

## Overview

This example pipeline provisions a single Azure Resource Group. It demonstrates the integration between source control, CI/CD, and IaC tools.

### Prerequisites

- **Azure Service Principal**:  
    Create a Service Principal in Azure Entra with a password. Assign it the Contributor RBAC role to allow infrastructure changes.

- **Jenkins Secrets**:  
    Store sensitive parameters (IDs, secrets) in Jenkins credentials to avoid exposing them in code.

- **Jenkins & Terraform Integration**:  
    Pass required parameters from Jenkins to Terraform as environment variables to minimize risks and keep secrets secure.


## Project Structure

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

### `variables.tf`

```hcl
variable "resource_group_name" {
    description = "Name of the Azure Resource Group"
    type        = string
    default     = "sandbox-01-rg"
}

variable "location" {
    description = "Azure location/region"
    type        = string
    default     = "West Europe"
}
```

### `Jenkinsfile`

```groovy
pipeline {
    agent any

    environment {
        ARM_CLIENT_ID       = credentials('AZURE_CLIENT_ID')
        ARM_CLIENT_SECRET   = credentials('AZURE_CLIENT_SECRET')
        ARM_SUBSCRIPTION_ID = credentials('SUBSCRIPTION_ID')
        ARM_TENANT_ID       = credentials('AZURE_TENANT_ID')
    }

    stages {
        stage('Checkout') {
            steps {
                git branch: 'main', url: 'https://dev.azure.com/<your-org>/<your-project>/_git/<your-repo>'
            }
        }
        stage('Terraform Init') {
            steps {
                powershell 'terraform init'
            }
        }
        stage('Terraform Plan') {
            steps {
                powershell 'terraform plan -out=tfplan'
            }
        }
        stage('Terraform Apply') {
            steps {
                powershell 'terraform apply -auto-approve tfplan'
            }
        }
    }
}
```
