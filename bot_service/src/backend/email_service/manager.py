"""Email service manager for sending emails using SMTP."""

import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import List, Optional

import aiosmtplib
from common.configuration import Configuration
from common.logger import logger
from jinja2 import DictLoader, Environment


class EmailServiceManager:
    """Manages email sending functionality using SMTP."""

    def __init__(self, config: Configuration):
        """Initialize the email service manager."""
        self.config = config
        self.smtp_config = self.config.configuration().smtp_configuration

        if self.smtp_config.host is None or self.smtp_config.host.strip() == "" or self.smtp_config.host == "YOUR_SMTP_HOST":
            logger.critical("SMTP credentials are not configured. Sending emails wont's work !.")

        # Email templates with Material UI design - neutral colors and consistent styling
        self.templates = {
            "registration_confirmation": """
            <html>
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <style>
                        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500&display=swap');
                        body {
                            margin: 0;
                            padding: 24px;
                            font-family: 'Roboto', -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                            background-color: #fafafa;
                            color: rgba(0, 0, 0, 0.87);
                            line-height: 1.5;
                        }
                        .container {
                            max-width: 600px;
                            margin: 0 auto;
                            background: #ffffff;
                            border-radius: 8px;
                            overflow: hidden;
                            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                        }
                        .header {
                            background: #1976d2;
                            padding: 24px;
                            text-align: center;
                            color: #ffffff;
                        }
                        .header h1 {
                            margin: 0;
                            font-size: 24px;
                            font-weight: 500;
                            letter-spacing: 0.15px;
                        }
                        .content {
                            padding: 24px;
                        }
                        .greeting {
                            font-size: 16px;
                            font-weight: 400;
                            color: rgba(0, 0, 0, 0.87);
                            margin-bottom: 16px;
                        }
                        .text {
                            font-size: 14px;
                            line-height: 1.5;
                            color: rgba(0, 0, 0, 0.6);
                            margin-bottom: 20px;
                        }
                        .cta-button {
                            display: inline-block;
                            background: #1565c0;
                            color: #ffffff;
                            padding: 12px 24px;
                            text-decoration: none;
                            border-radius: 4px;
                            font-weight: 500;
                            font-size: 14px;
                            text-transform: uppercase;
                            letter-spacing: 0.75px;
                            margin: 16px 0;
                            transition: background-color 0.2s ease;
                        }
                        .cta-button:hover {
                            background: #0d47a1;
                        }
                        .footer {
                            background: #f5f5f5;
                            padding: 16px 24px;
                            text-align: center;
                            border-top: 1px solid #e0e0e0;
                        }
                        .footer-text {
                            font-size: 12px;
                            color: rgba(0, 0, 0, 0.6);
                            line-height: 1.4;
                        }
                        .notice {
                            background: #f5f5f5;
                            border: 1px solid #bdbdbd;
                            border-radius: 4px;
                            padding: 12px 16px;
                            margin: 16px 0;
                            font-size: 12px;
                            color: rgba(0, 0, 0, 0.87);
                        }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>Welcome to {{ app_name }}</h1>
                        </div>
                        <div class="content">
                            <div class="greeting">Dear {{ user_name }},</div>
                            <div class="text">
                                Thank you for registering with {{ app_name }}. To complete your registration and activate your account,
                                please verify your email address by clicking the button below.
                            </div>
                            <div style="text-align: center;">
                                <a href="{{ verification_link }}" class="cta-button">Verify Email</a>
                            </div>
                            <div class="notice">
                                Please note: This verification link will expire in 24 hours for security purposes.
                            </div>
                            <div class="text" style="font-size: 12px; color: rgba(0, 0, 0, 0.54);">
                                If you did not create this account, please disregard this email.
                            </div>
                        </div>
                        <div class="footer">
                            <div class="footer-text">
                                Regards,<br>
                                The {{ app_name }} Team
                            </div>
                        </div>
                    </div>
                </body>
            </html>
            """,
            "password_reset": """
            <html>
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <style>
                        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500&display=swap');
                        body {
                            margin: 0;
                            padding: 24px;
                            font-family: 'Roboto', -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                            background-color: #fafafa;
                            color: rgba(0, 0, 0, 0.87);
                            line-height: 1.5;
                        }
                        .container {
                            max-width: 600px;
                            margin: 0 auto;
                            background: #ffffff;
                            border-radius: 8px;
                            overflow: hidden;
                            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                        }
                        .header {
                            background: #d32f2f;
                            padding: 24px;
                            text-align: center;
                            color: #ffffff;
                        }
                        .header h1 {
                            margin: 0;
                            font-size: 24px;
                            font-weight: 500;
                            letter-spacing: 0.15px;
                        }
                        .content {
                            padding: 24px;
                        }
                        .greeting {
                            font-size: 16px;
                            font-weight: 400;
                            color: rgba(0, 0, 0, 0.87);
                            margin-bottom: 16px;
                        }
                        .text {
                            font-size: 14px;
                            line-height: 1.5;
                            color: rgba(0, 0, 0, 0.6);
                            margin-bottom: 20px;
                        }
                        .cta-button {
                            display: inline-block;
                            background: #c62828;
                            color: #ffffff;
                            padding: 12px 24px;
                            text-decoration: none;
                            border-radius: 4px;
                            font-weight: 500;
                            font-size: 14px;
                            text-transform: uppercase;
                            letter-spacing: 0.75px;
                            margin: 16px 0;
                            transition: background-color 0.2s ease;
                        }
                        .cta-button:hover {
                            background: #b71c1c;
                        }
                        .footer {
                            background: #f5f5f5;
                            padding: 16px 24px;
                            text-align: center;
                            border-top: 1px solid #e0e0e0;
                        }
                        .footer-text {
                            font-size: 12px;
                            color: rgba(0, 0, 0, 0.6);
                            line-height: 1.4;
                        }
                        .notice {
                            background: #f5f5f5;
                            border: 1px solid #bdbdbd;
                            border-radius: 4px;
                            padding: 12px 16px;
                            margin: 16px 0;
                            font-size: 12px;
                            color: rgba(0, 0, 0, 0.87);
                        }
                        .security-note {
                            background: #fff3e0;
                            border: 1px solid #ff9800;
                            border-radius: 4px;
                            padding: 12px 16px;
                            margin: 16px 0;
                            font-size: 12px;
                            color: rgba(0, 0, 0, 0.87);
                        }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>Password Reset Request</h1>
                        </div>
                        <div class="content">
                            <div class="greeting">Dear {{ user_name }},</div>
                            <div class="text">
                                We received a request to reset your password for your {{ app_name }} account.
                                To proceed with the password reset, please click the button below.
                            </div>
                            <div style="text-align: center;">
                                <a href="{{ reset_link }}" class="cta-button">Reset Password</a>
                            </div>
                            <div class="notice">
                                Important: This password reset link will expire in 1 hour for security purposes.
                            </div>
                            <div class="security-note">
                                Security Notice: If you did not request this password reset, please disregard this email.
                                Your account remains secure and no changes have been made.
                            </div>
                        </div>
                        <div class="footer">
                            <div class="footer-text">
                                Regards,<br>
                                The {{ app_name }} Security Team
                            </div>
                        </div>
                    </div>
                </body>
            </html>
            """,
            "user_invitation": """
            <html>
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <style>
                        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500&display=swap');
                        body {
                            margin: 0;
                            padding: 24px;
                            font-family: 'Roboto', -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                            background-color: #fafafa;
                            color: rgba(0, 0, 0, 0.87);
                            line-height: 1.5;
                        }
                        .container {
                            max-width: 600px;
                            margin: 0 auto;
                            background: #ffffff;
                            border-radius: 8px;
                            overflow: hidden;
                            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                        }
                        .header {
                            background: #388e3c;
                            padding: 24px;
                            text-align: center;
                            color: #ffffff;
                        }
                        .header h1 {
                            margin: 0;
                            font-size: 24px;
                            font-weight: 500;
                            letter-spacing: 0.15px;
                        }
                        .content {
                            padding: 24px;
                        }
                        .greeting {
                            font-size: 16px;
                            font-weight: 400;
                            color: rgba(0, 0, 0, 0.87);
                            margin-bottom: 16px;
                        }
                        .text {
                            font-size: 14px;
                            line-height: 1.5;
                            color: rgba(0, 0, 0, 0.6);
                            margin-bottom: 20px;
                        }
                        .cta-button {
                            display: inline-block;
                            background: #2e7d32;
                            color: #ffffff;
                            padding: 12px 24px;
                            text-decoration: none;
                            border-radius: 4px;
                            font-weight: 500;
                            font-size: 14px;
                            text-transform: uppercase;
                            letter-spacing: 0.75px;
                            margin: 16px 0;
                            transition: background-color 0.2s ease;
                        }
                        .cta-button:hover {
                            background: #1b5e20;
                        }
                        .footer {
                            background: #f5f5f5;
                            padding: 16px 24px;
                            text-align: center;
                            border-top: 1px solid #e0e0e0;
                        }
                        .footer-text {
                            font-size: 12px;
                            color: rgba(0, 0, 0, 0.6);
                            line-height: 1.4;
                        }
                        .notice {
                            background: #f5f5f5;
                            border: 1px solid #bdbdbd;
                            border-radius: 4px;
                            padding: 12px 16px;
                            margin: 16px 0;
                            font-size: 12px;
                            color: rgba(0, 0, 0, 0.87);
                        }
                        .inviter-info {
                            background: #e8f5e8;
                            border-radius: 4px;
                            padding: 16px;
                            margin: 16px 0;
                            border-left: 4px solid #4caf50;
                        }
                        .inviter-name {
                            font-weight: 500;
                            color: rgba(0, 0, 0, 0.87);
                            font-size: 16px;
                        }
                        .inviter-label {
                            color: rgba(0, 0, 0, 0.6);
                            margin-top: 4px;
                            font-size: 12px;
                        }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>Invitation to Join {{ app_name }}</h1>
                        </div>
                        <div class="content">
                            <div class="greeting">Dear {{ invitee_name }},</div>
                            <div class="inviter-info">
                                <div class="inviter-name">{{ inviter_name }}</div>
                                <div class="inviter-label">
                                    has invited you to join {{ app_name }}
                                </div>
                            </div>
                            <div class="text">
                                You have been invited to join our platform. To accept this invitation and create your account,
                                please click the button below.
                            </div>
                            <div style="text-align: center;">
                                <a href="{{ invitation_link }}" class="cta-button">Accept Invitation</a>
                            </div>
                            <div class="notice">
                                Please note: This invitation will expire in 7 days.
                            </div>
                            <div class="text" style="font-size: 12px; color: rgba(0, 0, 0, 0.54);">
                                If you were not expecting this invitation, you may disregard this email.
                            </div>
                        </div>
                        <div class="footer">
                            <div class="footer-text">
                                Regards,<br>
                                The {{ app_name }} Team
                            </div>
                        </div>
                    </div>
                </body>
            </html>
            """,
        }

        self.template_env = Environment(loader=DictLoader(self.templates), autoescape=True)

    async def send_email_async(
        self,
        to_emails: List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        from_email: Optional[str] = None,
    ) -> bool:
        """Send an email asynchronously using aiosmtplib."""
        try:

            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = formataddr((self.smtp_config.from_name, from_email or self.smtp_config.from_email))
            message["To"] = ", ".join(to_emails)

            # Add text part if provided
            if text_content:
                text_part = MIMEText(text_content, "plain")
                message.attach(text_part)

            # Add HTML part
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)

            # Send email over TLS
            await aiosmtplib.send(message, hostname=self.smtp_config.host, port=self.smtp_config.port, username=self.smtp_config.username, password=self.smtp_config.password, start_tls=True, use_tls=False)

            logger.info(f"Email sent successfully to {to_emails}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_emails}: {str(e)}")
            return False  # noqa: ASYNC910

    def send_email_sync(
        self,
        to_emails: List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        from_email: Optional[str] = None,
    ) -> bool:
        """Send an email synchronously using smtplib."""
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = formataddr((self.smtp_config.from_name, from_email or self.smtp_config.from_email))
            message["To"] = ", ".join(to_emails)

            # Add text part if provided
            if text_content:
                text_part = MIMEText(text_content, "plain")
                message.attach(text_part)

            # Add HTML part
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)

            # Send email
            server = smtplib.SMTP(self.smtp_config.host, self.smtp_config.port)
            server.starttls()
            server.login(self.smtp_config.username, self.smtp_config.password)
            server.send_message(message)
            server.quit()

            logger.info(f"Email sent successfully to {to_emails}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_emails}: {str(e)}")
            return False

    async def send_registration_confirmation(self, email: str, user_name: str, verification_token: str, base_url: str = "http://localhost:8081") -> bool:
        """Send registration confirmation email."""
        template = self.template_env.get_template("registration_confirmation")
        verification_link = f"{base_url}/api/user/verify-email?token={verification_token}"

        html_content = template.render(app_name=self.config.configuration().application_name, user_name=user_name, verification_link=verification_link)

        return await self.send_email_async(to_emails=[email], subject=f"Verify Your {self.config.configuration().application_name} Account", html_content=html_content)

    async def send_password_reset(self, email: str, user_name: str, reset_token: str, base_url: str = "http://localhost:8081") -> bool:
        """Send password reset email."""
        template = self.template_env.get_template("password_reset")
        reset_link = f"{base_url}/api/user/reset-password?token={reset_token}"

        html_content = template.render(app_name=self.config.configuration().application_name, user_name=user_name, reset_link=reset_link)

        return await self.send_email_async(to_emails=[email], subject=f"Reset Your {self.config.configuration().application_name} Password", html_content=html_content)

    async def send_user_invitation(self, email: str, invitee_name: str, inviter_name: str, invitation_token: str, base_url: str) -> bool:
        """Send user invitation email."""
        template = self.template_env.get_template("user_invitation")
        invitation_link = f"{base_url}/api/user/accept-invitation?token={invitation_token}"

        html_content = template.render(app_name=self.config.configuration().application_name, invitee_name=invitee_name, inviter_name=inviter_name, invitation_link=invitation_link)

        return await self.send_email_async(to_emails=[email], subject=f"Invitation to Join {self.config.configuration().application_name}", html_content=html_content)
