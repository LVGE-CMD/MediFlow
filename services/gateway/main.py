import os

import requests
from fastapi import FastAPI

from services.common.health import health_payload


app = FastAPI(title="MediFlow Gateway Service")

SCHEDULE_URL = os.getenv("SCHEDULE_URL", "http://127.0.0.1:8001")


@app.get("/health/live")
def live():
    return health_payload("gateway")


@app.get("/health")
def health():
    dependencies = {}

    try:
        response = requests.get(f"{SCHEDULE_URL}/health", timeout=1)
        dependencies["schedule"] = {
            "status": "ok" if response.status_code == 200 else "error",
            "code": response.status_code,
        }
    except requests.RequestException:
        dependencies["schedule"] = {"status": "down"}

    status = "ok" if all(
        item["status"] == "ok" for item in dependencies.values()
    ) else "degraded"

    return {
        "status": status,
        "service": "gateway",
        "dependencies": dependencies,
    }