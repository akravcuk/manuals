# Hands-On Lab: Deploying Flask on Kubernetes with Azure Key Vault Secret Sync

## Stack
- Azure
- Terraform
- Kubernetes
- Helm
- Flask + Python

## Architecture
- Model: IaaS
- Everything will be placed on a VM, so good for rehost and refactor


# Implementation
## Generate RSA ssh key for vm
```sh
ssh-keygen -t rsa -b 4096 -C "VM key"
```
## Create Azure infrastructure
### Format and validate
```sh
terraform fmt ; terraform validate
```
### Plan and apply
```sh
terraform plan
terraform apply
```

## Service Principal
Application connects to the database with the password which is stored in a Key Vault using Service Principal:
```sh
# Get the values
sp_client_id = "xxx"
sp_client_secret = <sensitive>
sp_object_id = "xxx"

# get the secret
terraform output -raw sp_client_secret
xxx
```

## Prepare infrastructure for the application
### Install Minikube
```sh
# get it
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# With regards to Standard_B2s otherwise adjust the size of the vm
minikube start --memory=2048

# Get the kubectl
sudo curl -L https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl -o /usr/local/bin/kubectl

sudo chmod +x /usr/local/bin/kubectl

# More suitable to have it's shortened
echo "alias k=kubectl" >> $HOME/.bashrc && source $HOME/.hashrc

# Check
k get nodes
```

### Install Helm
```sh
curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

## Install Secrets Store CSI Driver with Helm
We want to have out secrets in Keyvault being exported to the kubernetes secrets
hence used by our containerized apps

### Add official repo
```
helm repo add secrets-store-csi-driver https://kubernetes-sigs.github.io/secrets-store-csi-driver/charts
helm repo update
```

### Install driver to the Kubernetes cluster
```sh
# install
helm install csi-secrets-store secrets-store-csi-driver/secrets-store-csi-driver --namespace kube-system

# check
kubectl --namespace=kube-system get pods -l "app=secrets-store-csi-driver"
NAME                                               READY   STATUS    RESTARTS   AGE
csi-secrets-store-secrets-store-csi-driver-mw65b   3/3     Running   0          20s
```

### Install Azure KeyVault provider
```sh
# add repo
helm repo add csi-secrets-store-provider-azure https://azure.github.io/secrets-store-csi-driver-provider-azure/charts

# update
helm repo update

# install provider
kubectl apply -f https://raw.githubusercontent.com/Azure/secrets-store-csi-driver-provider-azure/master/deployment/provider-azure-installer.yaml

# check
k get daemonset
NAME                               DESIRED   CURRENT   READY   UP-TO-DATE   AVAILABLE   NODE SELECTOR            AGE
csi-secrets-store-provider-azure   1         1         1       1            1           kubernetes.io/os=linux   81s
```

### Link this secret to Service Provider Class in order to Kubernetes Az KV Provider could use client secret
```sh
k apply -f ./secret-provider-class.yaml
```

### Create kubernetes secret to access to SP
```sh
k apply -f ./kv-creds.yaml
kubectl get secret kv-creds -o yaml
```

### Check
```sh
# The template if below
k apply -f ./test-pod.yaml

k get pods
NAME                                     READY   STATUS    RESTARTS   AGE
busybox-secrets-test                     1/1     Running   0          21m
csi-secrets-store-provider-azure-pp5kp   1/1     Running   0          175m

# make sure that the password is available
k exec -it busybox-secrets-test -- ls /mnt/secrets
flask-db-password

# delete
k delete -f ./test-pod.yaml
```

## App
The simple piece of software which writes data to database and reads the last line. It has to connect to the database with the password taken from the keyvault.

### Database
```sh
# add repo
helm repo add cetic https://cetic.github.io/helm-charts

helm repo update

# install 
helm install my-postgres cetic/postgresql -f ./helm/postgres/values.yaml

# check
kubectl exec -it my-postgres-postgresql-0 -- psql -U postgres -c "SELECT version();"
Defaulted container "my-postgres-postgresql" out of: my-postgres-postgresql, init-chmod-data (init)
                                                      version
