# Simple 10-Minute CI/CD Pipeline for a Lab Environment

This guide describes a fast and functional pipeline that you can deploy in your lab or test environment.

## The Stack

* **GitHub** (or any other code repository)
* **Python** with **Flask** for the application
* **Docker** (local installation + local Docker registry)
* **K3s** for orchestration (sufficient for this lab)
* **Jenkins** for Continuous Integration (CI)
* **ArgoCD** for Continuous Delivery (CD/GitOps)

## Step-by-Step Guide

### 1. Code Repository Setup

#### Obtaining and Storing the Token
1.  **Get the Token**: Go to **Settings** \ **Developer settings** \ **Issue a token** (Personal Access Token, **PAT**).
2.  **Store the Token**: Add this token to **Jenkins** credentials as a "Username and Password" pair (where the password is your **PAT**).

This token will be used by Jenkins when creating the SCM (Source Code Management) pipeline to access your repository.

### 2. Project Structure
The project has a simple structure:

```
root/
├── app/
│   ├── app.py
│   └── requirements.txt
│
├── infra/
│   ├── deployment.yaml
│   └── service.yaml
│
├── Dockerfile
└── Jenkinsfile
````

## File Contents

### Application (App)

#### `app/app.py`

A simple Flask application that returns JSON:

```python
from flask import Flask

app = Flask(__name__)

@app.route("/")
def index():
    return {
        "hello": "world"
    }

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
```

#### `requirements.txt`

Standard content for a Flask application (e.g., `Flask`).

### CD Manifests (infra/)

#### `infra/deployment.yaml`

This manifest describes the **Deployment** in Kubernetes. Note: the `'latest'` tag will be replaced with the **image digest** (hash) by the Jenkins pipeline.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: demo-app
  labels:
    app: demo-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: demo-app

  template:
    metadata:
      labels:
        app: demo-app

    spec:
      containers:
        - name: demo-app
        # This 'latest' tag will be replaced with the container hash (digest) in the Jenkins pipeline
          image: localhost:5000/my-flask:latest
          imagePullPolicy: Always

          ports:
            - containerPort: 5000
          
          # This is not necessary for this tiny app however keep if for the future usage
          readinessProbe:
            httpGet:
              path: /
              port: 5000
            initialDelaySeconds: 5
            periodSeconds: 5

          livenessProbe:
            httpGet:
              path: /
              port : 5000
            initialDelaySeconds: 5
            periodSeconds: 10
```

#### `infra/service.yaml`

A Service that exposes port 5000 for application access. Make sure that port **5000** is available in the K3s cluster (and not on the node where the local Docker registry is, or change the port here).

```yaml
apiVersion: v1
kind: Service
metadata:
  name: demo-app
spec:
  selector:
    app: demo-app
  ports:
  - port: 5000
    targetPort: 5000
    protocol: TCP
    name: http
```

### CI/Image (Dockerfile & Jenkinsfile)

#### `Dockerfile`

A standard Dockerfile for building the Flask application image, using `gunicorn` for execution:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY ./app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .

CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
```

#### `Jenkinsfile`

This pipeline combines the **imperative** style of Jenkins (build, test, push image) with the **declarative** GitOps approach (update manifest and push changes to Git, which ArgoCD picks up).

**Key Points:**

  * **A local Docker container registry** (`localhost:5000`) is used for simplicity. Change it to yours if necessary.
  * We obtain the **digest** (image hash) and use it to update `deployment.yaml`. This allows ArgoCD to deploy the new, verified version.

```groove
pipeline{
    agent any

    stages {
        stage('Build'){
            steps{
                sh 'docker build -t my-flask:latest -f Dockerfile .'
            }
        }

        stage('Test'){
            steps{
                sh '''
                    docker rm -f test-flask || true
                    docker run -d \
                        --name test-flask \
                        -p 5001:5000 \
                        my-flask:latest
                '''
            }
        }

        stage('Push to Local Registry'){
            steps{
                sh '''
                    docker tag \
                        my-flask:latest \
                        localhost:5000/my-flask:latest
                    docker push \
                        localhost:5000/my-flask:latest
                '''
            }
        }

        stage('Get Digest') {
            steps {
                script {
                    // We will pass this variable to another step
                    env.DIGEST = sh(
                        script: """
                            docker inspect \
                            --format='{{index .RepoDigests 0}}' \
                            localhost:5000/my-flask:latest \
                        """,
                        returnStdout: true
                    ).trim()
                } 
            }
        }

        stage('Update Manifest with Digest') {
            steps {
                sh """
                    sed -i 's|image:.*|image: ${env.DIGEST}|' infra/deployment.yaml
                """
            }
        }
        
        // Yes, we need to pass credentials here
        // even if we added them to the pipeline at the creation stage
        stage('Commit and Push Manifest Change') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'gt-token2',
                    usernameVariable: 'GIT_USER',
                    passwordVariable: 'GIT_PASS'
                )]){
                    sh """
                    git config user.email "jenkins@local"
                    git config user.name "Jenkins CI"

                    git add infra/deployment.yaml
                    git commit -m "Update image digest to ${env.DIGEST}" || true
                    git push https://${GIT_USER}:${GIT_PASS}@[github.com/<YOUR-ACCOUNT>/<REPO-NAME>.git](https://github.com/<YOUR-ACCOUNT>/<REPO-NAME>.git) HEAD:infra
                    """
                }
            }
        }
    }
}
```
