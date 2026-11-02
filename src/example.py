import os

from password_reset_service import InfraiClient, PasswordResetRequest, decide_password_reset


def main() -> None:
    request = PasswordResetRequest(
        user_id="user-1842",
        email=os.environ["RESET_EMAIL"],
        reset_link="https://pay.example.com/reset/example-token",
        payment_event_id="payment-event-2026-001",
        risk_score=42,
    )
    result = decide_password_reset(request, InfraiClient())
    print(result)


if __name__ == "__main__":
    main()
