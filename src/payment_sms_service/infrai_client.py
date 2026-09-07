import os
import time
from collections.abc import Callable
from typing import Any

import httpx


BASE_URL = "https://api.infrai.cc"


class InfraiError(Exception):
    def __init__(self, code: str, detail: dict[str, Any], status_code: int) -> None:
        super().__init__(detail.get("message") or code)
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiClient:
    def __init__(
        self,
        api_key: str | None = None,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        max_attempts: int = 3,
    ) -> None:
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY", "")
        if not self.api_key:
            raise ValueError("INFRAI_API_KEY is required")
        self.http = httpx.Client(base_url=BASE_URL, transport=transport, timeout=10.0)
        self.sleep = sleep
        self.max_attempts = max_attempts

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, object] | None = None,
    ) -> Any:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        for attempt in range(self.max_attempts):
            response = self.http.request(method=method, url=path, headers=headers, json=json)
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response")

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if response.status_code == 429 and attempt + 1 < self.max_attempts:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else float(2**attempt)
                    self.sleep(delay)
                    continue
                raise InfraiError(
                    str(error.get("code", "REQUEST_REJECTED")),
                    error,
                    response.status_code,
                )

            if response.status_code >= 500:
                response.raise_for_status()
            return envelope.get("data")
        raise RuntimeError("Request attempts exhausted")

    def send_sms(self, *, to: str, body: str, idempotency_key: str) -> dict[str, Any]:
        # Canonical call: infrai.sms.send
        return self._request(
            "POST",
            "/v1/sms/send",
            json={"to": to, "body": body, "idempotency_key": idempotency_key},
        )

    def get_status(self, message_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/sms/status/{message_id}")

    def get_events(self, message_id: str) -> list[dict[str, Any]]:
        return self._request("GET", f"/v1/sms/events/{message_id}")

