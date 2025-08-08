 <!-- markdownlint-disable MD041 -->
[![codecov](https://codecov.io/gh/ImperialCollegeLondon/proCAT/graph/badge.svg?token=A9KNEMYXXN)](https://codecov.io/gh/ImperialCollegeLondon/proCAT)

# proCAT

A Django web app for hosting the Project Charging and Analytics Tool (ProCAT).

This Django project uses:

- [`UV`][uv] for packaging and dependency management.
- [`pre-commit`][pre-commit] for various linting, formatting and static type checking.
  - Pre-commit hooks are automatically kept updated with [pre-commit.ci][pre-commit.ci].
- [`pytest`][pytest] and [GitHub Actions][GitHub Actions].

## Installation

To get started:

1. Create and activate a [virtual environment]:

   ```bash
   uv venv
   source .venv/bin/activate
   ```

1. Install dependencies:

   ```bash
   uv pip install -r requirements.txt dev-requirements.txt
   ```

1. Install the git hooks:

   ```bash
   pre-commit install
   ```

1. Run the web app:

   ```bash
   python manage.py runserver
   ```

   When running the webapp for the first time you may get a warning similar to:

   `You have 19 unapplied migration(s). Your project may not work properly until you apply the migrations for app(s): admin, auth, contenttypes, main, sessions.`

   If this is the case, stop your webapp (with CONTROL-C) and apply the migrations with:

   ```bash
   python manage.py migrate
   ```

   then restart it.

1. Run the tests:

   ```bash
   pytest
   ```

1. Create an admin account to access admin backend:

   ```bash
   python manage.py createsuperuser
   ```

## Installation with Docker

The app can be run within a Docker container and a `docker-compose.yml` file is provided to make this easy for development.

Ensure you have [Docker][Docker] installed and simply run:

```bash
docker compose up
```

The app will be available at <http://127.0.0.1:8000/>

## Updating Dependencies

uv manages project dependencies and environments, with support for lockfiles, workspaces, and more,
similar to `rye` or `poetry`:

1. run `uv add EXAMPLE`

where EXAMPLE would be the package name.

Versions can be restricted from updating within the `pyproject.toml` using standard

[uv]: https://docs.astral.sh/uv/
[pre-commit]: https://pre-commit.com/
[pytest]: https://pytest.org/
[GitHub Actions]: https://github.com/features/actions
[pre-commit.ci]: https://pre-commit.ci
[Docker]: https://docs.docker.com/desktop/
[virtual environment]: https://docs.python.org/3/library/venv.html
