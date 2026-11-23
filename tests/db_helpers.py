from services.appointment.db import get_connection



def fetch_appointment(appointment_id):
    conn = get_connection()
    try:
        return  conn.execute(
            "SELECT*FROM appointments WHERE id= ?",
            (appointment_id - 1000,)
        ).fetchone()
    finally:
        conn.close()


def delete_appointment(appointment_id):
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM appointments WHERE id= ?",
            (appointment_id - 1000,)
        )
        conn.commit()
    finally:
        conn.close()