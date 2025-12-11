# Hint from Snorkel
# Base Dockerfile or image that fully sets up the environment, including all required tools, resources, and dependencies.
# It should be reproducible, lightweight, and run without privileged mode.

FROM python:3.13-slim-bookworm

WORKDIR /app

RUN pip install sortedcontainers==2.4.0

COPY generate_scenarios.py /app/generate_scenarios.py

RUN python3 generate_scenarios.py