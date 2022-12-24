# syntax=docker/dockerfile:1

FROM python:3.11.1-slim-bullseye

ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --upgrade pip==22.3.1

COPY requirements-dev.txt requirements-dev.txt

RUN pip install -r requirements-dev.txt

COPY pyproject.toml LICENSE README.md ./

COPY src /app/src

RUN pip install -e .
