"""Le numéro de version doit être identique partout."""

from __future__ import annotations

import json
from pathlib import Path
import re
import tomllib

from custom_components.deferred_restart.const import VERSION

ROOT = Path(__file__).parent.parent


def test_versions_are_consistent() -> None:
    manifest = json.loads((ROOT / "custom_components/deferred_restart/manifest.json").read_text())
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert manifest["version"] == VERSION
    assert (ROOT / "VERSION").read_text().strip() == VERSION
    assert pyproject["project"]["version"] == VERSION
    for readme in ("README.md", "README.fr.md"):
        assert re.search(rf"\b{re.escape(VERSION)}\b", (ROOT / readme).read_text()), readme
    assert f"## [{VERSION}]" in (ROOT / "CHANGELOG.md").read_text()
