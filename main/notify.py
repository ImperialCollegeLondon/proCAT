"""Function to send notifications to user and HoRSE."""

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


def email_user_and_cc_head(
    subject: str,
    email: str,
    head_email: list[str] | str,
    message: str,
) -> None:
    """Send email notification to the project lead and CC HoRSE."""
    cc_list = [head_email] if isinstance(head_email, str) else head_email
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
