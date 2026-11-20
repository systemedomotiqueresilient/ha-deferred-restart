"""La copie d'admin_phone.py doit rester identique à la référence ha-sdr."""

from __future__ import annotations

import hashlib
from pathlib import Path

from custom_components.deferred_restart import admin_phone

# Référence : ha-sdr, commit dfc42ab, MODULE_VERSION 1.1.0.
EXPECTED_VERSION = "1.1.0"
EXPECTED_SHA256 = "32b3619e975eaeb0606252b4cdca9f3d2402854193f88619cd4bde383b30e1f9"


def test_admin_phone_is_unmodified_copy() -> None:
    content = Path(admin_phone.__file__).read_bytes()
    assert hashlib.sha256(content).hexdigest() == EXPECTED_SHA256
    assert admin_phone.MODULE_VERSION == EXPECTED_VERSION


def test_own_domain_is_a_sibling() -> None:
    """Les autres intégrations SDR doivent pouvoir lire notre entité."""
    assert "deferred_restart" in admin_phone.SIBLING_PLATFORMS
