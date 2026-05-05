"""
common/email_utils.py
Shared email sender used by all three scripts.
Reads credentials from environment variables (set as GitHub Secrets).
"""

import os
import smtplib
import time
from email.headerregistry import Address
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from typing import Optional


def send_email(
    subject: str,
    body_text: str,
    body_html: str,
    recipient_override: Optional[str] = None,
) -> None:
    """
    Send a plain+HTML multipart email via SMTP.

    recipient_override: if set, ignores EMAIL_RECIPIENT env var.
    Useful for alert scripts that may use a different recipient.
    """
    EU   = os.getenv("EMAIL_USERNAME")
    EP   = os.getenv("EMAIL_PASSWORD")
    ER   = recipient_override or os.getenv("EMAIL_RECIPIENT", "")
    CC   = os.getenv("EMAIL_CC",  "").strip()
    BCC  = os.getenv("EMAIL_BCC", "").strip()
    HOST = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    PORT = int(os.getenv("SMTP_PORT", "587"))

    if not EU or not EP or not ER:
        raise RuntimeError(
            "Missing: EMAIL_USERNAME / EMAIL_PASSWORD / EMAIL_RECIPIENT"
        )

    to_list  = [x.strip() for x in ER.split(",")  if x.strip()]
    cc_list  = [x.strip() for x in CC.split(",")  if x.strip()]
    bcc_list = [x.strip() for x in BCC.split(",") if x.strip()]
    all_rcpt = to_list + cc_list + bcc_list

    msg = MIMEMultipart("alternative")
    try:
        local, domain = EU.split("@", 1)
        msg["From"] = str(Address("Enerwave Energy Intel", local, domain))
    except Exception:
        msg["From"] = EU
    msg["To"]         = ", ".join(to_list)
    if cc_list:
        msg["Cc"]     = ", ".join(cc_list)
    msg["Subject"]    = subject
    msg["Date"]       = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid()
    msg.attach(MIMEText(body_text, "plain", "utf-8"))
    msg.attach(MIMEText(body_html, "html",  "utf-8"))

    last_exc: Optional[Exception] = None
    for mode, host, port in [("STARTTLS", HOST, PORT), ("SSL", HOST, 465)]:
        for _ in range(2):
            srv = None
            try:
                if mode == "STARTTLS":
                    srv = smtplib.SMTP(host, port, timeout=20)
                    srv.ehlo(); srv.starttls(); srv.ehlo()
                else:
                    srv = smtplib.SMTP_SSL(host, port, timeout=20)
                srv.login(EU, EP)
                srv.sendmail(EU, all_rcpt, msg.as_string())
                return
            except Exception as exc:
                last_exc = exc
                time.sleep(2)
            finally:
                try:
                    if srv:
                        srv.quit()
                except Exception:
                    pass
    raise RuntimeError(f"Email send failed: {last_exc}")
