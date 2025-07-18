"""Function to send notifications to user and admin."""

from django.core.mail import EmailMessage, send_mail


def email_user(subject: str, email: str, message: str) -> None:
    """Send email notification to the project lead."""
    send_mail(
        subject=subject,
        message=message,
        from_email=None,
        recipient_list=[email],
        fail_silently=False,
    )


def email_user_and_cc_admin(
    subject: str,
    email: str,
    admin_email: list[str] | str,
    message: str,
) -> None:
    """Send email notification to the project lead and CC admin."""
    cc_list = [admin_email] if isinstance(admin_email, str) else admin_email
    email_message = EmailMessage(
        subject=subject,
        body=message,
        from_email=None,
        to=[email],
        cc=cc_list,
    )
    email_message.send(fail_silently=False)


def email_attachment(
    subject: str,
    email: list[str],
    message: str,
    attachment_fname: str,
    attachment: str,
    attachment_type: str,
) -> None:
    """Send email with attachment to HoRSEs."""
    email_message = EmailMessage(
        subject=subject,
        body=message,
        from_email=None,
        to=email,
    )
    email_message.attach(
        filename=attachment_fname, content=attachment, mimetype=attachment_type
    )
    email_message.send(fail_silently=False)
