FROM python:3.13-slim-bookworm

ADD requirements.txt /
RUN pip install uv
RUN uv pip install --no-cache-dir --system -r /requirements.txt
EXPOSE 8000
COPY --chown=nobody:nogroup . /usr/src/app
WORKDIR /usr/src/app
USER nobody
