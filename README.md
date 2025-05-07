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
[Docker]: [https://docs.docker.com/desktop/]
[virtual environment]: https://docs.python.org/3/library/venv.html
