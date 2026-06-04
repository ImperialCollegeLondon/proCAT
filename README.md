 <!-- markdownlint-disable MD041 -->
<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-12-orange.svg?style=flat-square)](#contributors-)
<!-- ALL-CONTRIBUTORS-BADGE:END -->
[![codecov](https://codecov.io/gh/ImperialCollegeLondon/proCAT/graph/badge.svg?token=A9KNEMYXXN)](https://codecov.io/gh/ImperialCollegeLondon/proCAT)

# Project Charging and Analytics Tool (proCAT)

A Django web app for hosting the Project Charging and Analytics Tool (proCAT).

This Django project uses:

- [`uv`][uv] for packaging and dependency management.
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

1. Create and activate a virtual environment. This creates a `.venv` in the same
  directory with the environment, including the `dev` dependencies:

   ```bash
   uv sync
   ```

1. (Optionally) install tools for building documentation:

   ```bash
   uv sync --group doc
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

## Documentation

The documentation is built using the [Material theme for MkDocs](https://squidfunk.github.io/mkdocs-material/) and can be found at <https://imperialcollegelondon.github.io/proCAT/>.

## Updating Dependencies

You can check all the options for [managing dependencies with uv], but a summary would be:

1. To add a dependency use `uv add dependency_name`.
2. You can add it to a group, as well with the `--group` flag,
  eg. `uv add --group dev dependency_name`.
3. To remove a dependency use `uv remove dependency_name`.

To upgrade pinned versions, use `uv lock --upgrade`.

Versions can be restricted from updating within the `pyproject.toml` using standard
python package version specifiers, i.e. `"black<23"` or `"pip-tools!=6.12.2"`

[uv]: https://docs.astral.sh/uv/
[pre-commit]: https://pre-commit.com/
[pytest]: https://pytest.org/
[GitHub Actions]: https://github.com/features/actions
[pre-commit.ci]: https://pre-commit.ci
[Docker]: https://docs.docker.com/desktop/
[managing dependencies with uv]: https://docs.astral.sh/uv/concepts/projects/dependencies/

## Contributors ✨

Thanks goes to these wonderful people ([emoji key](https://allcontributors.org/docs/en/emoji-key)):

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tbody>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://www.imperial.ac.uk/admin-services/ict/self-service/research-support/rcs/service-offering/research-software-engineering/"><img src="https://avatars.githubusercontent.com/u/6095790?v=4?s=100" width="100px;" alt="Diego Alonso Álvarez"/><br /><sub><b>Diego Alonso Álvarez</b></sub></a><br /><a href="https://github.com/ImperialCollegeLondon/proCAT/commits?author=dalonsoa" title="Code">💻</a> <a href="#ideas-dalonsoa" title="Ideas, Planning, & Feedback">🤔</a> <a href="#infra-dalonsoa" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a> <a href="#maintenance-dalonsoa" title="Maintenance">🚧</a> <a href="https://github.com/ImperialCollegeLondon/proCAT/pulls?q=is%3Apr+reviewed-by%3Adalonsoa" title="Reviewed Pull Requests">👀</a> <a href="https://github.com/ImperialCollegeLondon/proCAT/commits?author=dalonsoa" title="Tests">⚠️</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/stephwills"><img src="https://avatars.githubusercontent.com/u/72925860?v=4?s=100" width="100px;" alt="Steph Wills"/><br /><sub><b>Steph Wills</b></sub></a><br /><a href="https://github.com/ImperialCollegeLondon/proCAT/commits?author=stephwills" title="Code">💻</a> <a href="https://github.com/ImperialCollegeLondon/proCAT/pulls?q=is%3Apr+reviewed-by%3Astephwills" title="Reviewed Pull Requests">👀</a> <a href="https://github.com/ImperialCollegeLondon/proCAT/commits?author=stephwills" title="Tests">⚠️</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/Sahil590"><img src="https://avatars.githubusercontent.com/u/56438860?v=4?s=100" width="100px;" alt="Sahil Raja"/><br /><sub><b>Sahil Raja</b></sub></a><br /><a href="https://github.com/ImperialCollegeLondon/proCAT/commits?author=Sahil590" title="Code">💻</a> <a href="https://github.com/ImperialCollegeLondon/proCAT/pulls?q=is%3Apr+reviewed-by%3ASahil590" title="Reviewed Pull Requests">👀</a> <a href="https://github.com/ImperialCollegeLondon/proCAT/commits?author=Sahil590" title="Tests">⚠️</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/SaranjeetKaur"><img src="https://avatars.githubusercontent.com/u/28556616?v=4?s=100" width="100px;" alt="Saranjeet Kaur"/><br /><sub><b>Saranjeet Kaur</b></sub></a><br /><a href="https://github.com/ImperialCollegeLondon/proCAT/commits?author=SaranjeetKaur" title="Code">💻</a> <a href="https://github.com/ImperialCollegeLondon/proCAT/pulls?q=is%3Apr+reviewed-by%3ASaranjeetKaur" title="Reviewed Pull Requests">👀</a> <a href="https://github.com/ImperialCollegeLondon/proCAT/commits?author=SaranjeetKaur" title="Tests">⚠️</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://www.imperial.ac.uk/people/j.coker20"><img src="https://avatars.githubusercontent.com/u/62701887?v=4?s=100" width="100px;" alt="jfcoker"/><br /><sub><b>jfcoker</b></sub></a><br /><a href="https://github.com/ImperialCollegeLondon/proCAT/commits?author=jfcoker" title="Code">💻</a> <a href="https://github.com/ImperialCollegeLondon/proCAT/pulls?q=is%3Apr+reviewed-by%3Ajfcoker" title="Reviewed Pull Requests">👀</a> <a href="https://github.com/ImperialCollegeLondon/proCAT/commits?author=jfcoker" title="Tests">⚠️</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/AdrianDAlessandro"><img src="https://avatars.githubusercontent.com/u/40875798?v=4?s=100" width="100px;" alt="Adrian D'Alessandro"/><br /><sub><b>Adrian D'Alessandro</b></sub></a><br /><a href="#ideas-AdrianDAlessandro" title="Ideas, Planning, & Feedback">🤔</a> <a href="#infra-AdrianDAlessandro" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/Alexnies"><img src="https://avatars.githubusercontent.com/u/139470181?v=4?s=100" width="100px;" alt="Alexander Nies"/><br /><sub><b>Alexander Nies</b></sub></a><br /><a href="https://github.com/ImperialCollegeLondon/proCAT/commits?author=Alexnies" title="Code">💻</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/laura-ellington"><img src="https://avatars.githubusercontent.com/u/184098019?v=4?s=100" width="100px;" alt="laura-ellington"/><br /><sub><b>laura-ellington</b></sub></a><br /><a href="https://github.com/ImperialCollegeLondon/proCAT/commits?author=laura-ellington" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://twitter.com/theyashjani"><img src="https://avatars.githubusercontent.com/u/54172910?v=4?s=100" width="100px;" alt="Yash Jani"/><br /><sub><b>Yash Jani</b></sub></a><br /><a href="https://github.com/ImperialCollegeLondon/proCAT/commits?author=theyashjani" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/Tosinibikunle"><img src="https://avatars.githubusercontent.com/u/89074158?v=4?s=100" width="100px;" alt="Tosinibikunle"/><br /><sub><b>Tosinibikunle</b></sub></a><br /><a href="https://github.com/ImperialCollegeLondon/proCAT/commits?author=Tosinibikunle" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/mjademitchell"><img src="https://avatars.githubusercontent.com/u/242165951?v=4?s=100" width="100px;" alt="mjademitchell"/><br /><sub><b>mjademitchell</b></sub></a><br /><a href="https://github.com/ImperialCollegeLondon/proCAT/commits?author=mjademitchell" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/Max-Gamill"><img src="https://avatars.githubusercontent.com/u/91465918?v=4?s=100" width="100px;" alt="Max Gamill"/><br /><sub><b>Max Gamill</b></sub></a><br /><a href="https://github.com/ImperialCollegeLondon/proCAT/commits?author=Max-Gamill" title="Code">💻</a></td>
    </tr>
  </tbody>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind welcome!
