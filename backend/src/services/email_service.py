"""Optional email notifications (US6 / FR-025).

Silently disabled when `SMTP_HOST` is empty — no attempt is made and nothing fails.
aiosmtplib is imported lazily so it is only needed when email is actually configured.
"""

from ..config import Settings


def is_enabled(settings: Settings) -> bool:
    return bool(settings.smtp_host)


async def send_email(settings: Settings, to: str, subject: str, body: str) -> bool:
    if not is_enabled(settings):
        return False
    try:
        from email.message import EmailMessage

        import aiosmtplib  # imported lazily

        message = EmailMessage()
        message["From"] = settings.smtp_from
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        await aiosmtplib.send(message, hostname=settings.smtp_host, port=settings.smtp_port)
        return True
    except Exception:  # noqa: BLE001 — notifications are best-effort
        return False
