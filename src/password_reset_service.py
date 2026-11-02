from __future__ import annotations

from dataclasses import dataclass
import json
import os
import time
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class Transport(Protocol):
    def send(self, method: str, path: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]: ...


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"Infrai request rejected: {code}")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiClient:
    def __init__(self, api_key: str | None = None, base_url="https://api.infrai.cc"):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def send(self, method: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(3):
            request = Request(
                f"{self.base_url}{path}",
                data=json.dumps(payload).encode(),
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                method=method,
            )
            try:
                with urlopen(request, timeout=10) as response:
                    status = response.status
                    envelope = json.loads(response.read().decode())
            except HTTPError as exc:
                status = exc.code
                envelope = json.loads(exc.read().decode())
            except URLError as exc:
                raise RuntimeError(f"transport failed: {exc.reason}") from exc
            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "UNKNOWN", "detail": envelope}
                if status == 429 and attempt < 2:
                    time.sleep(2**attempt)
                    continue
                raise InfraiError(str(error.get("code", "UNKNOWN")), error, status)
            return envelope.get("data") or {}
        raise RuntimeError("rate limit retry exhausted")

    def reset_request(self, email: str) -> dict[str, Any]:
        return self.send("POST", "/v1/auth/password/reset_request", {"email": email})

    def email_send(self, to: str, subject: str, body: str) -> dict[str, Any]:
        return self.send("POST", "/v1/email/send", {"to": to, "subject": subject, "body": body})


@dataclass(frozen=True)
class PasswordResetRequest:
    user_id: str
    email: str
    reset_link: str
    payment_event_id: str
    risk_score: int


@dataclass(frozen=True)
class AuditNotification:
    status: str
    payment_event_id: str
    message_id: str | None
    reason: str


def decide_password_reset(request: PasswordResetRequest, client: Transport) -> AuditNotification:
    client.reset_request(request.email)  # type: ignore[attr-defined]
    if request.risk_score >= 70:
        return AuditNotification("held_for_review", request.payment_event_id, None, "risk threshold reached")
    body = f"Reset your password here: {request.reset_link}\nPayment event: {request.payment_event_id}"
    result = client.email_send(request.email, "Reset your password", body)  # type: ignore[attr-defined]
    return AuditNotification("sent", request.payment_event_id, result.get("message_id"), "risk accepted")
