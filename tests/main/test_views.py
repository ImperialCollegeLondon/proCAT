from pytest_django.asserts import assertTemplateUsed


def test_index(client, admin_client):
    """Test the index view."""
    with assertTemplateUsed(template_name="main/index.html"):
        response = client.get("/")
    assert response.status_code == 200
