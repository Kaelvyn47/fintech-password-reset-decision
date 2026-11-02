from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from password_reset_service import PasswordResetRequest, decide_password_reset


class FakeClient:
    def __init__(self):
        self.calls = []

    def reset_request(self, email):
        self.calls.append(("reset_request", email))
        return {}

    def email_send(self, to, subject, body):
        self.calls.append(("email_send", to, subject, body))
        return {"message_id": "message-7"}


def test_accepted_reset_is_sent_with_audit_event():
    client = FakeClient()
    request = PasswordResetRequest("user-1", "a@example.com", "https://example.com/r", "payment-9", 42)

    result = decide_password_reset(request, client)

    assert result.status == "sent"
    assert result.message_id == "message-7"
    assert result.payment_event_id == "payment-9"
    assert "payment-9" in client.calls[1][3]


def test_high_risk_reset_is_held_before_email():
    client = FakeClient()
    request = PasswordResetRequest("user-1", "a@example.com", "https://example.com/r", "payment-10", 80)

    result = decide_password_reset(request, client)

    assert result.status == "held_for_review"
    assert [call[0] for call in client.calls] == ["reset_request"]
