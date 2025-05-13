"""Tests for the models."""


def test_department_model_str():
    """Test the object string for the model."""
    from main import models

    dep = models.Department(name="ICT", faculty="Other")
    assert str(dep) == "ICT - Other"


def test_activity_code_model_str():
    """Test the object string for the model."""
    from main import models

    dep = models.ActivityCode(code="1234", description="Some code", notes="None")
    assert str(dep) == "1234 - Some code"
