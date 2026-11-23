import sqlite3
from pathlib import Path
import os

DB_PATH = Path(
    os.getenv(
        "MEDIFLOW_DB_PATH",
        Path(__file__).resolve().parents[2] / "mediflow.db",
    )
)


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doctor_id INTEGER NOT NULL,
                slot TEXT NOT NULL,
                patient_name TEXT NOT NULL,
                status TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
                uq_appointments_booked_slot
            ON appointments (doctor_id, slot)
            WHERE status = 'booked'
            """
        )
        conn.commit()
    finally:
        conn.close()