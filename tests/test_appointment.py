import jsonschema
from tests.schemas import APPOINTMENT_SCHEMA
import pytest
import requests
import uuid
from tests.db_helpers import delete_appointment, fetch_appointment
from datetime import datetime



def create_appointment(base_url, patient_name = "Test User",slot = None):
    if slot is None:
        slot = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    payload = {
        "doctor_id": 7,
        "slot": slot,
        "patient_name": patient_name,

    }
    response = requests.post(f"{base_url}/appointments", json=payload,)
    assert response.status_code == 201
    return response.json()



def test_create_appointment(base_url):
    body = create_appointment(base_url)
    assert body["doctor_id"] == 7
    assert body["patient_name"] == "Test User"
    assert body["status"]=="booked"
    assert body["appointment_id"] > 1000


def test_get_appointment(base_url):
    appointment = create_appointment(base_url)
    appointment_id = appointment["appointment_id"]
    responses = requests.get(f"{base_url}/appointments/{appointment_id}")
    assert responses.status_code == 200
    body = responses.json()
    assert body["doctor_id"] == 7
    assert body["patient_name"] == "Test User"
    assert body["appointment_id"] == appointment_id
    assert body["status"]=="booked"


def test_get_missing_appointment(base_url):
    response = requests.get(f"{base_url}/appointments/9999")
    assert response.status_code == 404
    body = response.json()
    assert body["detail"] == "预约不存在"


def test_cancel_appointment(base_url):
    appointment = create_appointment(base_url)
    appointment_id = appointment["appointment_id"]
    response = requests.patch(f"{base_url}/appointments/{appointment_id}/cancel")
    assert response.status_code == 200
    body = response.json()
    assert body["doctor_id"] == 7
    assert body["status"]=="cancelled"


def test_cancel_twice(base_url):
    appointment = create_appointment(base_url)
    appointment_id = appointment["appointment_id"]
    first = requests.patch(f"{base_url}/appointments/{appointment_id}/cancel")
    assert first.status_code == 200
    second = requests.patch(f"{base_url}/appointments/{appointment_id}/cancel")
    assert second.status_code == 409
    assert second.json()["detail"] == "当前预约状态不可取消"


@pytest.mark.parametrize("raw_id,expected", [
    ("abc",422),
    ("0",404),
    ("-1",404),
    ("9999",404),
],
)
def test_invalid_id(base_url, raw_id, expected):
    response = requests.get(f"{base_url}/appointments/{raw_id}")
    assert response.status_code == expected



def test_create_appointment_persists(base_url):
    patient_name = f"Test User-{uuid.uuid4().hex[:8]}"


    appointment = create_appointment(base_url, patient_name)
    appointment_id = appointment["appointment_id"]

    try:
        row = fetch_appointment(appointment_id)
        assert row is not None
        assert row["doctor_id"] == 7
        assert row["patient_name"] == patient_name
        assert row["status"] == "booked"
    finally:
        delete_appointment(appointment_id)



def test_appointment_contract(base_url):
    appointment = create_appointment(base_url)
    jsonschema.validate(
        instance=appointment,
        schema=APPOINTMENT_SCHEMA,
    )