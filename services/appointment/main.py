import sqlite3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from services.common.health import health_payload
from services.appointment.db import get_connection, init_db
import os
import uuid
import redis
from fastapi.responses import HTMLResponse

app = FastAPI(title="MediFlow Appointment Service")
REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://127.0.0.1:6379/0",
)

redis_client = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True,
)


def acquire_lock(key: str, token: str, ttl: int = 5) -> bool:
    return bool(
        redis_client.set(
            key,
            token,
            nx=True,
            ex=ttl,
        )
    )


def release_lock(key: str, token: str) -> None:
    script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
    redis_client.eval(script, 1, key, token)


init_db()
appointments: list[dict] = []


class AppointmentIn(BaseModel):
    doctor_id: int
    slot: str
    patient_name: str = Field(min_length=1)


@app.get("/health")
def health():
    return health_payload("appointment")


@app.get("/", response_class=HTMLResponse)
def index():
    return """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>MediFlow 预约</title>
</head>
<body>
  <h1>预约</h1>

  <form id="form">
    <label>医生 ID
      <input id="doctor_id" value="7">
    </label>
    <label>时段
      <input id="slot" value="2026-11-25 09:00">
    </label>
    <label>患者
      <input id="patient_name" value="UI Test">
    </label>
    <button type="submit">提交</button>
  </form>

  <pre id="result"></pre>

  <script>
    document.getElementById("form").addEventListener("submit", async (event) => {
      event.preventDefault();

      const body = {
        doctor_id: Number(document.getElementById("doctor_id").value),
        slot: document.getElementById("slot").value,
        patient_name: document.getElementById("patient_name").value,
      };

      const response = await fetch("/appointments", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      const text = await response.text();
      document.getElementById("result").textContent =
        response.status + " " + text;
    });
  </script>
</body>
</html>
"""



@app.post("/appointments", status_code=201)
def create_appointment(payload: AppointmentIn):
    lock_key = f"lock:slot:{payload.doctor_id}:{payload.slot}"
    token = str(uuid.uuid4())

    if not acquire_lock(lock_key, token):
        raise HTTPException(
            status_code=409,
            detail="该时段正在被预约",
        )


    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO appointments
                (doctor_id, slot, patient_name, status)
            VALUES (?, ?, ?, ?)
            """,
            (
                payload.doctor_id,
                payload.slot,
                payload.patient_name,
                "booked",
            ),
        )
        conn.commit()
        appointment_id = 1000 + cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.rollback()
        raise HTTPException(
            status_code=409,
            detail="该时段已被预约"
        )
    finally:
        conn.close()
        release_lock(lock_key, token)
    return {
        "appointment_id": appointment_id,
        "doctor_id": payload.doctor_id,
        "slot": payload.slot,
        "patient_name": payload.patient_name,
        "status": "booked",
    }


@app.get("/appointments")
def list_appointments():
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM appointments ORDER BY id DESC"
        ).fetchall()
    finally:
        conn.close()
    items = []
    for row in rows:
        items.append({
            "appointment_id": 1000 + row["id"],
            "doctor_id": row["doctor_id"],
            "slot": row["slot"],
            "patient_name": row["patient_name"],
            "status": row["status"],
        })
    return {
        "item": items,
        "total": len(items),
    }


@app.get("/appointments/{appointment_id}")
def get_appointment(appointment_id: int):
    db_id = appointment_id - 1000
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM appointments WHERE id = ?",
            (db_id,),
        ).fetchone()
    finally:

        conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="预约不存在")

    return {
        "appointment_id": 1000 + row["id"],
        "doctor_id": row["doctor_id"],
        "slot": row["slot"],
        "patient_name": row["patient_name"],
        "status": row["status"],
    }


@app.patch("/appointments/{appointment_id}/cancel")
def cancel_appointment(appointment_id: int):
    db_id = appointment_id - 1000
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM appointments WHERE id = ?",
            (db_id,),
        ).fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="预约不存在")
        if row["status"] != "booked":
            raise HTTPException(status_code=409, detail="当前预约状态不可取消")
        conn.execute(
            "UPDATE appointments SET status = ? WHERE id = ?",
            ("cancelled", db_id),
        )
        conn.commit()
        result = {
            "appointment_id": 1000 + row["id"],
            "doctor_id": row["doctor_id"],
            "slot": row["slot"],
            "patient_name": row["patient_name"],
            "status": "cancelled",
        }
    finally:
        conn.close()
    return result
