from fastapi import FastAPI

from services.common.health import health_payload

app = FastAPI(title="MediFlow Schedule Service")
@app.get("/health")
def health():
    return health_payload("schedule")