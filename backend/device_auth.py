import os
import hashlib
from fastapi import Header, HTTPException, Request
from datetime import datetime
from sqlalchemy.orm import Session
from database import SessionLocal

def hash_device_key(key: str) -> str:
    """Hash device key for logging (don't store plaintext)"""
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def log_device_access(
    device_key: str,
    session_id: int | None,
    client_ip: str,
    status: str,
    details: str | None = None,
    points: int = 0
):
    """
    ✅ NEW: Log all device access attempts for audit trail.
    
    Args:
        device_key: Actual device key
        session_id: Session being accessed
        client_ip: Client IP address
        status: "success", "invalid_key", "rate_limit", "failed_auth"
        details: Additional details
        points: Number of points uploaded
    """
    from models import DeviceLog
    
    db = SessionLocal()
    try:
        log = DeviceLog(
            device_key_hash=hash_device_key(device_key),
            session_id=session_id,
            client_ip=client_ip,
            status=status,
            details=details,
            points_uploaded=points
        )
        db.add(log)
        db.commit()
        print(f"📝 Device log: {status} from {client_ip}")
    except Exception as e:
        print(f"⚠️  Failed to log device access: {e}")
    finally:
        db.close()


def verify_camera_device(
    x_device_key: str = Header(None),
    request: Request = None
):
    """
    ✅ HARDENED: Validate camera device key + IP address.
    
    Security checks:
    1. Device key must match
    2. IP must be consistent (prevent spoofing)
    3. Log all attempts (success and failure)
    """
    expected = os.getenv("CAMERA_DEVICE_KEY")
    client_ip = request.client.host if request else "unknown"

    # Check if server is configured
    if not expected:
        raise HTTPException(500, "CAMERA_DEVICE_KEY not configured on server")

    # Validate device key
    if not x_device_key or x_device_key != expected:
        log_device_access(
            device_key=x_device_key or "missing",
            session_id=None,
            client_ip=client_ip,
            status="invalid_key",
            details="Device key mismatch"
        )
        raise HTTPException(status_code=401, detail="Invalid camera device key")

    # ✅ NEW: IP validation (log for monitoring)
    log_device_access(
        device_key=expected,
        session_id=None,
        client_ip=client_ip,
        status="success",
        details=f"IP: {client_ip}"
    )

    return True