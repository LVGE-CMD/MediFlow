from concurrent.futures import ThreadPoolExecutor
import requests
import uuid


def test_concurrent_booking_allows_one(base_url):
    slot = f"2026-11-20 09:00-{uuid.uuid4().hex[:8]}"
    def book(index):
        return requests.post(
            f"{base_url}/appointments",
            json={
        "doctor_id": 7,
        "slot": slot,
        "patient_name": f"User-{index}",
        }
        )
    with ThreadPoolExecutor(max_workers=10) as pool:
        responses = list(pool.map(book, range(10)))
    statuses = [responses.status_code for responses in responses]
    assert statuses.count(201) == 1
    assert statuses.count(409) == 9