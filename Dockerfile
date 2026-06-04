ARG APPDIR=/usr/src/app

# Build environment
FROM python:3.13-slim-bookworm AS build

ARG APPDIR
RUN apt-get update && apt-get install --no-install-recommends -y \
    build-essential \
    curl \
    git \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

# Download the latest installer, install it and then remove it
ADD https://astral.sh/uv/install.sh /install.sh
RUN chmod -R 755 /install.sh && /install.sh && rm /install.sh

# Set up the UV environment path correctly
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR ${APPDIR}

# Copy dependency manifest files to make use of Docker cache
COPY pyproject.toml ./
COPY uv.lock ./

RUN uv sync

COPY . .

# Execution environment
FROM python:3.13-slim-bookworm
ARG APPDIR
WORKDIR ${APPDIR}

COPY . .
COPY --from=build ${APPDIR}/.venv/lib/python3.13/site-packages/ /usr/local/lib/python3.13/site-packages

EXPOSE 8000
COPY --chown=nobody:nogroup . /usr/src/app

USER nobody
