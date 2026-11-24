# Academic Performance Analyzer

A FastAPI application for managing student performance and generating statistical analyses and reports.

## Run locally

1. Install Python 3.12 or later.
2. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Start the app:

   ```powershell
   python run.py
   ```

Open <http://localhost:8000>. For local development, the initial admin login is `admin` / `admin123`. Set `ADMIN_USERNAME` and `ADMIN_PASSWORD` before using a non-local deployment.

## Deploy from GitHub with Render

1. Open [Render's Blueprint deployment page](https://render.com/deploy) and connect this repository: <https://github.com/192565073simats-gif/UBA5320-PMLA-CAPSTONE-PROJECT>.
2. Render reads `render.yaml` and creates the FastAPI web service and PostgreSQL database.
3. Enter a strong value for the requested `ADMIN_PASSWORD` environment variable. The generated `SECRET_KEY` is managed by Render.
4. Wait for the service deployment to finish, then open its `onrender.com` URL. `/health` is the configured health check.

The included Blueprint uses Render's free web-service and PostgreSQL plans for a demo. Free web services sleep when idle, and the free PostgreSQL database expires after 30 days; database contents are not suitable for long-term storage. Upgrade the service and database to paid plans before relying on persistent data. Do not use real or sensitive student records in a public demo.
