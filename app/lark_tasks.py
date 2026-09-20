from __future__ import annotations

from datetime import datetime

import lark_oapi as lark


class LarkTaskClient:
    def __init__(self, *, client: lark.Client, timezone: str) -> None:
        self._client = client
        self._timezone = timezone

    def create_task(self, *, summary: str, description: str, due_at: datetime | None, assignee_open_id: str | None) -> str | None:
        due = None
        if due_at:
            ts_ms = int(due_at.timestamp() * 1000)
            due = lark.api.task.v1.Due.builder().time(ts_ms).timezone(self._timezone).is_all_day(False).build()

        task_builder = lark.api.task.v1.Task.builder().summary(summary).description(description)
        if due:
            task_builder = task_builder.due(due)
        if assignee_open_id:
            task_builder = task_builder.collaborator_ids([assignee_open_id])

        req = (
            lark.api.task.v1.CreateTaskRequest.builder()
            .user_id_type("open_id")
            .request_body(task_builder.build())
            .build()
        )

        resp = self._client.task.v1.task.create(req)
        if not resp.success():
            raise RuntimeError(f"lark create_task failed: code={resp.code} msg={resp.msg}")
        task_id = getattr(resp.data, "id", None) if resp.data else None
        return str(task_id) if task_id else None