--------------------------------------------------------------------------------------------------------------------
 PostgreSQL 17.6 (Debian 17.6-2.pgdg13+1) on x86_64-pc-linux-gnu, compiled by gcc (Debian 14.2.0-19) 14.2.0, 64-bit
(1 row)
```

#### Create some db and a table
```sh
kubectl exec -it my-postgres-postgresql-0 -- psql -U postgres
```
Create
```sql
-- Remember to do not keep any secrets in deployment. We have this one for lab purposes
CREATE USER flaskuser WITH ENCRYPTED PASSWORD 'flaskpass';

CREATE DATABASE flaskdb OWNER flaskuser;

\c flaskdb flaskuser;

CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    text VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
#### Check
```sql
\du
\l
\dt
```

### Dockerize app
```sh
# Switch to local podman lab for simplicity
eval $(minikube docker-env)

# build
docker build -t flask-app:latest .

# check
docker images | grep flask-app
```

### Deploy and run
```sh
# deploy
k apply -f ./flask-deploy.yaml
k get pods

# check

# Get the url from the service to make sure that we can connect to out microservice
minikube service flask-hello-svc --url
http://192.168.49.2:30280


# Make a call
curl http://192.168.49.2:30280
{"created_at":"2025-10-07T11:45:04.836785","id":1,"text":"Hello from Flask"}

# One more - the id and the timestamp are increased
curl http://192.168.49.2:30280
{"created_at":"2025-10-07T11:45:06.215211","id":2,"text":"Hello from Flask"}
```
# Charts
main.tf
```sh
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.50"
    }
  }
}

provider "azurerm" {
  features {}

  subscription_id = var.subscription_id
  client_id       = var.client_id
  client_secret   = var.client_secret
  tenant_id       = var.tenant_id

}

provider "azuread" {
  tenant_id = var.tenant_id
}


resource "azurerm_resource_group" "rg" {
  name     = var.resource_group
  location = var.location
  tags     = { env = var.environment }
}
```

terraform.tvars
```sh

# Need for deployment
tenant_id       = "xxx"
subscription_id = "xxx"
client_id       = "xxx"
client_secret   = "xxx"

# Need for app
sp_client_id     = "xxx"
sp_client_secret = "xxx"
sp_object_id     = "xxx"


location       = "West Europe"
resource_group = "sandbox-01-rg"
environment    = "dev"

# networking
vnet_name     = "sandbox-vnet"
address_space = ["10.0.0.0/16"]

# snet
subnet_name   = "sandbox-01-snet"
subnet_prefix = ["10.0.1.0/24"]

# nsg
nsg_name = "sandbox-01-nsg"

# VM

# pip
pip_name = "sandbox-01-pip"
# nic
nic_name = "sandbox-01-nic"
# vm
vm_name        = "sandbox-01-vm"
vm_size        = "Standard_B1s"

# make sure that you have credentials separately stored
admin_username = "xxx"

# keyvault name
kv_name = "sandbox-02-kv"

###########################################
# This must not be hardcoded in production
# Added here for simplicity
############################################
# secret name
secret_name = "flask-db"
# secret value
secret_value = "xxx"
```

