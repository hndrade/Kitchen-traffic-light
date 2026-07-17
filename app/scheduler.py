"""Background loop that watches the schedule and fires notifications."""
import threading
import time
from datetime import datetime, timedelta

from app.config import DAYS
from app.notifier import notify_kitchen_open, notify_opens_soon, notify_closes_soon

CHECK_INTERVAL_SECONDS = 20


def _parse_time(value):
    hour, minute = value.split(":")
    return int(hour), int(minute)


class Scheduler:
    """Polls the current config and fires each notification at most once per day."""

    def __init__(self, get_config):
        self._get_config = get_config
        self._thread = None
        self._stop_event = threading.Event()
        self._fired_today = set()
        self._current_day = None

    def start(self):
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()

    def _run(self):
        while not self._stop_event.is_set():
            self._tick()
            self._stop_event.wait(CHECK_INTERVAL_SECONDS)

    def _tick(self):
        now = datetime.now()
        day_name = DAYS[now.weekday()]

        if day_name != self._current_day:
            self._current_day = day_name
            self._fired_today = set()

        entry = self._get_config()["schedule"].get(day_name)
        if not entry or not entry.get("enabled"):
            return

        open_h, open_m = _parse_time(entry["open"])
        close_h, close_m = _parse_time(entry["close"])
        open_dt = now.replace(hour=open_h, minute=open_m, second=0, microsecond=0)
        close_dt = now.replace(hour=close_h, minute=close_m, second=0, microsecond=0)
        open_soon_dt = open_dt - timedelta(minutes=5)
        close_soon_dt = close_dt - timedelta(minutes=5)

        self._maybe_fire("open_soon", now, open_soon_dt, notify_opens_soon)
        self._maybe_fire("open", now, open_dt, notify_kitchen_open)
        self._maybe_fire("close_soon", now, close_soon_dt, notify_closes_soon)

    def _maybe_fire(self, key, now, target_dt, action):
        if key in self._fired_today:
            return
        if target_dt <= now < target_dt + timedelta(seconds=CHECK_INTERVAL_SECONDS * 2):
            action()
            self._fired_today.add(key)
