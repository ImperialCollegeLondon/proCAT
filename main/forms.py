"""Forms needed by ProCAT."""

from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm


class CustomUserCreationForm(UserCreationForm):  # type: ignore [type-arg]
    """Form to create users with the custom User model.

    TODO: This is a placeholder for development. When SSO is implemented, this won't be
    needed since available users will be retrieved automatically.
    """

    class Meta:
        """Meta class for the form."""

        model = get_user_model()
        fields = ("username",)
