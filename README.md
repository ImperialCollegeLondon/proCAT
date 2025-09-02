 <!-- markdownlint-disable MD041 -->
[![codecov](https://codecov.io/gh/ImperialCollegeLondon/proCAT/graph/badge.svg?token=A9KNEMYXXN)](https://codecov.io/gh/ImperialCollegeLondon/proCAT)

# proCAT

A Django web app for hosting the Project Charging and Analytics Tool (ProCAT).

This Django project uses:

- [`pip-tools`][pip-tools] for packaging and dependency management.
- [`pre-commit`][pre-commit] for various linting, formatting and static type checking.
  - Pre-commit hooks are automatically kept updated with [pre-commit.ci][pre-commit.ci].
- [`pytest`][pytest] and [GitHub Actions][GitHub Actions].

## Installation

To get started:

1. Activate a git repository (required for `pre-commit` and the package versioning with
`setuptools-scm`):

   ```bash
   git init
   ```

1. Create and activate a [virtual environment]:

   ```bash
   python -m venv .venv
   source .venv/bin/activate # with Powershell on Windows: `.venv\Scripts\Activate.ps1`
   ```

1. Install development requirements:

   ```bash
   pip install -r dev-requirements.txt
   ```

1. (Optionally) install tools for building documentation:

   ```bash
   pip install -r doc-requirements.txt
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

## Login, SSO and local accounts

During development, local accounts are enabled but links in the front page will try to
login you via Imperial's Single Sign On (SSO) and it will fail unless you have all the
connection details configured - ask for details to the HoRSE.

If you want to use the local accounts instead of SSO, manually go to the following URLs:

- Registration: <http://localhost:8000/register/>
- Login: <http://localhost:8000/auth/login/>

If you use SSO and you already have a local account with the same email address,
typically your own, then that account will be updated with the details from the SSO
account. So, if you created a superuser account as above with your email and then
connect via SSO, then your account will be the superuser account.

## Installation with Docker

The app can be run within a Docker container and a `docker-compose.yml` file is provided to make this easy for development.

Ensure you have [Docker][Docker] installed and simply run:

```bash
docker compose up
```

The app will be available at <http://127.0.0.1:8000/>

## Updating Dependencies

To add or remove dependencies:

1. Edit the `dependencies` variables in the `pyproject.toml` file (aim to keep
development tools separate from the project requirements).
1. Update the requirements files:
   - `pip-compile` for `requirements.txt` - the project requirements.
   - `pip-compile --extra dev -o dev-requirements.txt` for the development requirements.
   - `pip-compile --extra doc -o doc-requirements.txt` for
the documentation tools.
1. Sync the files with your installation (install packages):
   - `pip-sync *requirements.txt`

To upgrade pinned versions, use the `--upgrade` flag with `pip-compile`.

Versions can be restricted from updating within the `pyproject.toml` using standard
python package version specifiers, i.e. `"black<23"` or `"pip-tools!=6.12.2"`

[pip-tools]: https://pip-tools.readthedocs.io/en/stable/
[pre-commit]: https://pre-commit.com/
[pytest]: https://pytest.org/
[GitHub Actions]: https://github.com/features/actions
[pre-commit.ci]: https://pre-commit.ci
[Docker]: https://docs.docker.com/desktop/
[virtual environment]: https://docs.python.org/3/library/venv.html
