import secrets
from flask import request, session


DEVICE_COOKIE = "device_id"


def device_rate_key() -> str:
    device_id = request.cookies.get(DEVICE_COOKIE)
    if not device_id:
        device_id = session.get(DEVICE_COOKIE)
    return device_id or request.remote_addr or "unknown-device"


def new_device_id() -> str:
    return secrets.token_urlsafe(32)
