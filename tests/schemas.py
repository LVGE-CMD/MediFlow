APPOINTMENT_SCHEMA = {
    "type": "object",
    "required": [
        "appointment_id",
        "doctor_id",
        "slot",
        "patient_name",
        "status",
    ],
    "properties": {
        "appointment_id": {"type": "integer", "minimum": 1001},
        "doctor_id": {"type": "integer", "minimum": 0},
        "slot": {"type": "string", "minLength": 1},
        "patient_name": {"type": "string", "minLength": 1},
        "status": {
            "type": "string",
            "enum": ["booked", "cancelled"],
        },
    },
}