variables.tf
```sh
variable "tenant_id" {
  description = "Azure Tenant ID"
  type        = string
}

variable "subscription_id" {
  description = "Azure Subscription ID"
  type        = string
}

variable "client_id" {
  description = "Azure Service Principal App ID"
  type        = string
}

variable "client_secret" {
  description = "Azure Service Principal Password"
  type        = string
}


variable "sp_client_id" {
  description = "Service Principal client_id for accessing Key Vault"
  type        = string
}
variable "sp_client_secret" {
  description = "Service Principal client_secret for accessing Key Vault"
  type        = string
  sensitive   = true
}
variable "sp_object_id" {
  description = "Service Principal object_id for Key Vault access policy"
  type        = string
}

variable "location" {
  description = "Azure location for all resources"
  type        = string
}
variable "resource_group" {
  description = "Name of the resource group"
  type        = string
}
variable "environment" {
  description = "Environment tag for resources"
  type        = string
}
# networking
variable "vnet_name" {
  description = "Name of the Virtual Network"
  type        = string
}
variable "address_space" {
  description = "Address space for the Virtual Network"
  type        = list(string)
}
# snet
variable "subnet_name" {
  description = "Name of the Subnet"
  type        = string
}
variable "subnet_prefix" {
  description = "Address prefix for the Subnet"
  type        = list(string)
}
# nsg
variable "nsg_name" {
  description = "Name of the Network Security Group"
  type        = string
}
# VM
# pip
variable "pip_name" {
  description = "Name of the Public IP"
  type        = string
}
# nic
variable "nic_name" {
  description = "Name of the Network Interface"
  type        = string
}
# vm
variable "vm_name" {
  description = "Name of the Virtual Machine"
  type        = string
}
variable "vm_size" {
  description = "Size of the Virtual Machine"
  type        = string
}
variable "admin_username" {
  description = "Admin username for the Virtual Machine"
  type        = string
}

# keyvault name
variable "kv_name" {
  description = "Name of the Key Vault"
  type        = string
}
# This must not be hardcoded in production
# Added here for simplicity
# secret name
variable "secret_name" {
  description = "Name of the secret in Key Vault"
  type        = string
}
# secret value
variable "secret_value" {
  description = "Value of the secret in Key Vault"
  type        = string
}
```

networking.tf
```sh
resource "azurerm_virtual_network" "vnet" {
  name                = var.vnet_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  address_space       = var.address_space
}

resource "azurerm_subnet" "subnet" {
  name                 = var.subnet_name
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = var.subnet_prefix
}
```

vm.tf
```sh
resource "azurerm_linux_virtual_machine" "vm" {
  name                = var.vm_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  size                = "Standard_B2s"
  admin_username      = "xxx" #sensitive
  network_interface_ids = [
    azurerm_network_interface.nic.id,
  ]

  admin_ssh_key {
    username   = "xxx" #sensitive
    public_key = file(".ssh/id_rsa.pub")
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-focal"
    sku       = "20_04-lts-gen2"
    version   = "latest"
  }
}

resource "azurerm_network_interface" "nic" {
  name                = var.nic_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.subnet.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.pip.id
  }

}

resource "azurerm_network_interface_security_group_association" "nsg_assoc" {
  network_interface_id      = azurerm_network_interface.nic.id
  network_security_group_id = azurerm_network_security_group.nsg.id
}


resource "azurerm_network_security_group" "nsg" {
  name                = var.nsg_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_network_security_rule" "ssh" {
  name                        = "SSH"
  priority                    = 100
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "22"
  source_address_prefix       = "*" # fix later on
  destination_address_prefix  = "*"
  resource_group_name         = azurerm_resource_group.rg.name
  network_security_group_name = azurerm_network_security_group.nsg.name
}

resource "azurerm_public_ip" "pip" {
  name                = var.pip_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  allocation_method   = "Static"
  sku                 = "Standard"
}
```

keyvault.tf
```sh
data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "kv" {
  name                = var.kv_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  tenant_id           = var.tenant_id
  sku_name            = "standard"

  # For cloud admin
  access_policy {
    tenant_id = var.tenant_id
    object_id = data.azurerm_client_config.current.object_id

    secret_permissions = [
      "Get",
      "List",
      "Set",
      "Delete"
    ]
  }

  # SP for kube
  access_policy {
    tenant_id = var.tenant_id
    object_id = azuread_service_principal.kv_sp.id

    secret_permissions = [
      "Get",
      "List"
    ]
  }
}

resource "azurerm_key_vault_secret" "pg_password" {
  name         = var.secret_name
  value        = var.secret_value
  key_vault_id = azurerm_key_vault.kv.id
}
```

