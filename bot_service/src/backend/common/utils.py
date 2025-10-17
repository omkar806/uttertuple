# Only put reusable functions here

import mimetypes
import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Any, Dict, Tuple

from dotenv import find_dotenv, load_dotenv
from passlib.context import CryptContext

_ = load_dotenv(find_dotenv())


def send_alert(
    message="Message to send",
    subject="Alert",
    file_to_send=None,
    filename="alert_log.txt",
    mail_to="",
    mail_cc="",
):
    """Send an email alert with an attachment if any

    Args:
        message (str): Message to be sent via email
        subject (str): Subject of the email. Defaults to Alert
        file_to_send (str, optional): Path to file to send via email attachment. Defaults to None.
        filename (str, optional): File name of the attachment. Defaults to 'alert_log.txt'.
        mail_to (str, optional): Recipient of the email. Defaults to ""
        mail_cc (str, optional): CC of the email. Defaults to ""
    """

    SMTP_HOST = os.getenv("SMTP_HOST", None)
    SMTP_TLS_PORT = os.getenv("SMTP_TLS_PORT", 587)
    SMTP_MAIL_FROM = os.getenv("SMTP_MAIL_FROM", None)
    SMTP_MAIL_TO = os.getenv("SMTP_MAIL_TO", None)
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", None)
    SMTP_USER = os.getenv("SMTP_USER", None)
    SMTP_DISPLAY_NAME = os.getenv("SMTP_DISPLAY_NAME", "Alert Service")
    msg = MIMEMultipart()

    msg["Subject"] = subject
    msg["From"] = SMTP_MAIL_FROM
    msg["From"] = formataddr((SMTP_DISPLAY_NAME, SMTP_MAIL_FROM))

    if mail_to:
        SMTP_MAIL_TO = mail_to
    if mail_cc:
        msg["Cc"] = mail_cc

    # msg['To'] requires SMTP_MAIL_TO to be a string
    msg["To"] = SMTP_MAIL_TO
    msg.attach(MIMEText(message, "html"))

    if file_to_send:
        ctype, encoding = mimetypes.guess_type(file_to_send)
        if ctype is None or encoding is not None:
            ctype = "text/*"

        maintype, subtype = ctype.split("/", 1)

        if "xlsx" not in file_to_send:
            with open(file_to_send, encoding="utf-8") as fp:
                attachment = MIMEText(fp.read(), _subtype="subtype")
                # encoders.encode_base64(attachment)
                attachment.add_header("Content-Disposition", "attachment", filename=filename)
                msg.attach(attachment)
        else:
            with open(file_to_send, "rb") as fp:
                # attachment = MIMEText(fp.read(), _subtype='xlsx')
                attachment = MIMEBase("application", "octet-stream")
                attachment.set_payload(open(file_to_send, "rb").read())
                encoders.encode_base64(attachment)
                attachment.add_header("Content-Disposition", "attachment", filename=f"{filename}.xlsx")
                msg.attach(attachment)

    with smtplib.SMTP(SMTP_HOST, SMTP_TLS_PORT) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(SMTP_USER, SMTP_PASSWORD)

        # sendmail requires SMTP_MAIL_TO to be a list
        smtp.sendmail(SMTP_MAIL_FROM, SMTP_MAIL_TO.split(","), msg.as_string())


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

import argon2

ph = argon2.PasswordHasher()


def get_password_hash(password: str):
    """Get hashed password

    Args:
        password (str): password to hash
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str):
    """Verify password

    Args:
        plain_password (str): plain password
        hashed_password (str): hashed password
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash_using_argon(password: str):
    """Get hashed password

    Args:
        password (str): password to hash
    """
    return ph.hash(password)


def verify_password_using_argon(plain_password: str, hashed_password: str):
    """Verify password

    Args:
        plain_password (str): plain password
        hashed_password (str): hashed password
    """
    return ph.verify(hashed_password, plain_password)


def custom_key_builder(fn: Any, *args: Tuple[Any], **kwargs: Dict[str, Any]) -> str:
    """Custom key builder for cache entries.

    Args:
        fn: The function being cached
        args: Positional arguments
        kwargs: Keyword arguments

    Returns:
        Formatted cache key as string
    """
    fname = fn.__name__

    # Filter out non-cacheable arguments
    filtered_kwargs = {}
    for k, v in kwargs.items():
        # Skip Request objects and other non-serializable objects
        if k in ["request"]:
            continue
        # Convert complex objects to string representation
        try:
            if hasattr(v, "__dict__"):
                # For objects like ListFilesRequest, User, etc.
                if hasattr(v, "id"):
                    filtered_kwargs[k] = f"{type(v).__name__}_{v.id}"
                else:
                    # Convert object attributes to a stable string
                    attrs = {attr: getattr(v, attr) for attr in dir(v) if not attr.startswith("_") and not callable(getattr(v, attr))}
                    filtered_kwargs[k] = f"{type(v).__name__}_{hash(str(sorted(attrs.items())))}"
            else:
                filtered_kwargs[k] = str(v)
        except Exception:
            # Fallback for problematic objects
            filtered_kwargs[k] = f"{type(v).__name__}"

    # Format args/kwargs into string
    args_str = ":".join(str(arg) for arg in args if arg is not None)
    kwargs_str = ":".join(f"{k}={v}" for k, v in filtered_kwargs.items())

    # Build key with components
    key_parts = [fname]
    if args_str:
        key_parts.append(args_str)
    if kwargs_str:
        key_parts.append(kwargs_str)

    cache_key = ":".join(key_parts)
    return cache_key
