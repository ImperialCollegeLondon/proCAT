FROM python:3.13-slim-bookworm

ADD requirements.txt /
RUN pip install -r /requirements.txt
EXPOSE 8000
COPY --chown=nobody:nogroup . /usr/src/app
WORKDIR /usr/src/app
USER nobody
