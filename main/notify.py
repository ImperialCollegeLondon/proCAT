"""Function to send notifications to user."""

from django.core.mail import send_mail


def email_user(subject: str, email: str, message: str) -> None:
    """Send email notification to the project lead."""
    send_mail(
        subject=subject,
        message=message,
        from_email=None,
        recipient_list=[email],
        fail_silently=False,
    )
