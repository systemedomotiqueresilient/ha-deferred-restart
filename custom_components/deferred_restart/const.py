"""Constantes de Deferred Restart."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "deferred_restart"
VERSION = "0.3.1"  # à garder identique à manifest.json et au fichier VERSION

CONF_BEFORE = "minutes_before"
CONF_AFTER = "minutes_after"
CONF_MAX_DEFER = "max_defer_minutes"
CONF_MIN_PATTERN = "min_pattern_interval"
CONF_ANY_RUNNING = "block_on_any_running"
CONF_EXCLUDE = "excluded_automations"
CONF_PAUSE = "pause_minutes"

DEFAULTS: dict = {
    CONF_BEFORE: 15,
    CONF_AFTER: 5,
    CONF_MAX_DEFER: 60,  # 0 = pas de limite
    CONF_MIN_PATTERN: 60,  # time_pattern plus fréquent que ça : ignoré
    CONF_ANY_RUNNING: False,
    CONF_EXCLUDE: [],
    CONF_PAUSE: 120,  # durée de pause de la protection (mode dev)
}

SERVICE_FORCE_RESTART = "force_restart"
SERVICE_CANCEL_PENDING = "cancel_pending"

SIGNAL_UPDATE = f"{DOMAIN}_update"
NOTIFICATION_ID = f"{DOMAIN}_pending"

SCAN_INTERVAL = timedelta(seconds=30)
HORIZON = timedelta(hours=24)
CALENDAR_CACHE_TTL = timedelta(minutes=5)
