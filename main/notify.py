"""Function to send notifications about project status."""

from django.core.mail import send_mail

lead_message = """The project {project_name} is due for completion soon.

Please check the project status and make sure to update your time spent
on the project.
"""


def notify_lead(project: object) -> None:
    """Send notification to the project lead about the project status."""
    subject = f"Project {project.name} is due for completion soon!"
    message = lead_message.format(project_name=project.name)

    send_mail(
        subject,
        message,
        from_email=None,
        recipient_list=[project.lead.email],
        fail_silently=False,
    )
