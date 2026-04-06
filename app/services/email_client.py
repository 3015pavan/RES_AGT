from __future__ import annotations

from email.message import EmailMessage

import aiosmtplib
from imapclient import IMAPClient
from tenacity import AsyncRetrying, Retrying, stop_after_attempt, wait_exponential

from app.core.config import Settings


class EmailClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def poll_unread(self, limit: int) -> list[dict]:
        # IMAP retrieval implementation is intentionally explicit and deterministic.
        retrying = Retrying(
            wait=wait_exponential(multiplier=1, min=1, max=8),
            stop=stop_after_attempt(3),
            reraise=True,
        )
        for attempt in retrying:
            with attempt:
                with IMAPClient(
                    self.settings.imap_host,
                    port=self.settings.imap_port,
                    ssl=True,
                    timeout=self.settings.external_call_timeout_seconds,
                ) as client:
                    client.login(self.settings.imap_user, self.settings.imap_password)
                    client.select_folder("INBOX")
                    messages = client.search(["UNSEEN"])
                    selected = messages[:limit]
                    fetched = client.fetch(selected, ["RFC822", "BODY[]", "ENVELOPE"])
                    return [{"uid": uid, "raw": data.get(b"RFC822") or data.get(b"BODY[]")} for uid, data in fetched.items()]
        return []

    async def send_reply(self, to_email: str, subject: str, body: str) -> None:
        msg = EmailMessage()
        msg["From"] = self.settings.smtp_from
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(body)

        async for attempt in AsyncRetrying(
            wait=wait_exponential(multiplier=1, min=1, max=8),
            stop=stop_after_attempt(3),
            reraise=True,
        ):
            with attempt:
                await aiosmtplib.send(
                    msg,
                    hostname=self.settings.smtp_host,
                    port=self.settings.smtp_port,
                    start_tls=True,
                    username=self.settings.smtp_user,
                    password=self.settings.smtp_password,
                    timeout=self.settings.external_call_timeout_seconds,
                )
