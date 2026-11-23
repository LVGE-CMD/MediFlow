import uuid

from playwright.sync_api import expect


def test_create_appointment_ui(base_url, page):
    page.goto(f"{base_url}/")

    page.fill("#doctor_id", "7")
    page.fill(
        "#slot",
        f"2026-11-25 10:00-{uuid.uuid4().hex[:8]}",
    )
    page.fill("#patient_name", "UI Test")

    page.click("button[type=submit]")

    expect(page.locator("#result")).to_contain_text("201")