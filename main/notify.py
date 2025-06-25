"""Function to send notifications to project lead."""

from django.core.mail import send_mail


def email_lead(subject: str, email: str, message: str) -> None:
    """Send email notification to the project lead."""
    send_mail(
        subject=subject,
        message=message,
        from_email="noreply@example.com",
        recipient_list=[email],
        fail_silently=False,
    )
