import requests


def test_appointment_health(base_url):
    response = requests.get(f"{base_url}/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"