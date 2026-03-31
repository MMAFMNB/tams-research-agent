"""Email verification using Resend API.

Sends a verification email with a 6-digit code when a user signs up.
The user must enter the code to complete registration.
"""

import os
import json
import hashlib
import secrets
import threading
from datetime import datetime, timedelta
from typing import Optional, Tuple

# Verification codes stored in JSON (fallback — no DB needed)
VERIFY_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "verify_codes.json")
_lock = threading.Lock()

# Resend API
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
FROM_EMAIL = os.environ.get("VERIFY_FROM_EMAIL", "noreply@tamcapital.sa")


def _load_codes() -> dict:
    """Load verification codes from JSON."""
    try:
        if os.path.exists(VERIFY_FILE):
            with open(VERIFY_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_codes(data: dict):
    """Save verification codes to JSON."""
    os.makedirs(os.path.dirname(VERIFY_FILE), exist_ok=True)
    with open(VERIFY_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)


def generate_code() -> str:
    """Generate a 6-digit verification code."""
    return f"{secrets.randbelow(900000) + 100000}"


def _hash_code(code: str) -> str:
    """Hash code for secure storage."""
    return hashlib.sha256(code.encode()).hexdigest()


def store_verification(email: str, code: str) -> None:
    """Store a hashed verification code for an email."""
    with _lock:
        data = _load_codes()
        data[email.lower()] = {
            "code_hash": _hash_code(code),
            "created_at": datetime.now().isoformat(),
            "attempts": 0,
            "verified": False,
        }
        _save_codes(data)


def verify_code(email: str, code: str) -> Tuple[bool, str]:
    """Verify a code for an email.

    Returns:
        (success, message) tuple
    """
    with _lock:
        data = _load_codes()
        entry = data.get(email.lower())

        if not entry:
            return False, "No verification pending for this email."

        if entry.get("verified"):
            return True, "Email already verified."

        # Check expiry (30 minutes)
        created = datetime.fromisoformat(entry["created_at"])
        if datetime.now() - created > timedelta(minutes=30):
            return False, "Verification code expired. Please request a new one."

        # Check attempts (max 5)
        if entry.get("attempts", 0) >= 5:
            return False, "Too many failed attempts. Please request a new code."

        # Check code
        if _hash_code(code) == entry["code_hash"]:
            entry["verified"] = True
            data[email.lower()] = entry
            _save_codes(data)
            return True, "Email verified successfully!"
        else:
            entry["attempts"] = entry.get("attempts", 0) + 1
            data[email.lower()] = entry
            _save_codes(data)
            remaining = 5 - entry["attempts"]
            return False, f"Invalid code. {remaining} attempts remaining."


def is_email_verified(email: str) -> bool:
    """Check if an email has been verified."""
    data = _load_codes()
    entry = data.get(email.lower(), {})
    return entry.get("verified", False)


def send_verification_email(email: str, code: str) -> Tuple[bool, str]:
    """Send verification email via Resend API.

    Returns:
        (success, message) tuple
    """
    if not RESEND_API_KEY:
        # No API key configured — auto-verify for development
        return True, f"[DEV MODE] No Resend API key. Code: {code}"

    try:
        import requests  # Using requests since resend package may not be installed

        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": FROM_EMAIL,
                "to": [email],
                "subject": "TAM Research Terminal — Verify Your Email",
                "html": f"""
                <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto;
                            background: #0A0F1C; color: #E6EDF3; padding: 40px 30px; border-radius: 16px;">
                    <div style="text-align:center; margin-bottom: 30px;">
                        <h2 style="color: #6CB9B6; margin: 0;">TAM Research Terminal</h2>
                        <p style="color: #8B949E; font-size: 0.85rem;">Email Verification</p>
                    </div>

                    <p style="font-size: 0.95rem; line-height: 1.6;">
                        Welcome! Please use the following code to verify your email address:
                    </p>

                    <div style="background: #111827; border: 1px solid rgba(108,185,182,0.3);
                                border-radius: 12px; padding: 20px; text-align: center;
                                margin: 20px 0;">
                        <span style="font-size: 2rem; font-weight: 700; letter-spacing: 8px;
                                     color: #6CB9B6;">{code}</span>
                    </div>

                    <p style="font-size: 0.85rem; color: #8B949E; line-height: 1.5;">
                        This code expires in 30 minutes. If you did not request this,
                        please ignore this email.
                    </p>

                    <hr style="border-color: rgba(255,255,255,0.1); margin: 25px 0;" />
                    <p style="font-size: 0.7rem; color: #8B949E; text-align: center;">
                        TAM Capital | CMA Regulated<br/>
                        Confidential — Authorized Personnel Only
                    </p>
                </div>
                """,
            },
            timeout=10,
        )

        if response.status_code in (200, 201):
            return True, "Verification email sent!"
        else:
            error_msg = response.json().get("message", response.text)
            return False, f"Failed to send email: {error_msg}"

    except ImportError:
        return False, "requests library not available. Install with: pip install requests"
    except Exception as e:
        return False, f"Error sending email: {str(e)}"


def send_and_store(email: str) -> Tuple[bool, str, Optional[str]]:
    """Generate, store, and send a verification code.

    Returns:
        (success, message, code_for_dev) — code_for_dev is only set when no Resend key.
    """
    code = generate_code()
    store_verification(email, code)

    success, msg = send_verification_email(email, code)

    # Return code for dev mode display
    dev_code = code if not RESEND_API_KEY else None
    return success, msg, dev_code
