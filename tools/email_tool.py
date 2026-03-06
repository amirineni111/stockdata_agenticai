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
    get_email_recipients,
    get_email_recipients_by_type,
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
            # Get recipients grouped by type (TO/CC/BCC)
            by_type = get_email_recipients_by_type("daily_briefing")
            all_recipients = by_type["TO"] + by_type["CC"] + by_type["BCC"]
            if not all_recipients:
                return "Error: No email recipients configured in database or .env"

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{EMAIL_FROM_NAME} <{EMAIL_FROM}>" if EMAIL_FROM_NAME else EMAIL_FROM
            if by_type["TO"]:
                msg["To"] = ", ".join(by_type["TO"])
            if by_type["CC"]:
                msg["Cc"] = ", ".join(by_type["CC"])
            if by_type["BCC"]:
                msg["Bcc"] = ", ".join(by_type["BCC"])

            # Attach the HTML body
            html_part = MIMEText(html_body, "html")
            msg.attach(html_part)

            # Connect to Office 365 SMTP and send
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.sendmail(EMAIL_FROM, all_recipients, msg.as_string())

            return f"Email sent successfully to {len(all_recipients)} recipients with subject: {subject}"

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
