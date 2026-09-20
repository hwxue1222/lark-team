from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.bby_today import BBYTodayAdminClient, DueJob
from app.cache import TTLCache
from app.lark_tasks import LarkTaskClient
from app.report_cards import build_morning_report_card

logger = logging.getLogger("secretary")


@dataclass(frozen=True)
class SecretaryConfig:
    enabled: bool
    poll_interval_seconds: int
    timezone: str
    morning_report_time: str
    morning_report_chat_id: str | None
    due_jobs_path: str
    task_assignee_open_id: str | None


class SecretaryService:
    def __init__(
        self,
        *,
        cfg: SecretaryConfig,
        bby_today: BBYTodayAdminClient | None,
        lark_tasks: LarkTaskClient,
        send_report_card,
    ) -> None:
        self._cfg = cfg
        self._bby_today = bby_today
        self._lark_tasks = lark_tasks
        self._send_report_card = send_report_card
        self._stop = threading.Event()
        self._created_jobs = TTLCache(ttl_seconds=24 * 3600)
        self._reported_days = TTLCache(ttl_seconds=48 * 3600)

    def start(self) -> None:
        if not self._cfg.enabled:
            return
        t = threading.Thread(target=self._run, daemon=True)
        t.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        tz = ZoneInfo(self._cfg.timezone)
        next_report_at = self._next_report_time(tz)

        while not self._stop.is_set():
            try:
                self._poll_due_jobs()
            except Exception:
                logger.exception("poll_due_jobs failed")

            now = datetime.now(tz)
            if self._cfg.morning_report_chat_id and now >= next_report_at:
                day_key = now.strftime("%Y-%m-%d")
                if self._reported_days.add_if_absent(f"report:{day_key}"):
                    try:
                        jobs = self._fetch_jobs_for_report()
                        card = build_morning_report_card(title="BBY 中控", date_label=day_key, jobs=jobs)
                        self._send_report_card(self._cfg.morning_report_chat_id, card)
                        logger.info("morning_report sent day=%s", day_key)
                    except Exception:
                        logger.exception("morning_report failed")
                next_report_at = self._next_report_time(tz)

            self._stop.wait(timeout=max(5, self._cfg.poll_interval_seconds))

    def _poll_due_jobs(self) -> None:
        if not self._bby_today:
            return
        jobs = self._bby_today.fetch_due_jobs(path=self._cfg.due_jobs_path)
        for j in jobs:
            job_key = f"due_job:{j.job_id}"
            if not self._created_jobs.add_if_absent(job_key):
                continue
            try:
                summary = f"[Due] {j.title}"
                desc = j.url or ""
                self._lark_tasks.create_task(
                    summary=summary,
                    description=desc,
                    due_at=j.due_at,
                    assignee_open_id=self._cfg.task_assignee_open_id,
                )
                logger.info("created lark task job_id=%s", j.job_id)
            except Exception:
                logger.exception("create task failed job_id=%s", j.job_id)

    def _fetch_jobs_for_report(self) -> list[DueJob]:
        if not self._bby_today:
            return []
        return self._bby_today.fetch_due_jobs(path=self._cfg.due_jobs_path)

    def _next_report_time(self, tz: ZoneInfo) -> datetime:
        hh, mm = _parse_hhmm(self._cfg.morning_report_time)
        now = datetime.now(tz)
        candidate = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if candidate <= now:
            candidate = candidate + timedelta(days=1)
        return candidate


def _parse_hhmm(v: str) -> tuple[int, int]:
    s = v.strip()
    if ":" not in s:
        return 8, 30
    a, b = s.split(":", 1)
    try:
        return int(a), int(b)
    except Exception:
        return 8, 30

