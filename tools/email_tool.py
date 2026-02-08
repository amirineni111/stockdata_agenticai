"""
Office 365 email sending tool for the Report Compiler Agent.
Sends the final HTML briefing email via SMTP.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from crewai.tools import BaseTool
from pydantic import Field, BaseModel
from typing import Type

from config.settings import (
    SMTP_SERVER,
    SMTP_PORT,
    SMTP_USERNAME,
    SMTP_PASSWORD,
    EMAIL_FROM,
    EMAIL_FROM_NAME,
    EMAIL_TO,
)


class SendEmailInput(BaseModel):
    """Input schema for the email tool."""
    subject: str = Field(description="The email subject line.")
    html_body: str = Field(description="The HTML content of the email body.")


class SendEmailTool(BaseTool):
    """
    Sends an HTML email via Office 365 SMTP.
    Used by the Report Compiler Agent to deliver the daily briefing.
    """
    name: str = "send_email_tool"
    description: str = (
        "Send an HTML email via Office 365 SMTP. "
        "Use this to deliver the daily briefing report. "
        "Provide a subject line and the HTML body content."
    )
    args_schema: Type[BaseModel] = SendEmailInput

    def _run(self, subject: str, html_body: str) -> str:
        """Send the email and return status."""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{EMAIL_FROM_NAME} <{EMAIL_FROM}>" if EMAIL_FROM_NAME else EMAIL_FROM
            msg["To"] = EMAIL_TO

            # Attach the HTML body
            html_part = MIMEText(html_body, "html")
            msg.attach(html_part)

            # Connect to Office 365 SMTP and send
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.sendmail(EMAIL_FROM, EMAIL_TO.split(","), msg.as_string())

            return f"Email sent successfully to {EMAIL_TO} with subject: {subject}"

        except smtplib.SMTPAuthenticationError:
            return (
                "Email authentication failed. Check SMTP_USERNAME and "
                "SMTP_PASSWORD in your .env file. For Office 365, you may "
                "need an App Password if MFA is enabled."
            )
        except smtplib.SMTPException as e:
            return f"SMTP Error: {str(e)}"
        except Exception as e:
            return f"Error sending email: {str(e)}"
