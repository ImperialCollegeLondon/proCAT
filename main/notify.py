"""Function to send notifications about project status."""

from django.core.mail import send_mail


def email_lead_project_status(email: str, project_name: str, message: str) -> None:
    """Send email notification to the project lead about the project status."""
    subject = f"[Project Status Update] {project_name}"
    send_mail(
        subject,
        message,
        from_email=None,
        recipient_list=[email],
        fail_silently=False,
    )
