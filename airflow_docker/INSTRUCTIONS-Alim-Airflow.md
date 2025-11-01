### Apache Airflow on Windows (Docker Desktop, Python 3.12)

This guide documents the exact steps executed on your Windows 10/11 machine to deploy Apache Airflow 2.x with Python 3.12 using Docker Desktop (Linux containers). It includes start/stop, verification, troubleshooting, and next steps.

---

## Quick start: Start the UI

```powershell
cd C:\Users\alimm\OneDrive\Desktop\Apache\Airflow\airflow_docker
# Start services (or ensure they are running)
docker compose up -d
# Wait until webserver is healthy
docker compose ps
# Open the UI
Start-Process 'http://localhost:8080'
# Login: airflow / airflow
```

---

## What was installed/detected

- Docker Desktop was detected and running (Linux containers).
- WSL2 backend is available via Docker Desktop.

If Docker Desktop is not available on another machine, see the WSL2 path at the end of this file.

---

## Project structure

```
airflow_docker/
  .env
  docker-compose.yaml
  dags/
    hello_dag.py
  logs/
  plugins/
```

---

## Exact commands used (PowerShell)

Run these in `C:\Users\alimm\OneDrive\Desktop\Apache\Airflow\airflow_docker`.

```powershell
# 1) Pull images
docker compose pull

# 2) Initialize Airflow database and create admin user
docker compose up airflow-init

# 3) Start all services in background
docker compose up -d

# 4) Check health of services
docker compose ps

# 5) Verify webserver responds (expect 200)
Invoke-WebRequest -UseBasicParsing http://localhost:8080 | Select-Object -ExpandProperty StatusCode

# 6) Confirm DAG presence from container
docker compose exec -T airflow-webserver bash -lc "airflow dags list | sed -n '1,20p'"
```

Credentials for the UI:
- Username: `airflow`
- Password: `airflow`

Open `http://localhost:8080` in your browser and log in with the above.

---

## docker-compose services

- Postgres 13 (metadata DB)
- Redis 7 (optional broker/cache)
- Airflow Webserver, Scheduler, Triggerer
- One-shot `airflow-init` service to init DB and create the admin user
- Optional `airflow-cli` profile for on-demand CLI usage

Image: `apache/airflow:2.9.1-python3.12` (Python 3.12 variant)

---

## Common operations

```powershell
# Stop services (keep volumes)
docker compose down

# View webserver logs
docker compose logs -f airflow-webserver

# Restart services
docker compose restart

# Reset all data (deletes volumes)
docker compose down -v
docker compose up airflow-init
docker compose up -d
```

---

## Troubleshooting

- Port 8080 already in use:
  ```powershell
  netstat -ano | findstr :8080
  taskkill /PID <PID> /F
  ```

- Permission issues on `logs/` or `dags/` (Windows):
  - Ensure `.env` contains `AIRFLOW_UID=50000` and `AIRFLOW_GID=0`.
  - Recreate the containers after fixes: `docker compose down -v` then bring up again.

- Webserver slow to become healthy:
  - Wait 10–30 seconds after first start; check `docker compose ps` until webserver is healthy.
  - Inspect logs: `docker compose logs -f airflow-webserver`.

- WSL2 networking (if using WSL path):
  - Access via `http://localhost:8080` from Windows; Docker Desktop forwards automatically.

---

## Security: Fernet key rotation (done)

- docker-compose now reads the key from `.env` as `FERNET_KEY` (no hardcoded key).
- `.env` is git-ignored to avoid leaking secrets.
- Rotation we performed:
  1) Generated a new key and temporarily set `FERNET_KEY=new,old` in `.env`.
  2) Restarted services and ran:
     ```powershell
     docker compose exec -T airflow-webserver airflow rotate-fernet-key
     ```
  3) Set `FERNET_KEY=new` only and restarted services again.

Rotate again later (recipe):
```powershell
docker run --rm python:3.12-slim python -c "import base64,os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
# Edit .env → FERNET_KEY=newKey,oldKey
docker compose down
docker compose up -d
docker compose exec -T airflow-webserver airflow rotate-fernet-key
# Edit .env → FERNET_KEY=newKey
docker compose down
docker compose up -d
```

If the old key existed in a remote repo, rewrite history with `git filter-repo` or BFG and force-push to fully purge it.

---

## Add more DAGs

- Place new `.py` files under `./dags/`. Airflow will auto-detect within ~1 minute.
- Use the UI to trigger DAGs, view task logs, and monitor runs.

---

## Where things live

- DAGs: `./dags/`
- Logs: `./logs/` (also visible in the UI)
- Plugins: `./plugins/`

---

## If Docker Desktop is not available: WSL2 + Docker Engine

Run these in elevated PowerShell:

```powershell
wsl --install
wsl --set-default-version 2
```

Install Ubuntu from Microsoft Store, launch it, then in Ubuntu shell:

```bash
sudo apt update && sudo apt install -y ca-certificates curl gnupg lsb-release
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update && sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
newgrp docker
```

Then inside Ubuntu shell, create the project and run the same `docker compose` commands in this folder (clone or copy the `airflow_docker/` directory). For WSL2, set in `.env`:

```
AIRFLOW_UID=$(id -u)
AIRFLOW_GID=$(id -g)
AIRFLOW_IMAGE_NAME=apache/airflow:2.9.1-python3.12
```

---

## Monitor DAGs from Terminal (Real-time)

The UI auto-refreshes but with a delay. For real-time monitoring:

```powershell
# View recent DAG runs
docker compose exec -T airflow-webserver airflow dags list-runs --dag-id download_dataset_dag --no-backfill --state running

# Stream logs for a specific task (real-time)
docker compose exec -T airflow-webserver airflow tasks logs download_dataset_dag store_task 2025-11-01

# Check task states for a DAG run
docker compose exec -T airflow-webserver airflow tasks states-for-dag-run download_dataset_dag manual__2025-11-01T01:45:49.637991+00:00

# Quick status check
docker compose exec -T airflow-webserver airflow dags state download_dataset_dag 2025-11-01
```

**UI vs Terminal:**
- **UI**: Auto-refreshes every ~30 seconds, good for overall status
- **Terminal**: Real-time logs, useful for debugging and immediate feedback

## What's next

- Create new DAGs in `./dags/` and enable them in the UI.
- Use the Admin → Connections and Variables screens to configure external systems.
- CLI example:
  ```powershell
  docker compose exec -T airflow-webserver bash -lc "airflow users list"
  ```

---

## Manage admin credentials (reset/create)

- Current admin (created during init): `airflow` / `airflow`
- List users:
  ```powershell
  docker compose exec -T airflow-webserver bash -lc "airflow users list"
  ```
- Update admin password (preferred):
  ```powershell
  docker compose exec -T airflow-webserver bash -lc "airflow users update --username airflow --password NEW_SECURE_PASSWORD"
  ```
- Alternatively, delete and recreate the admin user:
  ```powershell
  docker compose exec -T airflow-webserver bash -lc "airflow users delete --username airflow"
  docker compose exec -T airflow-webserver bash -lc "airflow users create --username airflow --password NEW_SECURE_PASSWORD --firstname Alim --lastname User --role Admin --email alim@example.com"
  ```
- After changing the password, refresh `http://localhost:8080` and log in with the new credentials.


