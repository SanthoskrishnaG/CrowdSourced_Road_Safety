import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
from uuid import UUID

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("app.notifications")


def send_email_notification(
    recipient_email: str,
    subject: str,
    body_text: str,
    body_html: Optional[str] = None
) -> bool:
    """
    Sends an email notification via configured SMTP provider,
    or logs the formatted email content if SMTP is not enabled.
    """
    if not settings.EMAIL_ENABLED or not settings.SMTP_HOST:
        logger.info(
            f"[MOCK EMAIL DISPATCH] To: {recipient_email} | Subject: {subject} | Content: {body_text[:100]}..."
        )
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = recipient_email

        msg.attach(MIMEText(body_text, "plain"))
        if body_html:
            msg.attach(MIMEText(body_html, "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM_EMAIL, [recipient_email], msg.as_string())

        logger.info(f"Successfully sent notification email to {recipient_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {recipient_email}: {str(e)}")
        return False


def notify_issue_verified(
    issue_id: UUID,
    issue_title: str,
    department_name: Optional[str] = None,
    recipient_emails: Optional[List[str]] = None
):
    """
    Dispatches notifications when an issue is verified by authorities.
    """
    subject = f"[RoadOps Alert] Issue Verified: {issue_title}"
    body = (
        f"A road infrastructure hazard has been verified by municipal inspection.\n\n"
        f"Issue ID: {issue_id}\n"
        f"Title: {issue_title}\n"
        f"Assigned Department: {department_name or 'Pending Assignment'}\n\n"
        f"View details on the Authority Command Center dashboard."
    )
    for email in (recipient_emails or ["authorities@roadsafety.gov"]):
        send_email_notification(email, subject, body)


def notify_issue_assigned(
    issue_id: UUID,
    issue_title: str,
    department_name: str,
    assigned_officer_email: Optional[str] = None,
    notes: Optional[str] = None
):
    """
    Dispatches notifications when an issue is assigned to a department or specific officer.
    """
    subject = f"[RoadOps Task Assignment] {department_name}: {issue_title}"
    body = (
        f"You have received a new road repair task assignment.\n\n"
        f"Issue ID: {issue_id}\n"
        f"Title: {issue_title}\n"
        f"Department: {department_name}\n"
        f"Instructions: {notes or 'No special instructions.'}\n\n"
        f"Please log in to the Authority Dashboard to manage field dispatch."
    )
    recipients = [assigned_officer_email] if assigned_officer_email else [f"{department_name.lower()}@city.gov"]
    for email in recipients:
        send_email_notification(email, subject, body)


def notify_issue_status_changed(
    issue_id: UUID,
    issue_title: str,
    previous_status: str,
    new_status: str,
    comment: Optional[str] = None,
    citizen_emails: Optional[List[str]] = None,
    citizen_phones: Optional[List[str]] = None
):
    """
    Dispatches notifications to citizen reporters and authorities when status changes (e.g. IN_PROGRESS, FIXED, CLOSED).
    """
    subject = f"[RoadOps Status Update] {issue_title} is now {new_status}"
    body = (
        f"The status of a reported road infrastructure issue has been updated.\n\n"
        f"Issue Title: {issue_title}\n"
        f"Previous State: {previous_status}\n"
        f"New State: {new_status}\n"
        f"Remarks: {comment or 'Status updated in system.'}\n\n"
        f"Thank you for helping keep our roads safe!"
    )
    for email in (citizen_emails or ["reporter@citizen.gov"]):
        send_email_notification(email, subject, body)

    # Dispatch SMS to citizen phone numbers
    if citizen_phones:
        sms_body = f"RoadOps Alert: Your reported issue '{issue_title}' is now {new_status}. Remarks: {comment or 'Updated'}. Ref: {str(issue_id)[:8]}"
        for phone in citizen_phones:
            send_sms_notification(phone, sms_body)


# ==============================================================================
# Twilio Citizen SMS Alerts Integration
# ==============================================================================

def send_sms_notification(to_phone: str, message_body: str) -> bool:
    """
    Sends an SMS notification via Twilio API,
    or logs formatted SMS in mock mode when Twilio credentials are not configured.
    """
    if not to_phone:
        return False

    if not settings.SMS_ENABLED or not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        logger.info(
            f"[MOCK TWILIO SMS DISPATCH] To: {to_phone} | From: {settings.TWILIO_FROM_NUMBER or '+15550199999'} | Message: {message_body}"
        )
        return True

    try:
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=message_body,
            from_=settings.TWILIO_FROM_NUMBER,
            to=to_phone
        )
        logger.info(f"Successfully sent Twilio SMS to {to_phone}, SID: {message.sid}")
        return True
    except Exception as e:
        logger.error(f"Failed to dispatch Twilio SMS to {to_phone}: {str(e)}")
        return False
