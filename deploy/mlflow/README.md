# MLflow on EC2 (Postgres + S3, IP-only)

MLflow server with Postgres backend and S3 artifact storage.
No domain or HTTPS required — connects via EC2 public IP on port 5000.

## Prerequisites

- EC2 instance running Amazon Linux 2023
- S3 bucket created: `sanskrit-shloka-bucket` (us-east-1)
- Key pair (e.g. `mithuna.pem`) for SSH access
- Security group inbound rules:
  - **TCP 22** from your IP (SSH)
  - **TCP 5000** from your IP (MLflow) — or `0.0.0.0/0` if you want GitHub Actions to reach it

## Step 1: Install Docker on EC2

```bash
ssh -i /path/to/mithuna.pem ec2-user@<EC2_PUBLIC_IP>

sudo dnf update -y
sudo dnf install -y docker docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
logout
```

SSH back in so the docker group takes effect.

## Step 2: Copy deploy bundle to EC2

From your local machine:

```bash
scp -i /path/to/mithuna.pem -r deploy/mlflow ec2-user@<EC2_PUBLIC_IP>:~/mlflow
```

## Step 3: Configure environment

```bash
ssh -i /path/to/mithuna.pem ec2-user@<EC2_PUBLIC_IP>
cd ~/mlflow
cp .env.example .env
nano .env   # or vi
```

Set these values in `.env`:

| Variable | Value |
|---|---|
| `POSTGRES_PASSWORD` | A strong password |
| `MLFLOW_BACKEND_STORE_URI` | `postgresql://mlflow:<PASSWORD>@postgres:5432/mlflow` |
| `MLFLOW_ARTIFACT_ROOT` | `s3://sanskrit-shloka-bucket/mlflow` |
| `AWS_ACCESS_KEY_ID` | Your IAM key |
| `AWS_SECRET_ACCESS_KEY` | Your IAM secret |
| `AWS_DEFAULT_REGION` | `us-east-1` |

## Step 4: Start MLflow

```bash
docker compose up -d --build
```

## Step 5: Verify

```bash
# Check containers are healthy
docker compose ps

# Check MLflow logs
docker compose logs -f mlflow

# Health check (from EC2 or your machine)
curl http://<EC2_PUBLIC_IP>:5000/health
```

Open `http://<EC2_PUBLIC_IP>:5000` in your browser — you should see the MLflow UI.

## Step 6: Set GitHub secrets

In your repo Settings > Secrets and variables > Actions, set:

| Secret | Value |
|---|---|
| `MLFLOW_TRACKING_URI` | `http://<EC2_PUBLIC_IP>:5000` |
| `AWS_ACCESS_KEY_ID` | Same as above |
| `AWS_SECRET_ACCESS_KEY` | Same as above |
| `AWS_DEFAULT_REGION` | `us-east-1` |

## Useful commands

```bash
docker compose logs -f mlflow    # Stream logs
docker compose restart mlflow    # Restart after config change
docker compose down              # Stop everything
docker compose up -d             # Start without rebuild
```

## Security notes

- Port 5000 is **unencrypted HTTP**. Restrict the security group to your IP and GitHub Actions IPs.
- To lock down to GitHub Actions only, use their [published IP ranges](https://api.github.com/meta) under `actions`.
- For production, add Caddy back with a domain for HTTPS (see Caddyfile in this directory).
