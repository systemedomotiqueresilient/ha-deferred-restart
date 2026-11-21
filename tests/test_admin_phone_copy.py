"""La copie d'admin_phone.py doit rester identique à la référence ha-sdr."""

from __future__ import annotations

import hashlib
from pathlib import Path

from custom_components.deferred_restart import admin_phone

# Référence : ha-sdr, commit 77a8992, MODULE_VERSION 1.2.0.
EXPECTED_VERSION = "1.2.0"
EXPECTED_SHA256 = "1d720150ff1c709547018236afcb1c555e630c504be0c34b20fe0b79ed80545b"


def test_admin_phone_is_unmodified_copy() -> None:
    content = Path(admin_phone.__file__).read_bytes()
    assert hashlib.sha256(content).hexdigest() == EXPECTED_SHA256
    assert admin_phone.MODULE_VERSION == EXPECTED_VERSION


def test_own_domain_is_a_sibling() -> None:
    """Les autres intégrations SDR doivent pouvoir lire notre entité."""
    assert "deferred_restart" in admin_phone.SIBLING_PLATFORMS
