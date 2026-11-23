from __future__ import annotations


def health_payload(service: str)->dict:
    return {"status": "ok", "service": service}