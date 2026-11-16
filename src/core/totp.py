"""RFC 6238 Standard Time-Based One-Time Password (TOTP) Implementation.
Provides zero-dependency HMAC-SHA1 two-factor authentication, secret key generation,
provisioning URI formatting, clock-drift tolerance, and backup code issuance.
"""

import base64
import hashlib
import hmac
import secrets
import struct
import time
import urllib.parse
from typing import List, Optional


class TOTPManager:
    """Zero-dependency RFC 6238 TOTP engine for multi-factor authentication."""

    DEFAULT_INTERVAL = 30
    DIGITS = 6

    @staticmethod
    def generate_secret(num_bytes: int = 20) -> str:
        """Generate a cryptographically secure Base32-encoded secret key."""
        random_bytes = secrets.token_bytes(num_bytes)
        return base64.b32encode(random_bytes).decode("ascii").rstrip("=")

    @classmethod
    def generate_totp(
        cls,
        secret_b32: str,
        timestamp: Optional[float] = None,
        interval: int = DEFAULT_INTERVAL,
    ) -> str:
        """Generate 6-digit TOTP token using HMAC-SHA1 algorithm."""
        if timestamp is None:
            timestamp = time.time()

        # Normalize Base32 padding
        padded_secret = secret_b32.upper()
        missing_padding = len(padded_secret) % 8
        if missing_padding:
            padded_secret += "=" * (8 - missing_padding)

        key = base64.b32decode(padded_secret, casefold=True)
        counter = int(timestamp // interval)
        counter_bytes = struct.pack(">Q", counter)

        h = hmac.new(key, counter_bytes, hashlib.sha1).digest()
        offset = h[-1] & 0x0F
        binary = struct.unpack(">I", h[offset : offset + 4])[0] & 0x7FFFFFFF
        token = str(binary % (10**cls.DIGITS)).zfill(cls.DIGITS)
        return token

    @classmethod
    def verify_totp(
        cls,
        secret_b32: str,
        code: str,
        window: int = 1,
        timestamp: Optional[float] = None,
    ) -> bool:
        """Verify TOTP token matching with window tolerance (±1 time step = ±30s)."""
        if not code or len(code.strip()) != cls.DIGITS:
            return False

        code = code.strip()
        now = time.time() if timestamp is None else timestamp
        for step in range(-window, window + 1):
            t = now + (step * cls.DEFAULT_INTERVAL)
            if cls.generate_totp(secret_b32, timestamp=t) == code:
                return True
        return False

    @classmethod
    def get_provisioning_uri(
        cls,
        secret_b32: str,
        account_name: str,
        issuer: str = "IMS Enterprise",
    ) -> str:
        """Generate standard otpauth:// URI for Google Authenticator and compatible apps."""
        escaped_issuer = urllib.parse.quote(issuer)
        escaped_account = urllib.parse.quote(account_name)
        label = f"{escaped_issuer}:{escaped_account}"
        params = urllib.parse.urlencode(
            {
                "secret": secret_b32,
                "issuer": issuer,
                "algorithm": "SHA1",
                "digits": cls.DIGITS,
                "period": cls.DEFAULT_INTERVAL,
            }
        )
        return f"otpauth://totp/{label}?{params}"

    @staticmethod
    def generate_backup_codes(count: int = 8) -> List[str]:
        """Generate single-use alphanumeric emergency backup recovery codes."""
        codes = []
        for _ in range(count):
            part1 = secrets.token_hex(2).upper()
            part2 = secrets.token_hex(2).upper()
            codes.append(f"{part1}-{part2}")
        return codes
