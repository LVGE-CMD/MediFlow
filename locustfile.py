import uuid

from locust import HttpUser, between, task


class AppointmentUser(HttpUser):
    wait_time = between(0.1, 0.3)

    @task
    def create_appointment(self):
        slot = f"perf-{uuid.uuid4().hex}"
        payload = {
            "doctor_id": 7,
            "slot": slot,
            "patient_name": "Perf User",
        }

        with self.client.post(
            "/appointments",
            json=payload,
            catch_response=True,
        ) as response:
            if response.status_code == 201:
                response.success()
            else:
                response.failure(
                    f"unexpected status {response.status_code}"
                )