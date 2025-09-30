# Bulkhead Pattern with Azure Functions: From Orders to Payments

Imagine you are running **Vitamins Online Shop**.  
Your customers click *Buy Now*, payments flow in, and the last thing you want is that one failing component sinks the entire system.  

That’s where the **Bulkhead pattern** comes in. It’s like watertight compartments on a ship: if one floods, the others keep sailing. In Azure, we can achieve this separation using **two Function Apps** and a **queue** between them.

---

## Why This Matters (Business Value)

- **Customer trust**: Orders are accepted even if payment processing is temporarily down.  
- **Resilience**: A bug in payment logic won’t stop the storefront from working.  
- **Scalability**: Queue absorbs spikes in customer orders; worker can scale independently.  
- **Cost control**: Pay-as-you-go model — you don’t need idle VMs just waiting for traffic.  

The result: smoother customer experience, fewer lost sales, better sleep for your ops team.

---

## Architecture

```ascii
[ Customers Clicking Buy ]
            │
            ▼
+----------------------+
|  Producer Function   |
|  (HTTP Trigger)      |
|  Accepts orders      |
+----------------------+
            │
            ▼
+----------------------+
| Azure Storage Queue  |
| "payments"           |
| Reliable buffer      |
+----------------------+
            │
            ▼
+----------------------+
|  Consumer Function   |
|  (Queue Trigger)     |
|  Processes payments  |
+----------------------+
            │
            ▼
[ Bank / 3rd party API ]
```

## Step 1. Prepare Azure Resources

```sh
az login
az account set --subscription <vitamins-shop>

az group create \
    --name vitamins-online-shop-rg \
    --location westeurope

az storage account create \
    --name orderspayments$RANDOM \
    --resource-group vitamins-online-shop-rg \
    --location westeurope \
    --sku Standard_LRS
```
We now have a storage account that will host our queue.


## Step 2. Producer — Taking Orders

Think of this as the cashier at the counter. Customers hand over money, and the cashier drops receipts into a safe box (the queue).

function_app.py:
```python
import random
import string
import azure.functions as func

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.function_name(name="enqueue_payment")
@app.route(route="enqueue", methods=["GET"])
@app.queue_output(arg_name="msg", queue_name="payments", connection="AzureWebJobsStorage")
def enqueue_payment(req: func.HttpRequest, msg: func.Out[str]) -> func.HttpResponse:
    # generate an order ID
    payload = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    msg.set(payload)
    return func.HttpResponse(f"Order accepted: {payload}\n", mimetype="text/plain")
```
Business effect: No matter what happens downstream, customers see “Order accepted” instantly.

## Step 3. Consumer — Processing Payments

This is the accountant in the back office. They quietly pick receipts from the safe box and settle payments with the bank.

function_app.py:
```python
import logging
import azure.functions as func

app = func.FunctionApp()

@app.function_name(name="process_payment")
@app.queue_trigger(arg_name="msg", queue_name="payments", connection="AzureWebJobsStorage")
def process_payment(msg: func.QueueMessage) -> None:
    body = msg.get_body().decode()
    logging.info("Processing payment for order: %s", body)
```
Business effect: Even if this part crashes, orders pile up safely in the queue and nothing is lost.


## Step 4. Bulkhead Isolation
Producer Function App = storefront, lightweight, responsive.

Consumer Function App = heavy worker, isolated from the storefront.

Queue = watertight door, keeping failures from spreading.

## Result
If payments integration goes down storefront still takes orders.
If storefront is redeployed worker keeps draining the queue.
Customers never see “Service Unavailable” at checkout.

## Key Takeaways

* Bulkhead is not theory: in Azure Functions it’s as simple as splitting Producer and Consumer into separate Function Apps.

* Business resilience: failures don’t cascade, customers keep buying, revenue keeps flowing.

* Operational peace of mind: scaling, retries, and poison queues can be added later, but the foundation is already safe.

This is how a simple queue between two Function Apps protects your business like watertight compartments protect a ship.