sp.tf
```sh
resource "azuread_application" "kv_app" {
  display_name = "kv-reader-sp"
}

resource "azuread_service_principal" "kv_sp" {
  client_id = azuread_application.kv_app.client_id
}

resource "azuread_service_principal_password" "kv_sp_secret" {
  service_principal_id = azuread_service_principal.kv_sp.id
  end_date_relative    = "8760h" # 1 year
}

output "sp_client_id" {
  description = "App registration (client_id)"
  value       = azuread_application.kv_app.client_id
}

output "sp_object_id" {
  description = "Object ID Service Principal"
  value       = azuread_service_principal.kv_sp.id
}

output "sp_client_secret" {
  description = "Client secret"
  value       = azuread_service_principal_password.kv_sp_secret.value
  sensitive   = true
}
```
# Kubernetes / Helm
## Postgresql

postgres-values.yaml
```yaml
image:
  repository: postgres
  tag: "17"

primary:
  persistence:
    enabled: true
    storageClass: standard
    size: 1Gi

  env:
    - name: POSTGRES_PASSWORD
      value: xxx
```

secret-provider-class.yaml
```yaml
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: flask-kv-provider
spec:
  provider: azure
  parameters:
    tenantId: "xxx"
    keyvaultName: sandbox-02-kv
    objects: |
      array:
        - |
          objectName: flask-db-password
          objectType: secret
  secretObjects:
    - secretName: flask-db-secret
      type: Opaque
      data:
        - objectName: flask-db-password
          key: password
```
kv-creds.yaml
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: kv-creds
type: Opaque
stringData:
  clientId: "xxx"       # appId
  clientSecret: "xxx"   # password
  tenantId: "xxx"       # tenantId
```

test-pod.yaml
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: busybox-secrets-test
spec:
  containers:
  - name: busybox
    image: busybox
    command: [ "sleep", "3600" ]
    volumeMounts:
    - name: secrets-store
      mountPath: "/mnt/secrets"
      readOnly: true
  volumes:
  - name: secrets-store
    csi:
      driver: secrets-store.csi.k8s.io
      readOnly: true
      volumeAttributes:
        secretProviderClass: flask-kv-provider
      nodePublishSecretRef:
        name: kv-creds
```

flask-deployment.yaml
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: flask-hello
spec:
  replicas: 1
  selector:
    matchLabels:
      app: flask-hello
  template:
    metadata:
      labels:
        app: flask-hello
    spec:
      containers:
        - name: flask-hello
          image: flask-app:latest
          imagePullPolicy: IfNotPresent

          ports:
            - containerPort: 5000

          env:
            - name: DB_HOST
              value: my-postgres-postgresql.default.svc.cluster.local
            - name: DB_PORT
              value: "5432"
            - name: DB_NAME
              value: flaskdb
            - name: DB_USER
              value: flaskuser
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: flask-db-secret
                  key: password
---
apiVersion: v1
kind: Service
metadata:
  name: flask-hello-svc
spec:
  type: NodePort
  selector:
    app: flask-hello
  ports:
    - port: 5000
      targetPort: 5000
```

## Dockerfile
```docker
FROM python:3.8-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt 
COPY app.py .

CMD ["python", "app.py"]

```

requirements.txt
```txt
blinker==1.8.2
click==8.1.8
flask==3.0.3
importlib-metadata==8.5.0
itsdangerous==2.2.0
jinja2==3.1.6
MarkupSafe==2.1.5
psycopg2-binary==2.9.10
werkzeug==3.0.6
zipp==3.20.2
```

## App
```python
import os
import psycopg2
from flask import Flask, jsonify

app = Flask(__name__)

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "flaskdb")
DB_USER = os.environ.get("DB_USER", "flaskuser")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "flaskpass")

def get_conn():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

@app.route("/")
def hello():
    conn = get_conn()
    cur = conn.cursor()

    # insert
    cur.execute("INSERT INTO messages (text) VALUES ('Hello from Flask') RETURNING id;")
    new_id = cur.fetchone()[0]
    conn.commit()

    # read it
    cur.execute("SELECT id, text, created_at FROM messages WHERE id = %s;", (new_id,))
    row = cur.fetchone()

    cur.close()
    conn.close()

    return jsonify({
        "id": row[0],
        "text": row[1],
        "created_at": row[2].isoformat()
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
```
