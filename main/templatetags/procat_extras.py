"""Extra functions for code in html templates."""

from django import template
from django.contrib.auth.models import User

register = template.Library()


@register.filter(name="has_group")
def has_group(user: User, group_name: str) -> bool:
    """Custom tag to check if user belongs to group.

    Args:
        user (_type_): _description_
        group_name (str): Name of group to check.

    Returns:
        bool: True if user is member of group_name, else False.
    """
    return user.groups.filter(name=group_name).exists()
